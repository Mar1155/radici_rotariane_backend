from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Skill, SoftSkill, FocusArea, PasswordResetToken

User = get_user_model()

@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(SoftSkill)
class SoftSkillAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(FocusArea)
class FocusAreaAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin personalizzato per User che gestisce automaticamente 
    l'hashing delle password quando create/modificate
    """
    # Campi mostrati nella lista utenti
    list_display = ('username', 'email', 'first_name', 'last_name', 'rotary_id', 'user_type', 'club', 'is_staff', 'is_active')
    list_filter = ('user_type', 'club', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'rotary_id')
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions', 'skills', 'soft_skills', 'focus_areas')
    
    # Configurazione per aggiungere un nuovo utente
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'rotary_id', 'password1', 'password2'),
        }),
        ('Informazioni personali', {
            'fields': ('first_name', 'last_name'),
        }),
        ('Permessi', {
            'fields': ('is_active', 'is_staff', 'is_superuser'),
        }),
    )
    
    # Configurazione per modificare un utente esistente
    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('Informazioni personali', {
            'fields': ('first_name', 'last_name', 'email', 'rotary_id')
        }),
        ('Profilo Professionale', {
            'fields': ('user_type', 'club', 'profession', 'sector', 'skills', 'soft_skills', 'focus_areas', 'languages', 'offers_mentoring', 'bio', 'club_name', 'location', 'avatar')
        }),
        ('Permessi', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Date importanti', {
            'fields': ('last_login', 'date_joined')
        }),
    )


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'expires_at', 'used_at', 'attempts')
    list_filter = ('used_at',)
    search_fields = ('user__email', 'user__username')
    readonly_fields = ('user', 'code_hash', 'created_at', 'expires_at', 'used_at', 'attempts', 'requested_ip', 'user_agent')