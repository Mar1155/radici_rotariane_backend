from rest_framework import viewsets, permissions, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db.models import Q
from .models import User, Skill, SoftSkill
from .serializers import (
    UserSearchSerializer, UserRegistrationSerializer, UserProfileSerializer,
    SkillSerializer, SoftSkillSerializer
)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserRegistrationSerializer


class MeView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user


class SkillListView(generics.ListAPIView):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_classes = [permissions.IsAuthenticated]


class SoftSkillListView(generics.ListAPIView):
    queryset = SoftSkill.objects.all()
    serializer_class = SoftSkillSerializer
    permission_classes = [permissions.IsAuthenticated]


class SkillsSearchView(generics.ListAPIView):
    """Search users based on skills and profession."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSearchSerializer

    def get_queryset(self):
        queryset = User.objects.exclude(id=self.request.user.id)
        
        # Filter users who have completed their profile (must have skills and soft_skills)
        queryset = queryset.filter(skills__isnull=False).distinct()
        queryset = queryset.filter(soft_skills__isnull=False).distinct()
        
        search = self.request.query_params.get('search', None)
        sector = self.request.query_params.get('sector', None)
        
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(profession__icontains=search) |
                Q(bio__icontains=search) |
                Q(skills__name__icontains=search) |
                Q(skills__translations__icontains=search) |
                Q(soft_skills__name__icontains=search) |
                Q(soft_skills__translations__icontains=search)
            ).distinct()
            
        if sector:
            queryset = queryset.filter(sector__icontains=sector)
            
        return queryset



class ClubListView(generics.ListAPIView):
    """List all club users."""
    permission_classes = [AllowAny]
    serializer_class = UserProfileSerializer

    def get_queryset(self):
        return User.objects.filter(user_type='CLUB')


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for searching users."""
    
    def get_permissions(self):
        if self.action == 'retrieve':
            return [AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return UserProfileSerializer
        return UserSearchSerializer

    def get_queryset(self):
        if self.request.user.is_authenticated:
            queryset = User.objects.exclude(id=self.request.user.id)
        else:
            queryset = User.objects.all()

        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        return queryset
