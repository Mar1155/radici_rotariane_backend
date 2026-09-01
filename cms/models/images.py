"""Modelli custom per immagini e documenti Wagtail.

Definiti fin dal primo giorno anche se oggi non aggiungono campi: sostituire
i modelli predefiniti *dopo* che esistono contenuti è una migrazione lunga e
fastidiosa, mentre farlo ora costa una riga di settings. Da qui in poi si
possono aggiungere campi (crediti fotografici, licenza d'uso, area geografica)
senza toccare l'infrastruttura.
"""

from django.db import models
from wagtail.documents.models import AbstractDocument, Document
from wagtail.images.models import AbstractImage, AbstractRendition, Image


class CMSImage(AbstractImage):
    # Il credito fotografico serve quasi sempre sulle immagini editoriali e
    # non esiste nel modello base.
    credit = models.CharField(max_length=255, blank=True, verbose_name='crediti')

    admin_form_fields = Image.admin_form_fields + ('credit',)

    class Meta(AbstractImage.Meta):
        verbose_name = 'immagine'
        verbose_name_plural = 'immagini'


class CMSRendition(AbstractRendition):
    image = models.ForeignKey(
        CMSImage, on_delete=models.CASCADE, related_name='renditions'
    )

    class Meta:
        unique_together = (('image', 'filter_spec', 'focal_point_key'),)


class CMSDocument(AbstractDocument):
    admin_form_fields = Document.admin_form_fields

    class Meta(AbstractDocument.Meta):
        verbose_name = 'documento'
        verbose_name_plural = 'documenti'
