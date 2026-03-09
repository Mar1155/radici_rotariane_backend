# serializers.py
from rest_framework import serializers
from .models import Card, CardAttachment, CardTranslation


class SavedByUserSerializer(serializers.Serializer):
    """Serializer leggero per gli utenti che hanno salvato una card"""
    id = serializers.IntegerField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    avatar = serializers.ImageField(allow_null=True)


class CardAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardAttachment
        fields = ['id', 'file', 'file_type', 'original_name', 'uploaded_at']


class CardTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardTranslation
        fields = [
            'id',
            'card',
            'target_language',
            'translated_title',
            'translated_subtitle',
            'translated_content',
            'provider',
            'detected_source_language',
            'created_at',
        ]


class CardSerializer(serializers.ModelSerializer):
    display_date = serializers.CharField(source='get_display_date', read_only=True)
    is_past = serializers.BooleanField(source='is_past_event', read_only=True)
    author_name = serializers.CharField(source='author.username', read_only=True, allow_null=True)
    author_id = serializers.IntegerField(source='author.id', read_only=True, allow_null=True)
    author_club = serializers.SerializerMethodField(read_only=True)
    club_name = serializers.CharField(source='author.club_name', read_only=True, allow_null=True)
    club_id = serializers.IntegerField(source='author.club.id', read_only=True, allow_null=True)
    attachments = CardAttachmentSerializer(many=True, read_only=True)
    is_saved = serializers.SerializerMethodField(read_only=True)
    saved_by_users = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Card
        fields = [
            'id',
            'title',
            'subtitle',
            'slug',
            'cover_image',
            'attachments',
            'tags',
            'content',
            'date_type',
            'date',
            'date_start',
            'date_end',
            'display_date',
            'is_past',
            'created_at',
            'updated_at',
            'is_published',
            'views_count',
            'author_name',
            'author_id',
            'author_club',
            'club_name',
            'club_id',
            'section',
            'tab',
            'infoElementValues',
            'is_saved',
            'saved_by_users',
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at', 'views_count']
    
    def get_is_saved(self, obj):
        """Controlla se l'utente corrente ha salvato questa card"""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            return obj.saved_by.filter(user=request.user).exists()
        return False

    def get_saved_by_users(self, obj):
        """Restituisce la lista degli utenti che hanno salvato questa card"""
        saved_entries = obj.saved_by.select_related('user').order_by('-created_at')
        users = []
        for entry in saved_entries:
            user = entry.user
            users.append({
                'id': user.id,
                'first_name': user.first_name or '',
                'last_name': user.last_name or '',
                'username': user.username or '',
                'user_type': getattr(user, 'user_type', 'NORMAL'),
                'club_name': getattr(user, 'club_name', '') or '',
                'avatar': user.avatar.url if user.avatar else None,
            })
        return users

    def get_author_club(self, obj):
        """Estrai il club dall'autore"""
        if obj.author:
            # Assume che l'utente abbia un campo club o simile
            # Adatta questo in base alla tua struttura User
            club = getattr(obj.author, 'club', None)
            if club:
                # Se club è un oggetto, ritorna l'ID o il nome
                # Dipende dalla struttura - usa quello che è disponibile
                return getattr(club, 'id', None) or getattr(club, 'name', None)
        return None
