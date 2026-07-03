"""
Admin 注册
"""
from django.contrib import admin
from .models import AITask, AIModel


@admin.register(AITask)
class AITaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'task_type', 'status', 'created_at']
    list_filter = ['status', 'task_type', 'created_at']
    search_fields = ['text_input', 'error_message']
    readonly_fields = ['created_at', 'updated_at', 'completed_at']


@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'version', 'task_type', 'is_active', 'created_at']
    list_filter = ['task_type', 'is_active']
    search_fields = ['name', 'description']
