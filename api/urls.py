"""
API URL 路由 — 使用 DRF Router 自动注册 ViewSet
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from . import views

router = DefaultRouter()
router.register(r'tasks', views.AITaskViewSet, basename='task')
router.register(r'models', views.AIModelViewSet, basename='aimodel')

urlpatterns = [
    # JWT 认证
    path('token/', TokenObtainPairView.as_view(), name='token_obtain'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', views.register, name='register'),
    # AI 能力列表
    path('abilities/', views.abilities_list, name='abilities'),
    # ViewSet 路由
    path('', include(router.urls)),
]
