# views.py
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from .models import Card, CardAttachment, CardReport, CardTranslation
from .serializers import CardSerializer, CardTranslationSerializer
from .structure import (
    get_required_fields,
    get_expected_info_elements_count,
    can_user_add_article,
    validate_card_consistency,
    get_tab_fields_config,
)
import json
from datetime import datetime
import traceback
from django.core.exceptions import ValidationError
from django.db import transaction
from forum.utils import sanitize_rich_text
from chat.services.translation import (
    TranslationProviderError,
    TranslationServiceNotConfigured,
    normalize_language_code,
    supported_languages,
    translate_text,
)


def validate_card_fields(section, tab, title, subtitle, content, cover_image, tags, 
                        location, info_element_values, gallery_files, author=None, date_value=None):
    """
    Centralizzata validazione di tutti i campi richiesti per una card.
    Usa la configurazione da structure.py per determinare quali campi sono required/hidden.
    
    Ritorna: (is_valid, error_message)
    """
    # 1. Ottieni configurazione dalla struttura
    fields_config = get_tab_fields_config(section, tab)
    required_fields = fields_config['required']
    hidden_fields = fields_config['hidden']
    expected_info_elements = get_expected_info_elements_count(section, tab)
    
    # 2. Mappa dei campi con i loro valori
    field_values = {
        'title': title,
        'subtitle': subtitle,
        'content': content,
        'coverImage': cover_image,
        'tags': tags,
        'location': location,
        'author': author,
        'gallery': gallery_files,
        'date': date_value,
        # infoElements gestito separatamente
    }
    
    # 3. Valida campi obbligatori (devono avere un valore)
    missing_fields = []
    for field in required_fields:
        if field == 'infoElements':
            continue  # Validato separatamente
        
        value = field_values.get(field)
        if not value:
            missing_fields.append(field)
    
    if missing_fields:
        return False, f'Campi obbligatori mancanti: {", ".join(missing_fields)}'
    
    # 4. Valida campi hidden (NON devono avere un valore)
    forbidden_fields = []
    for field in hidden_fields:
        if field == 'infoElements':
            continue  # Validato separatamente

        if field == 'author':
            # Author e' sempre valorizzato lato server, non deve bloccare la creazione
            continue
        
        value = field_values.get(field)
        if value:
            forbidden_fields.append(field)
    
    if forbidden_fields:
        return False, f'Campi non consentiti per questa sezione: {", ".join(forbidden_fields)}'
    
    # 5. Validazione infoElements count
    if len(info_element_values) != expected_info_elements:
        return False, f'Info elements count non valido. Atteso {expected_info_elements}, ricevuto {len(info_element_values)}'
    
    # 6. Validazione consistenza (tags, section/tab)
    is_valid, errors = validate_card_consistency(section, tab, tags, len(info_element_values))
    if not is_valid:
        return False, f'Validazione della card fallita: {", ".join(errors)}'
    
    return True, None


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def create_card(request, section, tab):
    """
    Crea una nuova card dal form Next.js
    
    Validazioni:
    - section e tab devono essere validi e non null
    - Solo i campi 'required' della struttura devono avere valori
    - I campi 'hidden' devono essere null
    - Tags devono appartenere alla lista consentita per section/tab
    - infoElementValues deve avere esattamente il numero di elementi atteso
    - L'utente deve avere il ruolo corretto per creare un articolo in questa sezione
    """
    try:
        # 1. Validazione section/tab - non possono essere null
        if not section or not tab:
            return Response(
                {'error': 'Section e tab sono obbligatori'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 2. Validazione utente autenticato e ruolo
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Utente non autenticato'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Determina il ruolo dell'utente
        user_role = 'admin' if request.user.is_staff else 'club' if hasattr(request.user, 'club') and request.user.club else 'user'
        
        # Controlla se l'utente può aggiungere articoli in questa sezione/tab
        if not can_user_add_article(section, tab, user_role):
            return Response(
                {'error': f'Utente con ruolo "{user_role}" non può aggiungere articoli in questa sezione'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 3. Estrai i dati dal FormData
        title = request.data.get('title')
        subtitle = request.data.get('subtitle')
        cover_image = request.FILES.get('coverImage')
        tags_json = request.data.get('tags')
        content = request.data.get('content')
        date_type = request.data.get('dateType', 'none')
        location = request.data.get('location')
        info_element_values_json = request.data.get('infoElementValues')
        gallery_files = request.FILES.getlist('galleryFiles')
        
        # Estrai date
        date_raw = request.data.get('date')
        date_start_raw = request.data.get('dateStart')
        date_end_raw = request.data.get('dateEnd')
        
        # Determina se c'è una data valida (per validazione)
        has_date = (date_type == 'single' and date_raw) or (date_type == 'range' and date_start_raw)
        
        # Parse tags da JSON string
        tags = json.loads(tags_json) if tags_json else []
        
        # Parse infoElementValues da JSON string
        info_element_values = json.loads(info_element_values_json) if info_element_values_json else []
        
        # 4. Validazione centralizzata di tutti i campi richiesti
        is_valid, error_msg = validate_card_fields(
            section=section,
            tab=tab,
            title=title,
            subtitle=subtitle,
            content=content,
            cover_image=cover_image,
            tags=tags,
            location=location,
            info_element_values=info_element_values,
            gallery_files=gallery_files,
            author=request.user,
            date_value=has_date
        )
        
        if not is_valid:
            return Response(
                {'error': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 5. Prepara i dati per il modello
        card_data = {
            'section': section,
            'tab': tab,
            'title': title,
            'subtitle': subtitle,
            'cover_image': cover_image,
            'tags': tags,
            'content': content,
            'date_type': date_type,
            'location': location,
            'author': request.user,
            'infoElementValues': info_element_values,
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
        serializer = CardSerializer(card)
        return Response(
            {
                'message': 'Card creata con successo',
                'card': serializer.data
            },
            status=status.HTTP_201_CREATED
        )
        
    except json.JSONDecodeError:
        return Response(
            {'error': 'Formato JSON non valido per tags o infoElementValues'},
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
def list_cards(request, section, tab):
    """
    Lista tutte le cards pubblicate per una specifica section e tab
    """
    filters = {'is_published': True, 'section': section, 'tab': tab}
    
    cards = Card.objects.filter(**filters)
    serializer = CardSerializer(cards, many=True)
    return Response(serializer.data)


@api_view(['GET', 'PATCH', 'DELETE'])
@parser_classes([MultiPartParser, FormParser, JSONParser])
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
        serializer = CardSerializer(card)
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
    content = data.get('content') if 'content' in data else card.content
    cover_image = request.FILES.get('coverImage') if 'coverImage' in request.FILES else card.cover_image
    tags = parse_json_field(data.get('tags'), None) if 'tags' in data else card.tags
    location = data.get('location') if 'location' in data else card.location
    info_element_values = parse_json_field(data.get('infoElementValues'), None) if 'infoElementValues' in data else card.infoElementValues
    
    # Determina se c'è una data valida (per validazione)
    has_date = card.date or card.date_start  # Controlla se la card ha già date
    
    # Validazione centralizzata
    is_valid, error_msg = validate_card_fields(
        section=card.section,
        tab=card.tab,
        title=title,
        subtitle=subtitle,
        content=content,
        cover_image=cover_image,
        tags=tags,
        location=location,
        info_element_values=info_element_values,
        gallery_files=gallery_files,
        author=card.author,
        date_value=has_date
    )
    
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
        card.content = data.get('content') or None
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

    if 'infoElementValues' in data:
        card.infoElementValues = parse_json_field(data.get('infoElementValues'), [])

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

    serializer = CardSerializer(card)
    return Response(serializer.data)


@api_view(['POST'])
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

    safe_content = sanitize_rich_text(content_result.text) if content_result.text else ''

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
