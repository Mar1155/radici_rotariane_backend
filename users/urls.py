from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, RegisterView, MeView, SkillsSearchView,
    SkillListView, SoftSkillListView, FocusAreaListView,
    ClubListView, platform_stats, password_reset_request, password_reset_confirm
)

router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('password-reset/request/', password_reset_request, name='password-reset-request'),
    path('password-reset/confirm/', password_reset_confirm, name='password-reset-confirm'),
    path('me/', MeView.as_view(), name='me'),
    path('clubs/', ClubListView.as_view(), name='club-list'),
    path('skills/', SkillsSearchView.as_view(), name='skills-search'),
    path('skills-list/', SkillListView.as_view(), name='skills-list'),
    path('soft-skills-list/', SoftSkillListView.as_view(), name='soft-skills-list'),
    path('focus-areas-list/', FocusAreaListView.as_view(), name='focus-areas-list'),
    path('stats/', platform_stats, name='platform-stats'),
    path('', include(router.urls)),
]
