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

from traduzione import lingue

from cms import vocabularies as vocab
from cms.models import ArticleType, GeoArea, Menu
from cms.blocks import percorso_pagina


def _codice_lingua(request) -> str:
    """Codice della lingua richiesta, se e' una lingua che serviamo.

    Le lingue attive stanno in `traduzione.Lingua`, una riga per lingua,
    aggiunta dal pannello: non serve piu' che qualcuno crei anche un Locale di
    Wagtail perche' un contenuto si veda tradotto.
    """
    richiesta = request.GET.get('locale') or get_language() or ''
    return lingue.normalizza(richiesta) or settings.LANGUAGE_CODE.split('-')[0]


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
def languages(request):
    """Le lingue in cui il sito si legge.

    Il selettore del frontend ne mostra l'intersezione con quelle di cui
    esistono anche le etichette dell'app: una lingua compare quando entrambe le
    meta' ci sono, e mai prima.
    """
    from traduzione.models import Lingua
    attive = Lingua.objects.filter(attiva=True).order_by('ordine', 'codice')
    return Response({
        'languages': [{'code': l.codice, 'name': l.nome} for l in attive],
        'default': settings.LANGUAGE_CODE.split('-')[0],
    })


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


def serializza_pagina(pagina, anteprima=False) -> dict:
    """Una pagina nella forma che il frontend sa disegnare.

    Il corpo e' una lista di blocchi {type, id, value}: il renderer React
    smista per `type` e passa `value` al componente corrispondente. Non viene
    mai generato HTML di impaginazione — solo dati — ed e' questo che tiene il
    design system fuori dalla portata di chi compone le pagine.
    """
    corpo = pagina.body
    return {
        'id': pagina.id,
        'title': pagina.title,
        'slug': pagina.slug,
        'path': percorso_pagina(pagina),
        'locale': pagina.locale.language_code,
        'type': pagina.__class__.__name__,
        'seo': {
            'title': pagina.seo_title or pagina.title,
            'description': pagina.search_description or '',
        },
        # La rappresentazione API la produce il BLOCCO, non il valore: e' il
        # blocco a sapere come si traduce ogni suo figlio.
        'body': corpo.stream_block.get_api_representation(corpo) if corpo else [],
        'preview': anteprima,
    }


@api_view(['GET'])
@permission_classes([AllowAny])
def page_by_path(request):
    """Risolve una pagina dal suo percorso: ?path=/partner

    E' la chiamata che fa la rotta catch-all di Next: un solo file di pagina
    serve tutte le pagine del CMS, comprese quelle create dopo l'ultimo deploy.
    """
    from wagtail.models import Page, Site

    percorso = (request.GET.get('path') or '/').strip()
    if not percorso.startswith('/'):
        percorso = '/' + percorso
    locale = _risolvi_locale(request)

    sito = Site.objects.filter(is_default_site=True).first()
    if not sito:
        return Response({'detail': 'Nessun sito configurato.'}, status=500)

    radice = sito.root_page.localized if hasattr(sito.root_page, 'localized') else sito.root_page
    if percorso == '/':
        pagina = radice
    else:
        url_path = radice.url_path.rstrip('/') + percorso + '/'
        pagina = Page.objects.filter(url_path=url_path, locale=locale).first()
        if pagina is None:
            pagina = Page.objects.filter(url_path=url_path).first()

    if pagina is None or not pagina.live:
        return Response({'detail': 'Pagina non trovata.'}, status=404)

    return Response(serializza_pagina(pagina.specific))


@api_view(['GET'])
@permission_classes([AllowAny])
def page_paths(request):
    """Tutti i percorsi pubblicati.

    Serve a generateStaticParams quando si accendera' la generazione statica:
    esporlo ora non costa nulla ed evita di doverci tornare.
    """
    from wagtail.models import Page, Site

    sito = Site.objects.filter(is_default_site=True).first()
    if not sito:
        return Response({'paths': []})
    pagine = (Page.objects.live().descendant_of(sito.root_page, inclusive=True)
              .order_by('path'))
    return Response({'paths': [percorso_pagina(p) for p in pagine]})


@api_view(['GET'])
@permission_classes([AllowAny])
def preview(request):
    """Contenuto di una bozza, per l'anteprima headless.

    Il token e' quello che Wagtail genera aprendo l'anteprima: identifica la
    revisione non pubblicata e scade da solo. Non e' un accesso ai contenuti
    riservati — e' un collegamento monouso a una bozza specifica.
    """
    from wagtail_headless_preview.models import PagePreview

    token = request.GET.get('token')
    if not token:
        return Response({'detail': 'Token mancante.'}, status=400)
    anteprima = PagePreview.objects.filter(token=token).first()
    if anteprima is None:
        return Response({'detail': 'Anteprima scaduta o inesistente.'}, status=404)
    return Response(serializza_pagina(anteprima.as_page(), anteprima=True))
