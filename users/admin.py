from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin personalizzato per User che gestisce automaticamente 
    l'hashing delle password quando create/modificate
    """
    # Campi mostrati nella lista utenti
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    
    # Configurazione per aggiungere un nuovo utente
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
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
            'fields': ('first_name', 'last_name', 'email')
        }),
        ('Permessi', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Date importanti', {
            'fields': ('last_login', 'date_joined')
        }),
    )