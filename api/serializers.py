"""
DRF 序列化器 — AITask / User / AIModel
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import AITask, AIModel


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'date_joined']
        read_only_fields = ['id', 'date_joined']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class AIModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIModel
        fields = '__all__'


class AITaskSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = AITask
        fields = [
            'id', 'user', 'username', 'task_type', 'task_type_display',
            'status', 'status_display', 'text_input', 'image',
            'result', 'error_message',
            'created_at', 'updated_at', 'completed_at',
        ]
        read_only_fields = [
            'id', 'user', 'username', 'status', 'status_display',
            'result', 'error_message', 'created_at', 'updated_at', 'completed_at',
        ]


class AITaskCreateSerializer(serializers.ModelSerializer):
    """创建任务专用 — 只暴露输入字段"""

    class Meta:
        model = AITask
        fields = ['id', 'task_type', 'text_input', 'image']
        read_only_fields = ['id']


class DashboardSerializer(serializers.Serializer):
    """仪表盘统计数据"""
    today_tasks = serializers.IntegerField()
    total_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
    failed_tasks = serializers.IntegerField()
    avg_duration_seconds = serializers.FloatField()
    model_usage = serializers.ListField(child=serializers.DictField())
    recent_tasks = AITaskSerializer(many=True)
