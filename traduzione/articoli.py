"""Tradurre un articolo.

Il corpo non passa dal traduttore come markup: si estraggono i nodi di testo
col loro percorso, si traducono insieme ai campi brevi, e si rimettono dove
stavano. La formattazione — grassetti, link, immagini — non viene mai vista dal
traduttore, quindi non puo' corrompersi. E' il motivo per cui il corpo di un
articolo e' un documento e non HTML.
"""

from __future__ import annotations

import logging

from django.conf import settings

from traduzione import lingue
from django.db import transaction

from section.models import Card, CardTranslation
from section.schema import estrai_testi, reinserisci_testi

from .motori import MotoreTraduzione, motore

logger = logging.getLogger(__name__)

# Prefissi con cui i campi brevi entrano nella mappa da tradurre, cosi' viaggiano
# insieme al corpo: il traduttore vede titolo e testo nella stessa richiesta e
# puo' essere coerente fra l'uno e l'altro.
CAMPO_TITOLO = 'campo:title'
CAMPO_SOTTOTITOLO = 'campo:subtitle'
CAMPO_LUOGO = 'campo:location'
PREFISSO_INFO = 'info:'
PREFISSO_CORPO = 'corpo:'


def lingue_di_destinazione(card: Card) -> list[str]:
    """Le lingue in cui questo articolo va tradotto: tutte tranne la sua."""
    return lingue.altre_lingue(card.source_locale)


def _da_tradurre(card: Card) -> dict[str, str]:
    testi: dict[str, str] = {}
    if card.title:
        testi[CAMPO_TITOLO] = card.title
    if card.subtitle:
        testi[CAMPO_SOTTOTITOLO] = card.subtitle
    if card.location:
        testi[CAMPO_LUOGO] = card.location
    for chiave, valore in (card.info_values or {}).items():
        if str(valore).strip():
            testi[f'{PREFISSO_INFO}{chiave}'] = str(valore)
    for percorso, testo in estrai_testi(card.body).items():
        testi[f'{PREFISSO_CORPO}{percorso}'] = testo
    return testi


def traduci_articolo(card: Card, lingua: str,
                     m: MotoreTraduzione | None = None) -> CardTranslation | None:
    """Traduce l'articolo in una lingua e salva il risultato.

    Non tocca una traduzione corretta a mano: chi l'ha scritta ne sapeva piu'
    della macchina. Restituisce `None` se non c'era niente da tradurre.
    """
    esistente = CardTranslation.objects.filter(
        card=card, target_language=lingua).first()
    if esistente and esistente.human_locked:
        logger.info('Traduzione %s di %s corretta a mano: non la tocco.',
                    lingua, card.slug)
        return esistente

    testi = _da_tradurre(card)
    if not testi:
        return None

    m = m or motore()
    tradotti = m.traduci(testi, da=(card.source_locale or 'it'), a=lingua)

    corpo = {chiave[len(PREFISSO_CORPO):]: valore
             for chiave, valore in tradotti.items()
             if chiave.startswith(PREFISSO_CORPO)}
    info = {chiave[len(PREFISSO_INFO):]: valore
            for chiave, valore in tradotti.items()
            if chiave.startswith(PREFISSO_INFO)}

    with transaction.atomic():
        traduzione, _ = CardTranslation.objects.update_or_create(
            card=card, target_language=lingua,
            defaults={
                'translated_title': tradotti.get(CAMPO_TITOLO, '') or '',
                'translated_subtitle': tradotti.get(CAMPO_SOTTOTITOLO, '') or '',
                'translated_location': tradotti.get(CAMPO_LUOGO, '') or '',
                'translated_body': reinserisci_testi(card.body, corpo) if card.body else None,
                'translated_info_values': info,
                'provider': m.nome,
                'detected_source_language': card.source_locale or 'it',
                'needs_review': m.da_rivedere,
                'human_locked': False,
            },
        )
    return traduzione


def traduci_in_tutte_le_lingue(card: Card, m: MotoreTraduzione | None = None) -> int:
    """Traduce l'articolo in tutte le lingue registrate. Torna quante ne ha fatte.

    Tutti i campi e tutte le lingue insieme: una traduzione a macchia di
    leopardo — titolo tradotto e corpo no — e' peggio di nessuna traduzione,
    perche' il lettore non capisce cosa stia guardando.
    """
    m = m or motore()
    fatte = 0
    for lingua in lingue_di_destinazione(card):
        try:
            if traduci_articolo(card, lingua, m):
                fatte += 1
        except Exception as e:
            # Una lingua che fallisce non deve impedire le altre, e soprattutto
            # non deve far fallire la pubblicazione.
            logger.exception('Traduzione di %s in %s non riuscita: %s',
                             card.slug, lingua, e)
    return fatte
