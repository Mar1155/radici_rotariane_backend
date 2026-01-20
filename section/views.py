# views.py
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from .models import Card, CardAttachment, CardReport, CardTranslation
from .serializers import CardSerializer, CardTranslationSerializer
from .structure import (
    get_required_fields,
    get_expected_info_elements_count,
    can_user_add_article,
    validate_card_consistency,
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
        
        # Parse tags da JSON string
        tags = json.loads(tags_json) if tags_json else []
        
        # Parse infoElementValues da JSON string
        info_element_values = json.loads(info_element_values_json) if info_element_values_json else []
        
        # 4. Ottieni la configurazione dei campi per questa section/tab
        required_fields = get_required_fields(section, tab)
        expected_info_elements = get_expected_info_elements_count(section, tab)
        
        # 5. Validazione campi obbligatori
        missing_fields = []
        for field in required_fields:
            if field == 'infoElements':
                continue  # Validato separatamente
            
            value = None
            if field == 'title':
                value = title
            elif field == 'subtitle':
                value = subtitle
            elif field == 'content':
                value = content
            elif field == 'coverImage':
                value = cover_image
            elif field == 'tags':
                value = tags
            elif field == 'location':
                value = location
            elif field == 'author':
                value = request.user
            
            if not value:
                missing_fields.append(field)
        
        if missing_fields:
            return Response(
                {'error': f'Campi obbligatori mancanti: {", ".join(missing_fields)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 6. Validazione infoElements count
        if len(info_element_values) != expected_info_elements:
            return Response(
                {'error': f'Info elements count non valido. Atteso {expected_info_elements}, ricevuto {len(info_element_values)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 7. Validazione completa della consistenza (tags, section/tab)
        is_valid, errors = validate_card_consistency(section, tab, tags, len(info_element_values))
        if not is_valid:
            return Response(
                {'error': 'Validazione della card fallita', 'details': errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 8. Prepara i dati per il modello
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
            date = request.data.get('date')
            if date:
                card_data['date'] = datetime.strptime(date, "%Y-%m-%d").date()
        elif date_type == 'range':
            date_start = request.data.get('dateStart')
            date_end = request.data.get('dateEnd')
            if date_start:
                card_data['date_start'] = datetime.strptime(date_start, "%Y-%m-%d").date()
            if date_end:
                card_data['date_end'] = datetime.strptime(date_end, "%Y-%m-%d").date()
        
        # 9. Crea la card
        card = Card.objects.create(**card_data)

        # 10. Salva eventuali allegati (galleria)
        gallery_files = request.FILES.getlist('galleryFiles')
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


@api_view(['GET'])
def get_card(request, slug):
    """
    Recupera una singola card per slug
    """
    try:
        card = Card.objects.get(slug=slug, is_published=True)
        
        # Incrementa views
        card.views_count += 1
        card.save(update_fields=['views_count'])
        
        serializer = CardSerializer(card)
        return Response(serializer.data)
    except Card.DoesNotExist:
        return Response(
            {'error': 'Card non trovata'},
            status=status.HTTP_404_NOT_FOUND
        )


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
