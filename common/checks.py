"""Cosa manca perche' la webapp funzioni davvero, detto al deploy.

Ognuna di queste configurazioni, se assente, lascia la webapp in piedi: parte,
risponde, sembra a posto. Si rompe un pezzo alla volta, e in silenzio — una
registrazione che non arriva mai, un'immagine che sparisce al riavvio. Il
posto giusto per accorgersene e' `manage.py check --deploy`, prima di
pubblicare, non la segnalazione di un utente una settimana dopo.

Tacciono tutte in sviluppo: con DEBUG acceso nessuna di queste manca per
sbaglio.
"""

from django.conf import settings
from django.core.checks import Warning, register


def _vuoto(nome: str) -> bool:
    return not (getattr(settings, nome, '') or '').strip()


@register('deploy')
def controlla_produzione(app_configs, **kwargs):
    if settings.DEBUG:
        return []

    problemi = []

    if ('smtp' in settings.EMAIL_BACKEND.lower()) and _vuoto('EMAIL_HOST_USER'):
        problemi.append(Warning(
            'EMAIL_HOST_USER non e\' configurato.',
            hint='La registrazione richiede un codice inviato per email. Senza '
                 'SMTP il codice non parte, la registrazione risulta riuscita '
                 'e nessun utente nuovo riesce mai a entrare.',
            id='deploy.W001'))

    if not settings.CSRF_TRUSTED_ORIGINS:
        problemi.append(Warning(
            'CSRF_TRUSTED_ORIGINS e\' vuoto.',
            hint='Dietro un proxy HTTPS il login a /cms/ viene rifiutato con '
                 '"CSRF verification failed": l\'admin non entra nel pannello.',
            id='deploy.W002'))

    if not getattr(settings, 'USE_S3', False):
        problemi.append(Warning(
            'USE_S3 non e\' attivo.',
            hint='I file caricati finiscono sul disco del container e spariscono '
                 'al primo riavvio, insieme alle immagini delle pagine.',
            id='deploy.W003'))

    if getattr(settings, 'TRANSLATION_ENGINE', '') == 'claude' and _vuoto('ANTHROPIC_API_KEY'):
        problemi.append(Warning(
            'ANTHROPIC_API_KEY non e\' configurata.',
            hint='I contenuti restano nella lingua in cui sono stati scritti e '
                 'si accumulano nella coda di revisione. Il sito funziona.',
            id='deploy.W004'))

    if getattr(settings, 'FRONTEND_BASE_URL', '') and _vuoto('REVALIDATE_SECRET'):
        problemi.append(Warning(
            'REVALIDATE_SECRET non e\' configurato.',
            hint='Pubblicando dal CMS il frontend non svuota la cache: chi '
                 'pubblica ricarica, vede la versione vecchia e conclude che '
                 'il salvataggio non abbia funzionato.',
            id='deploy.W005'))

    return problemi
