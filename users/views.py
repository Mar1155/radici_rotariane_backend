from rest_framework import viewsets, permissions, generics, status
from rest_framework.decorators import action, api_view, permission_classes as perm_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db.models import Q, Count
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
import secrets
from rest_framework_simplejwt.views import TokenObtainPairView
import logging
from .models import User, Skill, SoftSkill, FocusArea, PasswordResetToken, EmailVerificationToken
from .serializers import (
    UserSearchSerializer, UserRegistrationSerializer, UserProfileSerializer,
    SkillSerializer, SoftSkillSerializer, FocusAreaSerializer, EmailTokenObtainPairSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer,
    EmailVerificationRequestSerializer, EmailVerificationConfirmSerializer
)

logger = logging.getLogger('app.custom')


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserRegistrationSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        if not user.is_email_verified:
            _send_email_verification(user, self.request, force_send=True)


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer


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


class FocusAreaListView(generics.ListAPIView):
    queryset = FocusArea.objects.all()
    serializer_class = FocusAreaSerializer
    permission_classes = [permissions.IsAuthenticated]


class SkillsSearchView(generics.ListAPIView):
    """Search users based on skills and profession."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSearchSerializer

    def get_queryset(self):
        queryset = User.objects.exclude(id=self.request.user.id)
        
        # Filter users who have completed their profile (must have at least one skill)
        queryset = queryset.filter(skills__isnull=False).distinct()
        
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
        return User.objects.filter(user_type='CLUB').annotate(
            members_count=Count('members', filter=Q(members__user_type=User.Types.NORMAL), distinct=True),
            gemellaggi_count=Count('gemellaggi_chats', filter=Q(gemellaggi_chats__chat_type='gemellaggio'), distinct=True),
        )


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


@api_view(['GET'])
@perm_classes([AllowAny])
def platform_stats(request):
    """Return platform statistics for the homepage."""
    from forum.models import Post
    
    # Count clubs (users with user_type='CLUB')
    clubs_count = User.objects.filter(user_type='CLUB').count()
    
    # Count rotarians (users with user_type='NORMAL')
    rotarians_count = User.objects.filter(user_type='NORMAL').count()
    
    # Count unique countries from clubs
    countries = User.objects.filter(
        user_type='CLUB', 
        club_country__isnull=False
    ).exclude(club_country='').values_list('club_country', flat=True).distinct()
    countries_count = len(set(countries))
    
    # Count forum posts as "projects"
    projects_count = Post.objects.count()
    
    return Response({
        'clubs': clubs_count,
        'rotarians': rotarians_count,
        'countries': countries_count,
        'projects': projects_count,
    })


def _get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _build_reset_email_context(code: str, ttl_minutes: int):
    return {
        'code': code,
        'ttl_minutes': ttl_minutes,
        'site_name': getattr(settings, 'SITE_NAME', 'Radici Rotariane'),
        'support_email': getattr(settings, 'SUPPORT_EMAIL', ''),
    }


def _build_verification_email_context(code: str, ttl_minutes: int):
    return {
        'code': code,
        'ttl_minutes': ttl_minutes,
        'site_name': getattr(settings, 'SITE_NAME', 'Radici Rotariane'),
        'support_email': getattr(settings, 'SUPPORT_EMAIL', ''),
    }


def _send_email_verification(user, request, force_send: bool = False) -> bool:
    if user.is_email_verified:
        return True

    cooldown_seconds = getattr(settings, 'EMAIL_VERIFICATION_RESEND_SECONDS', 60)
    max_per_hour = getattr(settings, 'EMAIL_VERIFICATION_MAX_PER_HOUR', 5)
    ttl_minutes = getattr(settings, 'EMAIL_VERIFICATION_OTP_TTL_MINUTES', 30)

    now = timezone.now()
    if not force_send:
        recent_count = EmailVerificationToken.objects.filter(
            user=user,
            created_at__gte=now - timedelta(hours=1)
        ).count()

        if recent_count >= max_per_hour:
            return False

        last_token = EmailVerificationToken.objects.filter(user=user).order_by('-created_at').first()
        if last_token and (now - last_token.created_at).total_seconds() < cooldown_seconds:
            return False

    code = f"{secrets.randbelow(1000000):06d}"
    expires_at = now + timedelta(minutes=ttl_minutes)
    token = EmailVerificationToken.objects.create(
        user=user,
        code_hash=make_password(code),
        expires_at=expires_at,
        requested_ip=_get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
    )

    context = _build_verification_email_context(code, ttl_minutes)
    subject = f"{context['site_name']} - Verifica la tua email"
    text_body = render_to_string('users/email_verification_code.txt', context).strip()
    html_body = render_to_string('users/email_verification_code.html', context).strip()

    try:
        email_message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            to=[user.email],
        )
        if html_body:
            email_message.attach_alternative(html_body, 'text/html')
        email_message.send(fail_silently=False)
        return True
    except Exception as exc:
        logger.exception('Failed to send email verification: %s', exc)
        EmailVerificationToken.objects.filter(pk=token.pk).update(used_at=timezone.now())
        return False


@api_view(['POST'])
@perm_classes([AllowAny])
def password_reset_request(request):
    serializer = PasswordResetRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data['email']

    cooldown_seconds = getattr(settings, 'PASSWORD_RESET_RESEND_SECONDS', 60)
    max_per_hour = getattr(settings, 'PASSWORD_RESET_MAX_PER_HOUR', 5)
    ttl_minutes = getattr(settings, 'PASSWORD_RESET_OTP_TTL_MINUTES', 30)

    response_payload = {
        'detail': 'Se esiste un account associato a questa email, abbiamo inviato un codice di verifica.',
        'cooldown_seconds': cooldown_seconds,
    }

    try:
        user = get_user_model().objects.get(email__iexact=email)
    except get_user_model().DoesNotExist:
        return Response(response_payload)

    if not user.is_active:
        return Response(response_payload)

    now = timezone.now()
    recent_count = PasswordResetToken.objects.filter(
        user=user,
        created_at__gte=now - timedelta(hours=1)
    ).count()

    if recent_count >= max_per_hour:
        return Response(response_payload)

    last_token = PasswordResetToken.objects.filter(user=user).order_by('-created_at').first()
    if last_token and (now - last_token.created_at).total_seconds() < cooldown_seconds:
        return Response(response_payload)

    code = f"{secrets.randbelow(1000000):06d}"
    expires_at = now + timedelta(minutes=ttl_minutes)
    token = PasswordResetToken.objects.create(
        user=user,
        code_hash=make_password(code),
        expires_at=expires_at,
        requested_ip=_get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
    )

    context = _build_reset_email_context(code, ttl_minutes)
    subject = f"{context['site_name']} - Codice per reimpostare la password"
    text_body = render_to_string('users/password_reset_code.txt', context).strip()
    html_body = render_to_string('users/password_reset_code.html', context).strip()

    try:
        email_message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            to=[user.email],
        )
        if html_body:
            email_message.attach_alternative(html_body, 'text/html')
        email_message.send(fail_silently=False)
    except Exception as exc:
        logger.exception('Failed to send password reset email: %s', exc)
        PasswordResetToken.objects.filter(pk=token.pk).update(used_at=timezone.now())

    return Response(response_payload)


@api_view(['POST'])
@perm_classes([AllowAny])
def password_reset_confirm(request):
    serializer = PasswordResetConfirmSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data['email']
    code = serializer.validated_data['code']
    new_password = serializer.validated_data['new_password']

    invalid_response = Response(
        {'detail': 'Codice non valido o scaduto.'},
        status=status.HTTP_400_BAD_REQUEST
    )

    try:
        user = get_user_model().objects.get(email__iexact=email)
    except get_user_model().DoesNotExist:
        return invalid_response

    if not user.is_active:
        return invalid_response

    now = timezone.now()
    token = PasswordResetToken.objects.filter(
        user=user,
        used_at__isnull=True,
        expires_at__gt=now,
    ).order_by('-created_at').first()

    if not token:
        return invalid_response

    max_attempts = getattr(settings, 'PASSWORD_RESET_MAX_ATTEMPTS', 5)
    if not token.verify_code(code):
        token.attempts += 1
        if token.attempts >= max_attempts:
            token.used_at = now
        token.save(update_fields=['attempts', 'used_at'])
        return invalid_response

    try:
        validate_password(new_password, user=user)
    except ValidationError as exc:
        return Response(
            {'detail': exc.messages[0], 'errors': exc.messages},
            status=status.HTTP_400_BAD_REQUEST
        )

    user.set_password(new_password)
    user.save(update_fields=['password'])
    PasswordResetToken.objects.filter(
        user=user,
        used_at__isnull=True
    ).update(used_at=now)

    return Response({'detail': 'Password aggiornata con successo.'})


@api_view(['POST'])
@perm_classes([AllowAny])
def email_verification_request(request):
    serializer = EmailVerificationRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data['email']

    cooldown_seconds = getattr(settings, 'EMAIL_VERIFICATION_RESEND_SECONDS', 60)

    response_payload = {
        'detail': 'Se esiste un account associato a questa email, abbiamo inviato un codice di verifica.',
        'cooldown_seconds': cooldown_seconds,
    }

    try:
        user = get_user_model().objects.get(email__iexact=email)
    except get_user_model().DoesNotExist:
        return Response(response_payload)

    if not user.is_active or user.is_email_verified:
        return Response(response_payload)

    _send_email_verification(user, request, force_send=False)
    return Response(response_payload)


@api_view(['POST'])
@perm_classes([AllowAny])
def email_verification_confirm(request):
    serializer = EmailVerificationConfirmSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data['email']
    code = serializer.validated_data['code']

    invalid_response = Response(
        {'detail': 'Codice non valido o scaduto.'},
        status=status.HTTP_400_BAD_REQUEST
    )

    try:
        user = get_user_model().objects.get(email__iexact=email)
    except get_user_model().DoesNotExist:
        return invalid_response

    if user.is_email_verified:
        return Response({'detail': 'Email gia verificata.'})

    if not user.is_active:
        return invalid_response

    now = timezone.now()
    token = EmailVerificationToken.objects.filter(
        user=user,
        used_at__isnull=True,
        expires_at__gt=now,
    ).order_by('-created_at').first()

    if not token:
        return invalid_response

    max_attempts = getattr(settings, 'EMAIL_VERIFICATION_MAX_ATTEMPTS', 5)
    if not token.verify_code(code):
        token.attempts += 1
        if token.attempts >= max_attempts:
            token.used_at = now
        token.save(update_fields=['attempts', 'used_at'])
        return invalid_response

    user.email_verified_at = now
    user.save(update_fields=['email_verified_at'])
    EmailVerificationToken.objects.filter(
        user=user,
        used_at__isnull=True
    ).update(used_at=now)

    return Response({'detail': 'Email verificata con successo.'})
