# views.py
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from users.permissions import ruolo_applicativo
from .models import Card, CardAttachment, CardReport, CardTranslation, SavedCard
from .serializers import CardSerializer, CardListSerializer, CardTranslationSerializer
from .sanitizers import sanitize_article_html
from cms.models import GeoArea
from cms.models import ArticleType
import json
from datetime import datetime
import traceback
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db import transaction
from forum.utils import sanitize_rich_text
from chat.services.translation import (
    TranslationProviderError,
    TranslationServiceNotConfigured,
    normalize_language_code,
    supported_languages,
    translate_text,
)


def validate_article_fields(tipo, valori, info_values=None):
    """Controlla i campi di un articolo contro il suo tipo.

    `valori` e' una mappa campo -> valore. Due regole sole:
    un campo **obbligatorio** deve avere un valore, un campo **non attivo** non
    deve averlo. Non esiste piu' un terzo stato: attivo-ma-facoltativo e'
    semplicemente un campo attivo che non e' fra gli obbligatori.

    Ritorna: (valido, messaggio_errore)
    """
    attivi = set(tipo.active_fields or [])
    obbligatori = set(tipo.required_fields or [])

    # `author` lo compila il backend dall'utente autenticato, non il form.
    # `infoElements` e `save` non sono campi con un valore proprio.
    esclusi = {'author', 'infoElements', 'save'}

    mancanti = [c for c in sorted(obbligatori - esclusi) if not valori.get(c)]
    if mancanti:
        return False, f'Campi obbligatori mancanti: {", ".join(mancanti)}'

    non_previsti = [c for c in sorted(set(valori) - attivi - esclusi) if valori.get(c)]
    if non_previsti:
        return False, (f'Campi non previsti dal tipo «{tipo.name}»: '
                       f'{", ".join(non_previsti)}')

    if info_values:
        chiavi = set(tipo.info_elements.values_list('key', flat=True))
        sconosciute = sorted(set(info_values) - chiavi)
        if sconosciute:
            return False, (f'Elementi informativi non previsti dal tipo '
                           f'«{tipo.name}»: {", ".join(sconosciute)}')
        if 'infoElements' in obbligatori:
            vuoti = [k for k in chiavi if not str(info_values.get(k, '')).strip()]
            if vuoti:
                return False, (f'Elementi informativi da compilare: '
                               f'{", ".join(sorted(vuoti))}')
    elif 'infoElements' in obbligatori and tipo.info_elements.exists():
        return False, 'Elementi informativi da compilare.'

    tag = valori.get('tags') or []
    ammessi = set(tipo.allowed_tags.values_list('key', flat=True))
    estranei = sorted(set(tag) - ammessi)
    if estranei:
        return False, f'Tag non previsti dal tipo «{tipo.name}»: {", ".join(estranei)}'

    return True, None


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser, JSONParser])
@permission_classes([IsAuthenticated])
def create_article(request, type_key):
    """Crea un articolo del tipo indicato.

    Il tipo dice tutto: quali campi esistono, quali tag sono ammessi, quali
    elementi informativi, e chi puo' pubblicare. Prima la stessa informazione
    era spalmata su due stringhe libere (section, tab) validate contro una
    configurazione scritta nel codice e duplicata nel frontend.
    """
    try:
        tipo = ArticleType.objects.filter(key=type_key).first()
        if tipo is None:
            return Response(
                {'error': f'Tipo di articolo «{type_key}» inesistente'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not request.user.is_authenticated:
            return Response(
                {'error': 'Utente non autenticato'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        user_role = ruolo_applicativo(request.user)
        if user_role not in (tipo.can_publish or []):
            return Response(
                {'error': f'Un utente «{user_role}» non puo pubblicare articoli '
                          f'di tipo «{tipo.name}»'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 3. Estrai i dati dal FormData
        title = request.data.get('title')
        subtitle = request.data.get('subtitle')
        cover_image = request.FILES.get('coverImage')
        tags_json = request.data.get('tags')
        content = sanitize_article_html(request.data.get('content'))
        date_type = request.data.get('dateType', 'none')
        location = request.data.get('location')
        info_values_json = request.data.get('infoValues')
        gallery_files = request.FILES.getlist('galleryFiles')
        
        # Estrai date
        date_raw = request.data.get('date')
        date_start_raw = request.data.get('dateStart')
        date_end_raw = request.data.get('dateEnd')
        
        # Determina se c'è una data valida (per validazione)
        has_date = (date_type == 'single' and date_raw) or (date_type == 'range' and date_start_raw)
        
        # Parse tags da JSON string
        tags = json.loads(tags_json) if tags_json else []
        
        # Valori informativi indicizzati per CHIAVE: prima erano un array
        # posizionale allineato all'ordine della configurazione, e riordinare
        # gli elementi corrompeva in silenzio gli articoli gia' scritti.
        info_values = json.loads(info_values_json) if info_values_json else {}
        
        # 4. Validazione centralizzata di tutti i campi richiesti
        is_valid, error_msg = validate_article_fields(tipo, {
            'title': title, 'subtitle': subtitle, 'content': content,
            'coverImage': cover_image, 'tags': tags, 'location': location,
            'gallery': gallery_files, 'date': has_date,
        }, info_values)
        
        if not is_valid:
            return Response(
                {'error': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 5. Prepara i dati per il modello
        card_data = {
            'article_type': tipo,
            'title': title,
            'subtitle': subtitle,
            'cover_image': cover_image,
            'tags': tags,
            'content': content,
            'date_type': date_type,
            'location': location,
            'author': request.user,
            'info_values': info_values,
            'is_published': True,
        }
        
        # Aggiungi date in base al tipo
        if date_type == 'single':
            if date_raw:
                card_data['date'] = datetime.strptime(date_raw, "%Y-%m-%d").date()
        elif date_type == 'range':
            if date_start_raw:
                card_data['date_start'] = datetime.strptime(date_start_raw, "%Y-%m-%d").date()
            if date_end_raw:
                card_data['date_end'] = datetime.strptime(date_end_raw, "%Y-%m-%d").date()
        
        # 6. Crea la card
        card = Card.objects.create(**card_data)

        # 7. Salva eventuali allegati (galleria)
        for file in gallery_files:
            content_type = (file.content_type or '').lower()
            if content_type.startswith('image/'):
                file_type = 'image'
            elif content_type.startswith('video/'):
                file_type = 'video'
            else:
                file_type = 'file'

            CardAttachment.objects.create(
                card=card,
                file=file,
                file_type=file_type,
                original_name=getattr(file, 'name', '') or ''
            )
        
        # Serializza e ritorna
        serializer = CardSerializer(card, context={'request': request})
        return Response(
            {
                'message': 'Card creata con successo',
                'card': serializer.data
            },
            status=status.HTTP_201_CREATED
        )
        
    except json.JSONDecodeError:
        return Response(
            {'error': 'Formato JSON non valido per tags o infoValues'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except ValueError as e:
        return Response(
            {'error': f'Errore nel parsing dei dati: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except ValidationError as e:
        return Response(
            {'error': 'Validazione della card fallita', 'details': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        traceback.print_exc()
        return Response(
            {'error': f'Errore durante la creazione: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def list_articles(request):
    """Articoli pubblicati, filtrati per tipo.

    `?type=<chiave>` e' il filtro principale: e' il tipo a dire a quale elenco
    appartiene un articolo. Si aggiungono `?geo=` (gerarchico), `?tag=` e
    `?search=`, tutti facoltativi.
    """
    cards = (Card.objects.filter(is_published=True)
             .select_related('geo_area', 'article_type', 'author'))

    tipo_key = request.GET.get('type')
    if tipo_key:
        cards = cards.filter(article_type__key=tipo_key)

    tag = request.GET.get('tag')
    if tag:
        cards = cards.filter(tags__contains=[tag])

    ricerca = request.GET.get('search')
    if ricerca:
        cards = cards.filter(
            Q(title__icontains=ricerca) | Q(subtitle__icontains=ricerca)
        )

    # Filtro geografico GERARCHICO: `?geo=puglia` restituisce anche gli articoli
    # delle sue province. E' il motivo per cui la geografia e' un albero e non
    # una lista piatta di tag - con i tag "Puglia" e "Bari" sarebbero due
    # etichette scollegate.
    geo = request.GET.get('geo')
    if geo:
        area = GeoArea.objects.filter(key=geo, is_active=True).first()
        if area:
            cards = cards.filter(geo_area__path__startswith=area.path)
        else:
            cards = cards.none()

    limite = request.GET.get('limit')
    if limite and limite.isdigit():
        cards = cards[:int(limite)]

    serializer = CardListSerializer(cards, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET', 'PATCH', 'DELETE'])
@parser_classes([MultiPartParser, FormParser, JSONParser])
@permission_classes([AllowAny])
def get_card(request, slug):
    """
    Recupera, aggiorna o elimina una singola card per slug.
    PATCH/DELETE consentiti solo al proprietario o superuser.
    """
    try:
        if request.method == 'GET':
            card = Card.objects.get(slug=slug, is_published=True)
        else:
            card = Card.objects.get(slug=slug)
    except Card.DoesNotExist:
        return Response(
            {'error': 'Card non trovata'},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'GET':
        # Incrementa views
        card.views_count += 1
        card.save(update_fields=['views_count'])
        serializer = CardSerializer(card, context={'request': request})
        return Response(serializer.data)

    if not request.user.is_authenticated:
        return Response(
            {'error': 'Utente non autenticato'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not (request.user.is_superuser or (card.author_id and card.author_id == request.user.id)):
        return Response(
            {'error': 'Non autorizzato'},
            status=status.HTTP_403_FORBIDDEN
        )

    if request.method == 'DELETE':
        card.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PATCH - Aggiorna la card
    data = request.data
    gallery_files = request.FILES.getlist('galleryFiles')
    
    def parse_json_field(value, default):
        if value is None:
            return default
        if isinstance(value, str):
            try:
                return json.loads(value)
            except ValueError:
                return default
        return value

    # Prepara i dati per la validazione (usa valori attuali se non forniti)
    title = data.get('title') if 'title' in data else card.title
    subtitle = data.get('subtitle') if 'subtitle' in data else card.subtitle
    content = sanitize_article_html(data.get('content')) if 'content' in data else card.content
    cover_image = request.FILES.get('coverImage') if 'coverImage' in request.FILES else card.cover_image
    tags = parse_json_field(data.get('tags'), None) if 'tags' in data else card.tags
    location = data.get('location') if 'location' in data else card.location
    info_values = parse_json_field(data.get('infoValues'), None) if 'infoValues' in data else card.info_values
    
    # Determina se c'è una data valida (per validazione)
    has_date = card.date or card.date_start  # Controlla se la card ha già date
    
    # Validazione centralizzata
    is_valid, error_msg = validate_article_fields(card.article_type, {
        'title': title, 'subtitle': subtitle, 'content': content,
        'coverImage': cover_image, 'tags': tags, 'location': location,
        'gallery': gallery_files, 'date': has_date,
    }, info_values)
    
    if not is_valid:
        return Response(
            {'error': error_msg},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Se la validazione passa, aggiorna i campi
    if 'title' in data:
        card.title = data.get('title') or None
    if 'subtitle' in data:
        card.subtitle = data.get('subtitle') or None
    if 'content' in data:
        card.content = sanitize_article_html(data.get('content')) or None
    if 'location' in data:
        card.location = data.get('location') or None

    if 'dateType' in data:
        date_type = data.get('dateType') or 'none'
        card.date_type = date_type
        if date_type == 'none':
            card.date = None
            card.date_start = None
            card.date_end = None

    if 'date' in data:
        date = data.get('date')
        card.date = datetime.strptime(date, "%Y-%m-%d").date() if date else None
    if 'dateStart' in data:
        date_start = data.get('dateStart')
        card.date_start = datetime.strptime(date_start, "%Y-%m-%d").date() if date_start else None
    if 'dateEnd' in data:
        date_end = data.get('dateEnd')
        card.date_end = datetime.strptime(date_end, "%Y-%m-%d").date() if date_end else None

    if 'tags' in data:
        card.tags = parse_json_field(data.get('tags'), [])

    if 'infoValues' in data:
        card.info_values = parse_json_field(data.get('infoValues'), {})

    if 'coverImage' in request.FILES:
        card.cover_image = request.FILES.get('coverImage')

    card.save()

    # Salva nuovi allegati se forniti
    for file in gallery_files:
        content_type = (file.content_type or '').lower()
        if content_type.startswith('image/'):
            file_type = 'image'
        elif content_type.startswith('video/'):
            file_type = 'video'
        else:
            file_type = 'file'

        CardAttachment.objects.create(
            card=card,
            file=file,
            file_type=file_type,
            original_name=getattr(file, 'name', '') or ''
        )

    serializer = CardSerializer(card, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def report_card(request, slug):
    """Segnala una card."""
    if not request.user.is_authenticated:
        return Response(
            {'error': 'Utente non autenticato'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    try:
        card = Card.objects.get(slug=slug)
    except Card.DoesNotExist:
        return Response(
            {'error': 'Card non trovata'},
            status=status.HTTP_404_NOT_FOUND
        )

    reason = request.data.get('reason', '')
    CardReport.objects.create(card=card, reporter=request.user, reason=reason)
    return Response({'message': 'Segnalazione inviata'}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def translate_card(request, slug):
    """Traduci una card nella lingua richiesta, con caching."""
    try:
        card = Card.objects.get(slug=slug)
    except Card.DoesNotExist:
        return Response(
            {'detail': 'Card non trovata.'},
            status=status.HTTP_404_NOT_FOUND
        )

    target_language = request.data.get('target_language') or request.query_params.get('target_language')
    if not target_language:
        return Response(
            {'detail': 'target_language è obbligatorio.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    normalized_language = normalize_language_code(target_language)
    if normalized_language not in supported_languages():
        return Response(
            {'detail': 'Lingua di destinazione non supportata.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    existing = CardTranslation.objects.filter(card=card, target_language=normalized_language).first()
    if existing:
        serializer = CardTranslationSerializer(existing)
        return Response(serializer.data)

    if not (card.title or card.subtitle or card.content):
        return Response(
            {'detail': 'La card è vuota, impossibile tradurre.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        title_result = translate_text(card.title or '', normalized_language)
        subtitle_result = translate_text(card.subtitle or '', normalized_language)
        content_result = translate_text(
            card.content or '',
            normalized_language,
            text_format='html'
        )
    except TranslationServiceNotConfigured:
        return Response(
            {'detail': 'Nessun provider di traduzione configurato.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except TranslationProviderError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

    # sanitize_article_html (non quello del forum): conserva le immagini,
    # che l'allowlist del forum eliminerebbe dalla versione tradotta.
    safe_content = sanitize_article_html(content_result.text) if content_result.text else ''

    with transaction.atomic():
        translation, created = CardTranslation.objects.update_or_create(
            card=card,
            target_language=normalized_language,
            defaults={
                'translated_title': title_result.text,
                'translated_subtitle': subtitle_result.text,
                'translated_content': safe_content,
                'provider': title_result.provider,
                'detected_source_language': title_result.detected_source_language,
            }
        )

    serializer = CardTranslationSerializer(translation)
    http_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return Response(serializer.data, status=http_status)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_save_card(request, slug):
    """Toggle salvataggio di una card (salva/rimuovi)."""
    if not request.user.is_authenticated:
        return Response(
            {'error': 'Utente non autenticato'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    try:
        card = Card.objects.get(slug=slug)
    except Card.DoesNotExist:
        return Response(
            {'error': 'Card non trovata'},
            status=status.HTTP_404_NOT_FOUND
        )

    if 'save' not in (card.article_type.active_fields or []):
        return Response(
            {'error': 'Salvataggio non consentito per questa card'},
            status=status.HTTP_403_FORBIDDEN
        )

    saved, created = SavedCard.objects.get_or_create(user=request.user, card=card)
    if not created:
        # Già salvata, la rimuoviamo
        saved.delete()
        return Response({'is_saved': False}, status=status.HTTP_200_OK)
    
    return Response({'is_saved': True}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_saved_cards(request):
    """
    Lista le card salvate.
    ?user_id=<id> per vedere i salvati di un altro utente (pubblico).
    ?type=<chiave> per filtrare per tipo di articolo.
    Senza user_id, mostra i salvati dell'utente autenticato.
    """
    user_id = request.query_params.get('user_id')
    tipo_key = request.query_params.get('type')

    if user_id:
        # Salvati pubblici di un utente specifico
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'Utente non trovato'},
                status=status.HTTP_404_NOT_FOUND
            )
    else:
        # Salvati dell'utente autenticato
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Utente non autenticato'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        target_user = request.user

    saved_qs = SavedCard.objects.filter(user=target_user).select_related('card', 'card__author')
    if tipo_key:
        saved_qs = saved_qs.filter(card__article_type__key=tipo_key)
    
    # Estrai solo le card pubblicate, ordinate per data di salvataggio
    saved_qs = saved_qs.filter(card__is_published=True).order_by('-created_at')
    cards = [saved.card for saved in saved_qs]
    
    serializer = CardListSerializer(cards, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def list_user_cards(request):
    """
    Lista le card pubblicate da un utente.
    ?user_id=<id> per vedere le pubblicazioni di un utente specifico (pubblico).
    ?type=<chiave> per filtrare per tipo di articolo.
    Senza user_id, mostra le pubblicazioni dell'utente autenticato.
    """
    user_id = request.query_params.get('user_id')
    tipo_key = request.query_params.get('type')

    if user_id:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'Utente non trovato'},
                status=status.HTTP_404_NOT_FOUND
            )
    else:
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Utente non autenticato'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        target_user = request.user

    cards_qs = Card.objects.filter(author=target_user, is_published=True).select_related('author')
    if tipo_key:
        cards_qs = cards_qs.filter(article_type__key=tipo_key)
    cards_qs = cards_qs.order_by('-created_at')

    serializer = CardListSerializer(cards_qs, many=True, context={'request': request})
    return Response(serializer.data)
