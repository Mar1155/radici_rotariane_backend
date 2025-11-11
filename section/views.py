# views.py
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from .models import Card
from .serializers import CardSerializer
import json


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def create_card(request):
    """
    Crea una nuova card dal form Next.js
    """
    try:
        # Estrai i dati dal FormData
        title = request.data.get('title')
        subtitle = request.data.get('subtitle')
        cover_image = request.FILES.get('coverImage')
        tags_json = request.data.get('tags')
        content = request.data.get('content')
        date_type = request.data.get('dateType')
        
        # Parse tags da JSON string
        tags = json.loads(tags_json) if tags_json else []
        
        # Validazione base
        if not title or not subtitle or not cover_image or not content:
            return Response(
                {'error': 'Titolo, sottotitolo, immagine e contenuto sono obbligatori'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Prepara i dati per il modello
        card_data = {
            'title': title,
            'subtitle': subtitle,
            'cover_image': cover_image,
            'tags': tags,
            'content': content,
            'date_type': date_type,
            'author': request.user if request.user.is_authenticated else None,
        }
        
        # Aggiungi date in base al tipo
        if date_type == 'single':
            date = request.data.get('date')
            if date:
                card_data['date'] = date
        elif date_type == 'range':
            date_start = request.data.get('dateStart')
            date_end = request.data.get('dateEnd')
            if date_start and date_end:
                card_data['date_start'] = date_start
                card_data['date_end'] = date_end
        
        # Crea la card
        card = Card.objects.create(**card_data)
        
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
            {'error': 'Formato tags non valido'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': f'Errore durante la creazione: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def list_cards(request):
    """
    Lista tutte le cards pubblicate
    """
    cards = Card.objects.filter(is_published=True)
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