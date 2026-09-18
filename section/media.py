"""Immagini degli articoli: caricamento, normalizzazione, deduplica.

Esiste per chiudere alla radice il problema che riempiva il database: l'editor
precedente non aveva un endpoint di caricamento, quindi ogni immagine incollata
finiva **dentro il testo** come base64. Su 44 card ne bastavano 41 per fare
7.039.633 caratteri a fronte di ~65 KB di testo vero, e una card da 171 KB non
si puo' nemmeno mandare a un servizio di traduzione.

La normalizzazione non e' cosmetica, e' la parte che protegge: un file che
viene decodificato e **ri-codificato** perde tutto cio' che non era pixel —
metadati EXIF, dati appesi in coda, file polyglot che sono immagine e script
insieme. Non ci si fida dell'estensione ne' del content-type dichiarati.
"""

from __future__ import annotations

import hashlib
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError

# Oltre questa soglia si ridimensiona: nessun articolo ha bisogno di piu', e
# una foto da telefono moderna arriva tranquillamente a 8000px.
LATO_MASSIMO = 2000

# Limite sul file in ingresso, prima ancora di aprirlo.
BYTE_MASSIMI = 12 * 1024 * 1024

# Formati che accettiamo in ingresso. In uscita c'e' solo WebP.
FORMATI_AMMESSI = {'JPEG', 'PNG', 'WEBP', 'GIF', 'BMP', 'TIFF'}


class ImmagineNonValida(ValidationError):
    """Il file non e' un'immagine che possiamo trattare."""


def normalizza(file) -> tuple[ContentFile, dict]:
    """Verifica, ri-codifica in WebP e restituisce (file, metadati).

    Solleva `ImmagineNonValida` se il file non e' un'immagine trattabile.
    """
    dati = file.read()
    if len(dati) > BYTE_MASSIMI:
        raise ImmagineNonValida(
            f'Immagine troppo grande: massimo {BYTE_MASSIMI // (1024 * 1024)} MB.')
    if not dati:
        raise ImmagineNonValida('File vuoto.')

    # `verify()` controlla l'integrita' ma consuma il file: va riaperto dopo.
    try:
        Image.open(BytesIO(dati)).verify()
    except (UnidentifiedImageError, OSError, ValueError) as e:
        raise ImmagineNonValida(f'Non e un immagine leggibile: {e}')

    img = Image.open(BytesIO(dati))
    if img.format not in FORMATI_AMMESSI:
        raise ImmagineNonValida(f'Formato non ammesso: {img.format}.')

    # La trasparenza si appiattisce su bianco: WebP la reggerebbe, ma un PNG
    # trasparente su fondo chiaro e uno su fondo scuro si comportano diversamente
    # e l'autore non se ne accorge finche' non e' pubblicato.
    if img.mode in ('RGBA', 'LA', 'P'):
        img = img.convert('RGBA')
        fondo = Image.new('RGB', img.size, (255, 255, 255))
        fondo.paste(img, mask=img.split()[-1])
        img = fondo
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    if max(img.size) > LATO_MASSIMO:
        img.thumbnail((LATO_MASSIMO, LATO_MASSIMO), Image.LANCZOS)

    buffer = BytesIO()
    img.save(buffer, format='WEBP', quality=82, method=4)
    contenuto = buffer.getvalue()

    return (
        ContentFile(contenuto, name='immagine.webp'),
        {
            'width': img.width,
            'height': img.height,
            'byte_size': len(contenuto),
            # Sul contenuto ri-codificato, non sull'originale: due file diversi
            # che producono la stessa immagine sono la stessa immagine.
            'checksum': hashlib.sha256(contenuto).hexdigest(),
        },
    )
