"""Semina l'albero geografico italiano.

Idempotente: si puo' rilanciare. Aggiorna nomi e traduzioni, non tocca i
collegamenti degli articoli.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from cms.data.italia import COMUNI_INIZIALI, REGIONI
from cms.models import GeoArea


class Command(BaseCommand):
    help = "Crea nazione, regioni, province e i comuni gia' in uso."

    @transaction.atomic
    def handle(self, *args, **options):
        italia, _ = GeoArea.objects.update_or_create(
            parent=None, key='it',
            defaults=dict(level=GeoArea.Livello.COUNTRY, name='Italia',
                          code='IT', translations={'en': 'Italy'}, sort_order=0),
        )

        n_reg = n_prov = 0
        for i, (nome, chiave, nome_en, province) in enumerate(REGIONI):
            regione, _ = GeoArea.objects.update_or_create(
                parent=italia, key=chiave,
                defaults=dict(level=GeoArea.Livello.REGION, name=nome,
                              translations={'en': nome_en} if nome_en else {},
                              sort_order=i),
            )
            n_reg += 1
            for j, (nome_p, sigla) in enumerate(province):
                GeoArea.objects.update_or_create(
                    parent=regione, key=slugify(nome_p),
                    defaults=dict(level=GeoArea.Livello.PROVINCE, name=nome_p,
                                  code=sigla, sort_order=j),
                )
                n_prov += 1

        n_com = 0
        for nome_c, chiave_c, chiave_prov in COMUNI_INIZIALI:
            provincia = GeoArea.objects.filter(
                key=chiave_prov, level=GeoArea.Livello.PROVINCE).first()
            if not provincia:
                self.stderr.write(f'  ! provincia {chiave_prov} non trovata per {nome_c}')
                continue
            GeoArea.objects.update_or_create(
                parent=provincia, key=chiave_c,
                defaults=dict(level=GeoArea.Livello.CITY, name=nome_c),
            )
            n_com += 1

        self.stdout.write(self.style.SUCCESS(
            f'1 nazione, {n_reg} regioni, {n_prov} province, {n_com} comuni.'))
