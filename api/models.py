"""
AITask — AI 推理任务模型
状态机: pending → processing → completed / failed
"""
from django.db import models
from django.contrib.auth.models import User


class AITask(models.Model):
    """每条记录 = 一次 AI 推理请求"""

    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]

    TASK_TYPE_CHOICES = [
        ('text_summary', '文本摘要'),
        ('text_generation', '文本生成'),
        ('image_classify', '图像识别'),
        ('image_generate', '图像生成'),
        ('code_generate', '代码生成'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks',
                             verbose_name='用户')
    task_type = models.CharField('任务类型', max_length=32,
                                 choices=TASK_TYPE_CHOICES, default='text_summary')
    status = models.CharField('状态', max_length=16,
                              choices=STATUS_CHOICES, default='pending')
    # 输入
    text_input = models.TextField('文本输入', blank=True, default='')
    image = models.ImageField('图片', upload_to='uploads/%Y/%m/', blank=True, null=True)
    # 输出
    result = models.JSONField('推理结果', default=dict, blank=True)
    error_message = models.TextField('错误信息', blank=True, default='')
    # 时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    completed_at = models.DateTimeField('完成时间', null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'AI任务'
        verbose_name_plural = 'AI任务'

    def __str__(self):
        return f'[{self.get_task_type_display()}] {self.status} — {self.user.username}'

    def is_finished(self):
        return self.status in ('completed', 'failed')


class AIModel(models.Model):
    """模型注册表 — 记录接入的 AI 模型及其能力"""
    name = models.CharField('模型名称', max_length=128, unique=True)
    version = models.CharField('版本', max_length=32, default='v1')
    task_type = models.CharField('任务类型', max_length=32,
                                 choices=AITask.TASK_TYPE_CHOICES)
    description = models.TextField('描述', blank=True, default='')
    is_active = models.BooleanField('启用', default=True)
    created_at = models.DateTimeField('注册时间', auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'AI模型'
        verbose_name_plural = 'AI模型'

    def __str__(self):
        return f'{self.name} ({self.version})'
