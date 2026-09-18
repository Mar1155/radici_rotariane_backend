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
            'translated_location',
            'translated_body',
            'translated_info_values',
            'needs_review',
            'human_locked',
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
    geo_area = serializers.SerializerMethodField(read_only=True)
    article_type = serializers.SlugRelatedField(slug_field='key', read_only=True)
    assets = serializers.SerializerMethodField(read_only=True)
    # I campi testuali arrivano gia' nella lingua richiesta: e' il server a
    # scegliere fra originale e traduzione, non il client ad assemblarli.
    title = serializers.SerializerMethodField()
    subtitle = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()
    info_values = serializers.SerializerMethodField()
    translated_from = serializers.SerializerMethodField(read_only=True)
    
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
            'body',
            'assets',
            # `location` e' il testo che si legge sulla card; `geo_area` e' cio'
            # su cui filtra la ricerca. Servono entrambi, e mancava il primo:
            # si salvava e l'API non lo restituiva, quindi riaprendo una bozza
            # spariva — ed e' obbligatorio per meta' dei tipi.
            'location',
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
            'article_type',
            'info_values',
            'source_locale',
            'translated_from',
            'is_saved',
            'saved_by_users',
            'geo_area',
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at', 'views_count']
    
    def get_geo_area(self, obj):
        """Area geografica dell'articolo, con il percorso completo.

        Il percorso serve al frontend per capire se un articolo ricade sotto
        l'area filtrata senza dover conoscere l'albero.
        """
        area = obj.geo_area
        if not area:
            return None
        return {
            'key': area.key,
            'name': area.name,
            'level': area.level,
            'path': area.path,
        }

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


    # --- Lingua richiesta ----------------------------------------------------

    def _lingua(self):
        richiesta = self.context.get('locale')
        if not richiesta:
            req = self.context.get('request')
            richiesta = req.GET.get('locale') if req else None
        return (richiesta or '').strip().lower() or None

    def _traduzione(self, obj):
        """La traduzione da usare, o None se si mostra l'originale."""
        if '_traduzione' in self.__dict__.setdefault('_cache', {}).get(obj.pk, {}):
            return self._cache[obj.pk]['_traduzione']
        lingua = self._lingua()
        trovata = None
        if lingua and lingua != (obj.source_locale or 'it'):
            trovata = next(
                (t for t in obj.translations.all() if t.target_language == lingua),
                None)
        self._cache.setdefault(obj.pk, {})['_traduzione'] = trovata
        return trovata

    def get_title(self, obj):
        t = self._traduzione(obj)
        return (t.translated_title or obj.title) if t else obj.title

    def get_subtitle(self, obj):
        t = self._traduzione(obj)
        return (t.translated_subtitle or obj.subtitle) if t else obj.subtitle

    def get_location(self, obj):
        t = self._traduzione(obj)
        return (t.translated_location or obj.location) if t else obj.location

    def get_body(self, obj):
        t = self._traduzione(obj)
        return (t.translated_body or obj.body) if t else obj.body

    def get_info_values(self, obj):
        t = self._traduzione(obj)
        if t and t.translated_info_values:
            # I valori tradotti, con quelli non tradotti al loro posto.
            return {**(obj.info_values or {}), **t.translated_info_values}
        return obj.info_values

    def get_translated_from(self, obj):
        """La lingua originale, quando si sta leggendo una traduzione.

        `None` quando si legge l'originale: e' cosi' che il frontend sa se
        mostrare la nota "scritto originariamente in ...".
        """
        return (obj.source_locale or 'it') if self._traduzione(obj) else None

    def get_assets(self, obj):
        """Le immagini citate dal corpo, risolte in indirizzi.

        Il corpo memorizza l'identificativo, mai l'indirizzo: se i file si
        spostano, gli articoli non vanno toccati. Il prezzo e' questa tabella
        di risoluzione, che viaggia accanto al documento invece che dentro.
        """
        from cms.media import url_assoluto
        from .media_refs import identificativi_media
        from .models import MediaAsset

        ids = identificativi_media(obj.body)
        if not ids:
            return {}
        return {
            str(a.id): {
                'url': url_assoluto(a.file.url),
                'width': a.width, 'height': a.height, 'alt': a.alt,
            }
            for a in MediaAsset.objects.filter(id__in=ids)
        }


class CardListSerializer(CardSerializer):
    """Serializer per gli ENDPOINT DI LISTA.

    Identico a CardSerializer ma senza `body`: il corpo di un articolo non
    serve per disegnare una card in griglia, e includerlo rende ogni risposta
    di lista pesante quanto la somma di tutti gli articoli della sezione.
    Il corpo resta disponibile sul dettaglio (GET /api/section/cards/<slug>).
    """

    class Meta(CardSerializer.Meta):
        fields = [f for f in CardSerializer.Meta.fields if f != 'body']
