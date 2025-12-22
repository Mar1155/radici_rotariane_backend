from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, RegisterView, MeView, SkillsSearchView, SkillListView, SoftSkillListView, ClubListView

router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('me/', MeView.as_view(), name='me'),
    path('clubs/', ClubListView.as_view(), name='club-list'),
    path('skills/', SkillsSearchView.as_view(), name='skills-search'),
    path('skills-list/', SkillListView.as_view(), name='skills-list'),
    path('soft-skills-list/', SoftSkillListView.as_view(), name='soft-skills-list'),
    path('', include(router.urls)),
]
