from django.contrib import admin
from .models import Card, CardAttachment, CardReport, CardTranslation, SavedCard


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
	list_display = ('title', 'section', 'tab', 'is_published', 'created_at')
	list_filter = ('section', 'tab', 'is_published')
	search_fields = ('title', 'subtitle', 'slug')
	ordering = ('-created_at',)


@admin.register(CardAttachment)
class CardAttachmentAdmin(admin.ModelAdmin):
	list_display = ('card', 'file_type', 'original_name', 'uploaded_at')
	list_filter = ('file_type',)
	search_fields = ('original_name', 'file')
	ordering = ('-uploaded_at',)


@admin.register(CardReport)
class CardReportAdmin(admin.ModelAdmin):
	list_display = ('card', 'reporter', 'created_at')
	list_filter = ('created_at',)
	search_fields = ('card__title', 'reporter__email', 'reporter__first_name', 'reporter__last_name')
	ordering = ('-created_at',)


@admin.register(CardTranslation)
class CardTranslationAdmin(admin.ModelAdmin):
	list_display = ('card', 'target_language', 'provider', 'created_at')
	list_filter = ('target_language', 'provider')
	search_fields = ('card__title',)
	ordering = ('-created_at',)


@admin.register(SavedCard)
class SavedCardAdmin(admin.ModelAdmin):
	list_display = ('user', 'card', 'created_at')
	list_filter = ('created_at',)
	search_fields = ('user__username', 'user__email', 'card__title')
	ordering = ('-created_at',)
