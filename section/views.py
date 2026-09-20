# views.py
from rest_framework import status
from rest_framework.decorators import (api_view, parser_classes,
                                       permission_classes, throttle_classes)
from common.throttling import Caricamento, Scrittura
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from users.permissions import ruolo_applicativo
from .media import ImmagineNonValida, normalizza
from .models import (Card, CardAttachment, CardReport, CardTranslation,
                     MediaAsset, SavedCard)
from .serializers import CardSerializer, CardListSerializer
from .schema import CorpoNonValido, pulisci_corpo, testo_semplice
from cms.models import GeoArea
from cms.media import url_assoluto
from cms.models import ArticleType
import json
from datetime import datetime
import traceback
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db import transaction
from common.richtext import sanitize_rich_text


def _area_geografica(chiave, tipo):
    """L'area scelta, se il tipo usa la geografia. `None` se non c'e'."""
    if not chiave or not tipo.uses_geo:
        return None
    return GeoArea.objects.filter(key=chiave, is_active=True).first()


def _puo_gestire(user, card) -> bool:
    """Chi ha scritto l'articolo, o un amministratore."""
    if not getattr(user, 'is_authenticated', False):
        return False
    if ruolo_applicativo(user) == 'admin':
        return True
    return bool(card.author_id and card.author_id == user.id)


def _corpo_da_richiesta(request, tipo):
    """Il corpo dell'articolo, ripulito contro la palette del suo tipo.

    Arriva come JSON dentro un FormData (l'articolo si invia insieme ai file),
    quindi puo' essere una stringa da decodificare o gia' un oggetto.
    """
    grezzo = request.data.get('body')
    if grezzo in (None, '', 'null'):
        return None
    if isinstance(grezzo, str):
        try:
            grezzo = json.loads(grezzo)
        except json.JSONDecodeError:
            raise CorpoNonValido('Il corpo non e JSON valido.')
    return pulisci_corpo(grezzo, tipo.body_blocks)


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
@throttle_classes([Scrittura])
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
        corpo = _corpo_da_richiesta(request, tipo)
        date_type = request.data.get('dateType', 'none')
        location = request.data.get('location')
        info_values_json = request.data.get('infoValues')
        geo_key = (request.data.get('geoArea') or '').strip()
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
        
        # 4. Validazione dei campi richiesti.
        #
        # Solo per cio' che si pubblica: una bozza incompleta e' il motivo per
        # cui esistono le bozze. Prima si validava comunque, e "salva bozza"
        # rispondeva chiedendo campi che stanno in un altro passo del form.
        pubblica = str(request.data.get('isPublished', 'true')).lower() != 'false'
        is_valid, error_msg = (True, None) if not pubblica else validate_article_fields(tipo, {
            'title': title, 'subtitle': subtitle, 'content': corpo,
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
            'body': corpo,
            'date_type': date_type,
            'location': location,
            'author': request.user,
            'info_values': info_values,
            # L'area geografica e' cio' su cui filtra la ricerca. Finora non era
            # impostabile da nessuna parte: la tassonomia e il filtro esistevano
            # dalla fase 4, ma un articolo scritto dall'app non poteva averla, e
            # quindi non compariva mai in un filtro per regione.
            'geo_area': _area_geografica(geo_key, tipo),
            # Il primo passo del form salva una bozza; il secondo pubblica.
            # Prima `is_published` esisteva come colonna ma non come flusso: un
            # articolo nasceva pubblicato, e non c'era modo di metterlo via.
            'is_published': pubblica,
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
        card = Card.objects.get(slug=slug)
        if request.method == 'GET' and not card.is_published:
            # Una bozza la vede solo chi l'ha scritta, e gli amministratori.
            if not _puo_gestire(request.user, card):
                raise Card.DoesNotExist
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

    if not _puo_gestire(request.user, card):
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
    corpo = _corpo_da_richiesta(request, card.article_type) if 'body' in data else card.body
    cover_image = request.FILES.get('coverImage') if 'coverImage' in request.FILES else card.cover_image
    tags = parse_json_field(data.get('tags'), None) if 'tags' in data else card.tags
    location = data.get('location') if 'location' in data else card.location
    info_values = parse_json_field(data.get('infoValues'), None) if 'infoValues' in data else card.info_values
    
    # Determina se c'è una data valida (per validazione)
    has_date = card.date or card.date_start  # Controlla se la card ha già date
    
    # Validazione solo di cio' che resta (o diventa) pubblicato: una bozza
    # incompleta e' il motivo per cui esistono le bozze.
    restera_pubblicato = (str(data.get('isPublished')).lower() != 'false'
                          if 'isPublished' in data else card.is_published)
    is_valid, error_msg = (True, None) if not restera_pubblicato else validate_article_fields(card.article_type, {
        'title': title, 'subtitle': subtitle, 'content': corpo,
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
    if 'body' in data:
        card.body = corpo
    if 'geoArea' in data:
        card.geo_area = _area_geografica((data.get('geoArea') or '').strip(),
                                         card.article_type)
    if 'isPublished' in data:
        card.is_published = str(data.get('isPublished')).lower() != 'false'
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

    cards_qs = (Card.objects.filter(author=target_user)
                .select_related('author', 'article_type'))

    # Le bozze le vede solo chi le ha scritte: a chiunque altro il profilo
    # mostra ciò che è pubblicato.
    # `stato` risparmia al client di scaricare tutto per poi filtrare, e tiene
    # qui la definizione di cos'è una bozza.
    stato = request.GET.get('stato')
    proprio = _puo_gestire(request.user, Card(author_id=target_user.id))
    if not proprio:
        # Chi guarda il profilo di un altro vede solo il pubblicato; se chiede
        # le bozze riceve un elenco vuoto, non il pubblicato al loro posto.
        cards_qs = (cards_qs.none() if stato == 'bozze'
                    else cards_qs.filter(is_published=True))
    elif stato == 'bozze':
        cards_qs = cards_qs.filter(is_published=False)
    elif stato == 'pubblicati':
        cards_qs = cards_qs.filter(is_published=True)

    if tipo_key:
        cards_qs = cards_qs.filter(article_type__key=tipo_key)
    # Le bozze si ordinano per ultima modifica: si riprende quella che si stava
    # scrivendo, non quella che si è cominciata per prima.
    cards_qs = cards_qs.order_by('-updated_at', '-created_at')

    serializer = CardListSerializer(cards_qs, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
@permission_classes([IsAuthenticated])
@throttle_classes([Caricamento])
def upload_media(request):
    """Carica un'immagine per il corpo di un articolo.

    E' il pezzo che impedisce alle immagini di tornare dentro il testo come
    base64: l'editor chiama questa, riceve un identificativo e lo mette nel
    documento. Prima non esisteva, e incollare una foto era l'unico modo.
    """
    file = request.FILES.get('file')
    if file is None:
        return Response({'error': 'Nessun file.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        contenuto, meta = normalizza(file)
    except ImmagineNonValida as e:
        return Response({'error': ' '.join(e.messages)},
                        status=status.HTTP_400_BAD_REQUEST)

    # Stessa immagine gia' caricata: si riusa invece di duplicare il file.
    asset = MediaAsset.objects.filter(checksum=meta['checksum']).first()
    creato = asset is None
    if creato:
        asset = MediaAsset(uploaded_by=request.user, **meta)
        asset.alt = (request.data.get('alt') or '')[:255]
        asset.file.save(f"{meta['checksum'][:16]}.webp", contenuto, save=True)

    return Response(
        {
            'id': asset.id,
            'url': url_assoluto(asset.file.url),
            'width': asset.width,
            'height': asset.height,
            'alt': asset.alt,
        },
        status=status.HTTP_201_CREATED if creato else status.HTTP_200_OK,
    )
