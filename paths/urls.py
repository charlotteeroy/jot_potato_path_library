"""
URL configuration for the Path Library API.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    IssueViewSet,
    RootCauseViewSet,
    InitiativeViewSet,
    PathViewSet,
    TaskViewSet,
    PathCommentViewSet,
)

router = DefaultRouter()
router.register(r'issues', IssueViewSet, basename='issue')
router.register(r'root-causes', RootCauseViewSet, basename='rootcause')
router.register(r'initiatives', InitiativeViewSet, basename='initiative')
router.register(r'paths', PathViewSet, basename='path')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'comments', PathCommentViewSet, basename='comment')

urlpatterns = [
    path('', include(router.urls)),
]
