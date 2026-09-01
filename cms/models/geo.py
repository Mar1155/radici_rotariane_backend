"""Tassonomia geografica.

Un albero auto-referenziale nazione -> regione -> provincia -> comune, invece
di due tabelle separate: aggiungere il livello comune (o sovranazionale, per i
gemellaggi) non richiede una migrazione.

**Perche' non e' una lista piatta di tag.** Oggi la geografia sta fra i tag
tematici: sei province calabresi. Su scala nazionale sarebbero 107 province in
un menu a tendina, insieme a "enogastronomia" e "artigianato". Separare le due
cose permette di filtrare per regione e vedere anche gli articoli delle sue
province, cosa che una lista piatta non sa fare.

**Perche' le traduzioni sono un JSONField e non TranslatableMixin.** I nomi
geografici sono un vocabolario di riferimento fisso, non contenuto editoriale
con un flusso di revisione: con TranslatableMixin l'intero albero andrebbe
duplicato per lingua, con i parent che puntano dentro il proprio locale.
Aggiungere una lingua resta comunque senza migrazione, perche' e' una chiave in
piu' nel JSON. E' anche il modo in cui questo progetto tratta gia' le altre
tassonomie (users.Skill, users.FocusArea).
"""

from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.search import index

SEPARATORE = '/'


class GeoArea(index.Indexed, models.Model):
    class Livello(models.TextChoices):
        COUNTRY = 'country', 'Nazione'
        REGION = 'region', 'Regione'
        PROVINCE = 'province', 'Provincia'
        CITY = 'city', 'Comune'

    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='children', verbose_name='contenuto in',
    )
    level = models.CharField(max_length=12, choices=Livello.choices, verbose_name='livello')
    key = models.SlugField(max_length=80, verbose_name='chiave')
    name = models.CharField(max_length=120, verbose_name='nome')
    translations = models.JSONField(
        default=dict, blank=True, verbose_name='traduzioni',
        help_text='Nomi in altre lingue, es. {"en": "Apulia"}. '
                  'Se manca si usa il nome italiano.',
    )
    code = models.CharField(
        max_length=8, blank=True, verbose_name='sigla',
        help_text='Sigla della provincia (BA, MI) o codice della nazione (IT).',
    )
    # Percorso denormalizzato ('it/puglia/bari'): rende la ricerca dei
    # discendenti una startswith con indice, invece di una ricorsione.
    path = models.CharField(max_length=255, db_index=True, editable=False)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True, verbose_name='attiva')

    search_fields = [index.SearchField('name'), index.AutocompleteField('name')]

    panels = [
        FieldPanel('parent'), FieldPanel('level'), FieldPanel('key'),
        FieldPanel('name'), FieldPanel('code'), FieldPanel('translations'),
        FieldPanel('is_active'),
    ]

    class Meta:
        verbose_name = 'area geografica'
        verbose_name_plural = 'aree geografiche'
        ordering = ['path']
        constraints = [
            models.UniqueConstraint(fields=['parent', 'key'], name='uniq_geoarea_parent_key'),
        ]

    def __str__(self):
        return self.name

    # --- percorso -----------------------------------------------------------
    def calcola_path(self) -> str:
        return f'{self.parent.path}{SEPARATORE}{self.key}' if self.parent_id else self.key

    def save(self, *args, **kwargs):
        nuovo = self.calcola_path()
        cambiato = nuovo != self.path
        self.path = nuovo
        super().save(*args, **kwargs)
        # Se il percorso cambia, i discendenti vanno riallineati: succede solo
        # quando un admin sposta un nodo, quindi il costo non e' sulla strada
        # calda.
        if cambiato:
            for figlio in self.children.all():
                figlio.save()

    # --- comodita' ----------------------------------------------------------
    def label(self, locale: str = 'it') -> str:
        return (self.translations or {}).get(locale) or self.name

    def discendenti(self):
        return GeoArea.objects.filter(path__startswith=f'{self.path}{SEPARATORE}')

    def con_discendenti(self):
        return GeoArea.objects.filter(
            models.Q(pk=self.pk) | models.Q(path__startswith=f'{self.path}{SEPARATORE}')
        )

    @property
    def nome_completo(self) -> str:
        """Es. 'Bari (Puglia)': utile nei menu, dove 'Bari' da solo e' ambiguo."""
        if self.parent_id and self.parent.level == self.Livello.REGION:
            return f'{self.name} ({self.parent.name})'
        return self.name
