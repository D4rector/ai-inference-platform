"""
Celery 异步任务 —— AI 推理

面试话术：
「任务提交后立即返回 pending，由 Celery 异步队列处理推理，
通过 Redis 传递状态变更，前端轮询或 WebSocket 获取结果。
避免长时间推理阻塞 HTTP 请求。」
"""
from celery import shared_task
from django.utils import timezone
from .ai_service import run_inference


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def process_ai_task(self, task_id: int):
    """
    异步处理 AI 推理任务。
    自动重试 3 次，每次间隔 5 秒。
    """
    from .models import AITask

    try:
        task = AITask.objects.get(id=task_id)
        task.status = 'processing'
        task.save(update_fields=['status'])

        result = run_inference(task)

        task.result = result
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.save()

    except Exception as exc:
        try:
            task = AITask.objects.get(id=task_id)
            # 重试次数未用完 → 扔回队列
            if self.request.retries < self.max_retries:
                task.status = 'pending'
                task.save(update_fields=['status'])
                raise self.retry(exc=exc)
            # 重试耗尽 → 标记失败
            task.status = 'failed'
            task.error_message = str(exc)
            task.save()
        except AITask.DoesNotExist:
            pass
