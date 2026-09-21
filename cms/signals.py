"""Invalidazione della cache del frontend quando il contenuto cambia.

Senza questo, una modifica pubblicata comparirebbe sul sito fino a un minuto
dopo — e siccome Next serve la copia vecchia mentre rigenera, la **prima**
ricarica mostrerebbe ancora il contenuto precedente. Chi pubblica ricarica,
vede la versione vecchia e conclude che il salvataggio non abbia funzionato.

La chiamata e' volutamente silenziosa sui fallimenti: se il frontend non
risponde, la pubblicazione deve comunque riuscire. Al massimo si torna al
comportamento di prima, cioe' l'aggiornamento entro un minuto.
"""

import logging

import requests
from django.conf import settings
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from wagtail.signals import page_published, page_unpublished

logger = logging.getLogger(__name__)

TIMEOUT = 3


def invalida(tags):
    base = getattr(settings, 'FRONTEND_BASE_URL', '')
    segreto = getattr(settings, 'REVALIDATE_SECRET', '')
    if not base or not segreto:
        return
    try:
        requests.post(
            f'{base.rstrip("/")}/api/revalidate',
            json={'tags': sorted(set(tags))},
            headers={'x-revalidate-secret': segreto},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        logger.warning('Invalidazione cache non riuscita: %s', exc)


@receiver(page_published)
@receiver(page_unpublished)
def su_pagina_pubblicata(sender, instance, **kwargs):
    from cms.blocks import percorso_pagina
    invalida(['cms-page', f'cms-page:{percorso_pagina(instance)}'])


def _tag_per_modello(modello) -> list[str] | None:
    nome = modello.__name__
    if nome == 'Traduzione':
        # Una traduzione corretta a mano deve comparire subito. Senza, si
        # aspetta un minuto — ed e' il problema per cui questo file esiste.
        return ['cms-page', 'article-types', 'navigation', 'geo-areas']
    return {
        'ArticleType': ['article-types'],
        'ArticleTypeInfoElement': ['article-types'],
        'ArticleTypeTag': ['article-types'],
        'GeoArea': ['geo-areas'],
        'Menu': ['navigation'],
        'MenuItem': ['navigation'],
    }.get(nome)


@receiver(post_save)
@receiver(post_delete)
def su_snippet_salvato(sender, **kwargs):
    tags = _tag_per_modello(sender)
    if tags:
        invalida(tags)
