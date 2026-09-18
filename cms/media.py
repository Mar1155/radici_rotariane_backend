"""Indirizzi dei file caricati.

Sta qui e non dentro i blocchi Wagtail perche' serve a chiunque restituisca un
file al frontend: le pagine del CMS, le copertine degli articoli, le immagini
dentro il corpo di un articolo.
"""

from django.conf import settings


def url_assoluto(url: str) -> str:
    """Rende assoluto un URL di media.

    Con S3 gli URL sono gia' assoluti; con lo storage su disco sono relativi
    (`/media/...`), e il frontend gira su un'altra porta: un URL relativo
    verrebbe cercato sul server Next, dove non c'e' nulla.
    """
    if not url or url.startswith(('http://', 'https://', '//')):
        return url
    base = (getattr(settings, 'MEDIA_BASE_URL', '')
            or getattr(settings, 'WAGTAILADMIN_BASE_URL', '') or '')
    return f'{base.rstrip("/")}{url}' if base else url
