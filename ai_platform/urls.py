"""
项目根 URL 配置
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]

# 前端 SPA：所有非 API/Admin 路径返回 index.html
if settings.FRONTEND_DIST.exists():
    urlpatterns += [
        re_path(r'^assets/(?P<path>.*)$', serve, {
            'document_root': settings.FRONTEND_DIST / 'assets',
        }),
    ]

# Vue SPA fallback — 放最后
urlpatterns += [
    re_path(r'^.*$', TemplateView.as_view(template_name='index.html'), name='spa'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
