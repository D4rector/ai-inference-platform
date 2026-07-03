"""
API ViewSets — 任务 CRUD / 仪表盘 / 能力列表 / 认证
任务状态机: pending → processing → completed / failed
"""
from datetime import date
from django.utils import timezone
from django.db.models import Count, Avg, F, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.models import User

from .models import AITask, AIModel
from .serializers import (
    AITaskSerializer, AITaskCreateSerializer,
    AIModelSerializer, UserSerializer, DashboardSerializer,
)
from .ai_service import run_inference, get_abilities_list


# ── 认证 ──────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """用户注册"""
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({'message': '注册成功'}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ── AI 能力列表 ───────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def abilities_list(request):
    """返回所有可用的 AI 能力（前端下拉框用）"""
    return Response(get_abilities_list())


# ── AITask ViewSet ────────────────────────────────────────

class AITaskViewSet(viewsets.ModelViewSet):
    """
    AI 推理任务 CRUD。
    创建时自动触发推理（perform_create），通过状态机管理生命周期。
    """
    queryset = AITask.objects.all()  # Router 用
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return AITaskCreateSerializer
        return AITaskSerializer

    def create(self, request, *args, **kwargs):
        """创建任务 + 返回完整任务数据"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # 用完整序列化器返回（包含 status / result 等）
        task = serializer.instance
        out = AITaskSerializer(task, context={'request': request})
        return Response(out.data, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        """只返回当前用户的任务"""
        return AITask.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """任务创建 → 优先 Celery 异步，不可用则同步降级"""
        task = serializer.save(user=self.request.user)

        # 尝试 Celery 异步
        try:
            from .tasks import process_ai_task
            process_ai_task.delay(task.id)
            return  # 任务交给 Celery，立即返回 pending
        except Exception:
            pass  # Celery 不可用，同步执行

        task.status = 'processing'
        task.save(update_fields=['status'])
        try:
            result = run_inference(task)
            task.result = result
            task.status = 'completed'
            task.completed_at = timezone.now()
        except Exception as e:
            task.error_message = str(e)
            task.status = 'failed'
        task.save()

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """仪表盘统计数据"""
        tasks = self.get_queryset()
        today = date.today()

        today_tasks = tasks.filter(created_at__date=today)
        completed = tasks.filter(status='completed')

        # 平均耗时
        avg_duration = completed.annotate(
            duration=F('completed_at') - F('created_at')
        ).aggregate(avg=Avg('duration'))['avg']
        avg_seconds = avg_duration.total_seconds() if avg_duration else 0

        # 模型使用统计（按任务类型）
        model_usage = tasks.values('task_type').annotate(
            count=Count('id')
        ).order_by('-count')[:5]

        data = {
            'today_tasks': today_tasks.count(),
            'total_tasks': tasks.count(),
            'completed_tasks': completed.count(),
            'failed_tasks': tasks.filter(status='failed').count(),
            'avg_duration_seconds': round(avg_seconds, 2),
            'model_usage': list(model_usage),
            'recent_tasks': AITaskSerializer(
                tasks[:10], many=True, context={'request': request}
            ).data,
        }
        return Response(data)

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """重试失败任务"""
        task = self.get_object()
        if task.status != 'failed':
            return Response({'error': '只能重试失败的任务'}, status=400)

        task.status = 'processing'
        task.error_message = ''
        task.save(update_fields=['status', 'error_message'])

        try:
            result = run_inference(task)
            task.result = result
            task.status = 'completed'
            task.completed_at = timezone.now()
        except Exception as e:
            task.error_message = str(e)
            task.status = 'failed'

        task.save()
        return Response(AITaskSerializer(task, context={'request': request}).data)


# ── AIModel ViewSet ───────────────────────────────────────

class AIModelViewSet(viewsets.ReadOnlyModelViewSet):
    """模型注册表 — 只读查看"""
    queryset = AIModel.objects.filter(is_active=True)
    serializer_class = AIModelSerializer
    permission_classes = [IsAuthenticated]
