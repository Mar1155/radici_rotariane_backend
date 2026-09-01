"""API di lettura della struttura dei contenuti.

Una sola chiamata sostituisce i quattro moduli TypeScript che oggi vivono in
`app/scopri/config/`. Il frontend non deve piu' conoscere staticamente i tipi
di articolo: li chiede, e chiedendoli scopre anche quelli che l'admin ha creato
dopo l'ultimo deploy.

Lettura pubblica: le liste di articoli sono visibili anche a chi non ha fatto
accesso, quindi il frontend deve poter disegnare le card senza autenticazione.
"""

import hashlib
import json

from django.utils.translation import get_language
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from wagtail.models import Locale

from cms import vocabularies as vocab
from cms.models import ArticleType


def _risolvi_locale(request):
    """Locale richiesto, con fallback su quello di default."""
    codice = (request.GET.get('locale') or get_language() or '').split('-')[0]
    if codice:
        loc = Locale.objects.filter(language_code=codice).first()
        if loc:
            return loc
    return Locale.get_default()


def serializza_tipo(t: ArticleType) -> dict:
    return {
        'key': t.key,
        'name': t.name,
        'namePlural': t.name_plural,
        'description': t.description,
        'fields': {
            'active': list(t.active_fields or []),
            'required': list(t.required_fields or []),
        },
        'infoElements': [
            {'key': i.key, 'icon': i.icon, 'label': i.label}
            for i in t.info_elements.all()
        ],
        'tags': [
            {'key': g.key, 'label': g.label}
            for g in t.allowed_tags.all()
        ],
        'buttons': list(t.buttons or []),
        'columns': t.default_columns,
        'canPublish': list(t.can_publish or []),
        'newArticleLabel': t.create_label,
        'bodyBlocks': list(t.body_blocks or []),
        'usesGeo': t.uses_geo,
        'external': {
            'url': t.external_url or None,
            'email': t.external_email or None,
            'phone': t.external_phone or None,
        },
    }


@api_view(['GET'])
@permission_classes([AllowAny])
def article_types(request):
    locale = _risolvi_locale(request)
    qs = (ArticleType.objects.filter(locale=locale)
          .prefetch_related('info_elements', 'allowed_tags')
          .order_by('name'))

    payload = {
        'locale': locale.language_code,
        'articleTypes': [serializza_tipo(t) for t in qs],
        # I vocabolari viaggiano con la risposta cosi' il frontend non li
        # ridichiara: sono un contratto, e un contratto con due copie diverge.
        'vocabularies': {
            'fields': [{'key': k, 'label': l} for k, l in vocab.FIELD_CHOICES],
            'buttons': [{'key': k, 'label': l} for k, l in vocab.BUTTON_CHOICES],
            'roles': [{'key': k, 'label': l} for k, l in vocab.ROLE_CHOICES],
            'icons': vocab.ICON_KEYS,
            'layouts': [{'key': k, 'label': l} for k, l in vocab.LAYOUT_CHOICES],
            'bodyBlocks': [{'key': k, 'label': l} for k, l in vocab.BODY_BLOCK_CHOICES],
        },
    }
    # ETag calcolato sul contenuto: nessuna colonna in piu' sul modello, e
    # cambia esattamente quando cambia la risposta.
    grezzo = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode('utf-8')
    payload['version'] = hashlib.sha256(grezzo).hexdigest()[:16]

    resp = Response(payload)
    resp['ETag'] = f'"{payload["version"]}"'
    resp['Cache-Control'] = 'public, max-age=60'
    return resp
