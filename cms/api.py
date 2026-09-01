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

from django.conf import settings
from django.utils.translation import get_language
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from wagtail.models import Locale

from cms import vocabularies as vocab
from cms.models import ArticleType, GeoArea, Menu


def _codice_lingua(request) -> str:
    """Codice della lingua richiesta, validato sulle lingue configurate.

    Diverso da `_risolvi_locale`: quello serve ai contenuti legati a una riga
    Locale di Wagtail (che esiste solo dopo che la lingua e' stata aggiunta in
    admin). Le traduzioni della tassonomia geografica stanno invece in un
    JSONField, quindi basta il codice — e funzionano appena la lingua e'
    configurata, senza aspettare che qualcuno crei il Locale.
    """
    ammesse = {c for c, _ in settings.WAGTAIL_CONTENT_LANGUAGES}
    richiesta = (request.GET.get('locale') or get_language() or '').split('-')[0]
    if richiesta in ammesse:
        return richiesta
    return settings.LANGUAGE_CODE.split('-')[0]


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


def _albero(nodi, per_parent, locale_code):
    return [
        {
            'key': n.key,
            'name': n.label(locale_code),
            'level': n.level,
            'code': n.code or None,
            'path': n.path,
            'children': _albero(per_parent.get(n.pk, []), per_parent, locale_code),
        }
        for n in nodi
    ]


@api_view(['GET'])
@permission_classes([AllowAny])
def geo_areas(request):
    """L'albero geografico completo.

    Una sola query: l'albero si costruisce in memoria. Sono ~130 nodi, e
    servirli tutti insieme evita al frontend una chiamata per ogni livello
    mentre l'utente naviga il selettore.
    """
    codice = _codice_lingua(request)

    tutti = list(GeoArea.objects.filter(is_active=True).order_by('sort_order', 'name'))
    per_parent: dict = {}
    radici = []
    for n in tutti:
        (radici if n.parent_id is None else per_parent.setdefault(n.parent_id, [])).append(n)

    payload = {'locale': codice, 'areas': _albero(radici, per_parent, codice)}
    grezzo = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode('utf-8')
    payload['version'] = hashlib.sha256(grezzo).hexdigest()[:16]

    resp = Response(payload)
    resp['ETag'] = f'"{payload["version"]}"'
    resp['Cache-Control'] = 'public, max-age=300'
    return resp


def _serializza_voce(voce, menu_per_id, profondita=0):
    dati = {
        'label': voce.label,
        'href': voce.href,
        'icon': voce.icon or None,
        'visibility': voce.visibility,
        'roles': list(voce.roles or []),
        'newTab': voce.open_in_new_tab,
        'children': [],
    }
    # Un solo livello di annidamento: la tendina "Esplora" e' un menu, non un
    # albero. Piu' livelli in una barra di navigazione sono difficili da usare e
    # impossibili su mobile.
    if voce.submenu_id and profondita == 0:
        figlio = menu_per_id.get(voce.submenu_id)
        if figlio:
            dati['children'] = [
                _serializza_voce(v, menu_per_id, profondita + 1)
                for v in figlio.items.all()
            ]
    return dati


@api_view(['GET'])
@permission_classes([AllowAny])
def navigation(request):
    """Tutti i menu, con i sottomenu gia' espansi.

    Il frontend riceve una struttura pronta da disegnare: non deve sapere che
    "Esplora" e' un menu a se' referenziato da un altro, ne' fare una seconda
    chiamata per averlo.
    """
    locale = _risolvi_locale(request)
    menus = (Menu.objects.filter(locale=locale)
             .prefetch_related('items', 'items__page'))
    per_id = {m.pk: m for m in menus}

    payload = {
        'locale': locale.language_code,
        'menus': {
            m.key: {
                'name': m.name,
                'items': [_serializza_voce(v, per_id) for v in m.items.all()],
            }
            for m in menus
        },
    }
    grezzo = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode('utf-8')
    payload['version'] = hashlib.sha256(grezzo).hexdigest()[:16]

    resp = Response(payload)
    resp['ETag'] = f'"{payload["version"]}"'
    resp['Cache-Control'] = 'public, max-age=60'
    return resp
