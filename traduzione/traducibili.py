"""Cosa si traduce, e di che genere e'.

Un elenco solo, esplicito. Prima erano tre: le colonne `translated_*` di
quattro tabelle, i `campi_tradotti` di cinque serializer, e i
`translatable_fields` che wagtail-localize si autogenerava. Quest'ultimo
includeva anche `slug`, che nessuno voleva tradurre — ed e' il motivo per cui
qui si scrive cosa si traduce invece di dedurlo: **cio' che non e' scritto non
si traduce.**

Per la stessa ragione non compaiono `external_url`, `external_email`, `key`,
`icon`, `accent`, `surface`: sono identificatori e indirizzi, non testo.
"""

from traduzione.generi import DIZIONARIO, DOCUMENTO, FLUSSO, RICCO, TESTO

TRADUCIBILI: dict[str, dict[str, object]] = {
    # --- Cio' che scrivono gli utenti ---------------------------------------
    'section.Card': {
        'title': TESTO,
        'subtitle': TESTO,
        'location': TESTO,
        'info_values': DIZIONARIO,
        'body': DOCUMENTO,
    },
    'forum.Post': {
        'title': TESTO,
        'description': TESTO,
        # Non era mai stato tradotto: in inglese si leggevano titolo e
        # sommario tradotti e il corpo in italiano.
        'content_html': RICCO,
    },
    'forum.Comment': {
        'text': TESTO,
    },
    'chat.Message': {
        'body': TESTO,
    },

    # --- Cio' che scrive l'admin --------------------------------------------
    'cms.HomePage': {
        'title': TESTO,
        'seo_title': TESTO,
        'search_description': TESTO,
        'body': FLUSSO,
    },
    'cms.StandardPage': {
        'title': TESTO,
        'seo_title': TESTO,
        'search_description': TESTO,
        'body': FLUSSO,
    },
    'cms.ArticleType': {
        'name': TESTO,
        'name_plural': TESTO,
        'description': TESTO,
        'new_article_label': TESTO,
    },
    'cms.ArticleTypeInfoElement': {'label': TESTO},
    'cms.ArticleTypeTag': {'label': TESTO},
    'cms.Menu': {'name': TESTO},
    'cms.MenuItem': {'label': TESTO},
    'cms.GeoArea': {'name': TESTO},
}


def etichetta(modello) -> str:
    return f'{modello._meta.app_label}.{modello.__name__}'


def campi_di(oggetto) -> dict[str, object]:
    """I campi traducibili di questo oggetto, o vuoto se non e' traducibile.

    Si guarda anche alle classi da cui eredita: una `Page` arriva spesso come
    istanza generica e si specializza con `.specific`, e i due percorsi devono
    dare la stessa risposta.
    """
    for classe in type(oggetto).__mro__:
        meta = getattr(classe, '_meta', None)
        if meta is None:
            continue
        dichiarati = TRADUCIBILI.get(f'{meta.app_label}.{classe.__name__}')
        if dichiarati:
            return dichiarati
    return {}


def e_traducibile(oggetto) -> bool:
    return bool(campi_di(oggetto))


def modelli():
    """Le classi dichiarate, risolte. Utile ai controlli e ai comandi."""
    from django.apps import apps
    risolti = []
    for chiave in TRADUCIBILI:
        app_label, nome = chiave.split('.')
        try:
            risolti.append(apps.get_model(app_label, nome))
        except LookupError:
            continue
    return risolti
