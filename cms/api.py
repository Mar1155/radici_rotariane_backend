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



def tradotto(oggetto, lingua: str | None) -> dict:
    """I campi dell'oggetto nella lingua richiesta, o vuoto.

    Si ricade sull'originale per costruzione: cio' che non e' tradotto non
    compare qui, e il chiamante usa il valore che ha gia'. E' la differenza
    con il filtro per locale di prima, che non trovando la riga nella lingua
    giusta restituiva il vuoto invece dell'italiano.
    """
    if not lingua:
        return {}
    from traduzione.percorsi import applica
    from traduzione.servizio import lingua_di_stesura, traduzione_di
    if lingua == lingua_di_stesura(oggetto):
        return {}
    t = traduzione_di(oggetto, lingua)
    return applica(oggetto, t.texts) if t is not None else {}


def serializza_tipo(t: ArticleType, lingua: str | None = None) -> dict:
    tr = tradotto(t, lingua)
    return {
        'key': t.key,
        'name': tr.get('name') or t.name,
        'namePlural': tr.get('name_plural') or t.name_plural,
        'description': tr.get('description') or t.description,
        'fields': {
            'active': list(t.active_fields or []),
            'required': list(t.required_fields or []),
        },
        'infoElements': [
            {'key': i.key, 'icon': i.icon,
             'label': tradotto(i, lingua).get('label') or i.label}
            for i in t.info_elements.all()
        ],
        'tags': [
            {'key': g.key, 'label': tradotto(g, lingua).get('label') or g.label}
            for g in t.allowed_tags.all()
        ],
        'buttons': list(t.buttons or []),
        'columns': t.default_columns,
        'canPublish': list(t.can_publish or []),
        'newArticleLabel': tr.get('new_article_label') or t.create_label,
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
    lingua = _codice_lingua(request)
    qs = (ArticleType.objects
          .prefetch_related('info_elements', 'allowed_tags', 'traduzioni',
                            'info_elements__traduzioni', 'allowed_tags__traduzioni')
          .order_by('name'))

    payload = {
        'locale': lingua,
        'articleTypes': [serializza_tipo(t, lingua) for t in qs],
        # I vocabolari viaggiano con la risposta cosi' il frontend non li
        # ridichiara: sono un contratto, e un contratto con due copie diverge.
        #
        # Le CHIAVI sono il contratto; le ETICHETTE no. Prima viaggiavano qui,
        # in italiano e basta, e in inglese si leggeva "Leggi articolo" su un
        # sito per il resto tradotto. Non era una traduzione mancante: era
        # testo dell'app nel posto sbagliato. Ora stanno in intlayer.
        'vocabularies': {
            'fields': list(vocab.FIELD_KEYS),
            'buttons': list(vocab.BUTTON_KEYS),
            'roles': list(vocab.ROLE_KEYS),
            'icons': vocab.ICON_KEYS,
            'layouts': [k for k, _ in vocab.LAYOUT_CHOICES],
            'bodyBlocks': [k for k, _ in vocab.BODY_BLOCK_CHOICES],
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


def _serializza_voce(voce, menu_per_id, profondita=0, lingua=None):
    dati = {
        'label': tradotto(voce, lingua).get('label') or voce.label,
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
    lingua = _codice_lingua(request)
    menus = (Menu.objects
             .prefetch_related('items', 'items__page', 'traduzioni',
                               'items__traduzioni'))
    per_id = {m.pk: m for m in menus}

    payload = {
        'locale': lingua,
        'menus': {
            m.key: {
                'name': tradotto(m, lingua).get('name') or m.name,
                'items': [_serializza_voce(v, per_id, lingua=lingua)
                          for v in m.items.all()],
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


def serializza_pagina(pagina, anteprima=False, lingua=None) -> dict:
    """Una pagina nella forma che il frontend sa disegnare.

    Il corpo e' una lista di blocchi {type, id, value}: il renderer React
    smista per `type` e passa `value` al componente corrispondente. Non viene
    mai generato HTML di impaginazione — solo dati — ed e' questo che tiene il
    design system fuori dalla portata di chi compone le pagine.

    Una bozza in anteprima non ha traduzioni: si serve l'originale, perche' chi
    sta componendo deve vedere quello che sta scrivendo.
    """
    from traduzione.servizio import lingua_di_stesura
    tr = {} if anteprima else tradotto(pagina, lingua)
    corpo = pagina.body
    if 'body' in tr:
        # I testi tornano dentro i **dati grezzi**, che poi si riconvertono:
        # reinserirli nella rappresentazione API non funzionerebbe, perche'
        # quella butta via gli id degli item di lista e i percorsi non
        # coinciderebbero piu'.
        corpo = pagina.body.stream_block.to_python(tr['body'])
    return {
        'id': pagina.id,
        'title': tr.get('title') or pagina.title,
        'slug': pagina.slug,
        'path': percorso_pagina(pagina),
        'locale': lingua or pagina.locale.language_code,
        'translated_from': (lingua_di_stesura(pagina)
                            if tr and lingua != lingua_di_stesura(pagina) else None),
        'type': pagina.__class__.__name__,
        'seo': {
            'title': tr.get('seo_title') or pagina.seo_title or tr.get('title') or pagina.title,
            'description': tr.get('search_description') or pagina.search_description or '',
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
    lingua = _codice_lingua(request)

    sito = Site.objects.filter(is_default_site=True).first()
    if not sito:
        return Response({'detail': 'Nessun sito configurato.'}, status=500)

    radice = sito.root_page
    if percorso == '/':
        pagina = radice
    else:
        # Una sola pagina per percorso: non c'e' piu' un albero per lingua, la
        # traduzione sta a lato della riga.
        url_path = radice.url_path.rstrip('/') + percorso + '/'
        pagina = Page.objects.filter(url_path=url_path).first()

    if pagina is None or not pagina.live:
        return Response({'detail': 'Pagina non trovata.'}, status=404)

    return Response(serializza_pagina(pagina.specific, lingua=lingua))


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
