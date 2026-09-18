"""I motori di traduzione, dietro una sola interfaccia.

La scelta sta in `TRANSLATION_ENGINE`; il resto del codice non sa quale motore
stia usando. Serve perche' i motori hanno caratteristiche diverse e la scelta
puo' cambiare: un modello linguistico rispetta un glossario in prosa, un
servizio di traduzione classico no, ma costa meno ed e' gia' configurato.

La chat e il forum NON passano di qui: restano su `chat/services/translation.py`
con DeepL. Sono conversazioni, non documenti, e mescolarli significherebbe far
dipendere una chat dal glossario del Rotary.
"""

from __future__ import annotations

import json
import logging

from django.conf import settings

from .glossario import REGOLE

logger = logging.getLogger(__name__)

# Cosa restituisce un motore: le stesse chiavi che ha ricevuto.
Testi = dict[str, str]


class TraduzioneNonConfigurata(RuntimeError):
    """Manca la chiave, o il motore scelto non esiste."""


class MotoreTraduzione:
    """Traduce una mappa chiave -> testo, restituendo le stesse chiavi.

    Lavorare a mappa e non a stringa singola serve a due cose: il motore vede
    tutto il documento insieme, quindi puo' essere coerente fra un paragrafo e
    l'altro; e le chiavi permettono di verificare che non ne abbia perse.
    """

    nome = 'astratto'
    #: Se le traduzioni prodotte vanno segnate come da rivedere.
    da_rivedere = False

    def traduci(self, testi: Testi, da: str, a: str) -> Testi:
        raise NotImplementedError


class MotoreIdentita(MotoreTraduzione):
    """Restituisce il testo com'e'. E' il motore quando non ce n'e' uno.

    Non solleva un'eccezione apposta: senza chiave configurata il sito deve
    continuare a funzionare, con le traduzioni segnate come da fare. Un articolo
    visibile in italiano a un lettore inglese e' meglio di un articolo assente.
    """

    nome = 'identita'
    da_rivedere = True

    def traduci(self, testi: Testi, da: str, a: str) -> Testi:
        logger.warning(
            'Nessun motore di traduzione configurato: il testo resta in %s. '
            'Imposta ANTHROPIC_API_KEY e TRANSLATION_ENGINE=claude.', da)
        return dict(testi)


class MotoreClaude(MotoreTraduzione):
    """Traduzione con un modello linguistico, guidata dal glossario.

    Chiede e riceve JSON con le stesse chiavi, e verifica che tornino: un
    modello che ne inventa o ne perde ha frainteso il compito, e in quel caso e'
    meglio accorgersene che salvare un documento con dei buchi.
    """

    nome = 'claude'

    def __init__(self, api_key: str, modello: str | None = None):
        self.api_key = api_key
        self.modello = modello or getattr(
            settings, 'TRANSLATION_MODEL', 'claude-opus-5')

    def traduci(self, testi: Testi, da: str, a: str) -> Testi:
        if not testi:
            return {}
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)
        risposta = client.messages.create(
            model=self.modello,
            max_tokens=8000,
            system=[{
                'type': 'text',
                'text': REGOLE,
                # Il glossario e' identico a ogni chiamata: metterlo in cache
                # evita di pagarlo ogni volta.
                'cache_control': {'type': 'ephemeral'},
            }],
            messages=[{
                'role': 'user',
                'content': (
                    f'Traduci da {da} a {a} i valori di questo oggetto JSON.\n'
                    'Rispondi SOLO con un oggetto JSON che ha ESATTAMENTE le '
                    'stesse chiavi, e come valori le traduzioni.\n\n'
                    + json.dumps(testi, ensure_ascii=False, indent=1)
                ),
            }],
        )

        grezzo = ''.join(b.text for b in risposta.content if b.type == 'text')
        tradotti = self._estrai_json(grezzo)

        mancanti = set(testi) - set(tradotti)
        se_di_troppo = set(tradotti) - set(testi)
        if mancanti or se_di_troppo:
            raise ValueError(
                f'Il traduttore ha cambiato le chiavi: {len(mancanti)} perse, '
                f'{len(se_di_troppo)} inventate.')
        return {k: str(v) for k, v in tradotti.items()}

    @staticmethod
    def _estrai_json(testo: str) -> dict:
        testo = testo.strip()
        # A volte la risposta arriva dentro un blocco di codice.
        if testo.startswith('```'):
            testo = testo.split('\n', 1)[1].rsplit('```', 1)[0]
        return json.loads(testo)


def motore() -> MotoreTraduzione:
    """Il motore configurato, o quello di identita' se non ce n'e' uno."""
    scelta = (getattr(settings, 'TRANSLATION_ENGINE', '') or '').lower()
    chiave = getattr(settings, 'ANTHROPIC_API_KEY', '') or ''

    if scelta == 'claude':
        if not chiave:
            logger.warning('TRANSLATION_ENGINE=claude ma ANTHROPIC_API_KEY manca.')
            return MotoreIdentita()
        return MotoreClaude(chiave)
    if scelta in ('', 'nessuno', 'identita'):
        return MotoreIdentita()
    raise TraduzioneNonConfigurata(f'Motore di traduzione sconosciuto: {scelta!r}')
