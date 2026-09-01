"""Costruisce /progetto nel CMS.

Le tre griglie di schede (piattaforma, pilastri, visione futura) usano lo
stesso blocco `icon_card_grid` con superfici diverse: e' il caso che mostra
perche' conviene un catalogo piccolo di blocchi riutilizzati invece di un
blocco per ogni sezione della pagina.

Idempotente.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.models import Locale

from cms.models import HomePage, StandardPage

# Icone e accenti per le schede: la vecchia pagina li aveva scritti in JSX.
ICONE_PIATTAFORMA = {'mission': ('Target', 'brand-primary'), 'vision': ('Compass', 'sky')}
ICONE_PILASTRI = {
    'networking': ('Users', 'brand-primary'), 'twinnings': ('Handshake', 'emerald'),
    'service': ('Heart', 'rose'), 'excellence': ('Award', 'amber'),
    'sustainability': ('Leaf', 'emerald'),
}


class Command(BaseCommand):
    help = 'Crea (o aggiorna) la pagina /progetto.'

    def add_arguments(self, parser):
        parser.add_argument('--content', required=True)

    def _schede(self, mappa, icone, accento_default='brand-primary'):
        voci = []
        for chiave, scheda in mappa.items():
            icona, accento = icone.get(chiave, ('Info', accento_default))
            voci.append({
                'icon': icona, 'title': scheda['title'],
                'description': scheda['description'], 'accent': accento,
                'cta': {'label': '', 'route': '', 'external_url': '', 'page': None},
            })
        return voci

    @transaction.atomic
    def handle(self, *args, **options):
        d = json.loads(Path(options['content']).read_text(encoding='utf-8'))
        locale = Locale.get_default()
        home = HomePage.objects.filter(locale=locale).first()

        pf, pi, bd, fv = d['platform'], d['pillars'], d['badges'], d['futureVision']

        corpo = [
            ('hero', {'title': d['hero']['title'], 'description': d['hero']['subtitle'],
                      'tag': d['hero'].get('badge', ''), 'surface': 'brand-gradient',
                      'scroll_to_id': 'contenuto'}),
            ('icon_card_grid', {
                'title': pf['title'], 'subtitle': pf.get('subtitle', ''),
                'columns': '2', 'surface': 'white',
                'items': self._schede(pf['cards'], ICONE_PIATTAFORMA)}),
            ('icon_card_grid', {
                'title': pi['title'], 'subtitle': pi.get('subtitle', ''),
                'columns': '3', 'surface': 'light',
                'items': self._schede(pi['items'], ICONE_PILASTRI)}),
            ('tier_cards', {
                'title': bd['title'], 'subtitle': bd.get('subtitle', ''),
                'surface': 'white',
                'items': [
                    {'tier': livello, 'title': scheda.get('title', nome),
                     'description': scheda.get('description', '')}
                    for livello, (nome, scheda) in zip(
                        ('bronze', 'silver', 'gold'), list(bd['cards'].items())[:3])
                ]}),
            ('icon_card_grid', {
                'title': fv['title'], 'subtitle': fv.get('subtitle', ''),
                'columns': '3', 'surface': 'brand-gradient',
                'items': self._schede(fv['cards'], {}, 'brand-secondary')}),
            ('cta_banner', {
                'title': fv.get('functionalities', '') or fv['title'],
                'description': '', 'surface': 'light',
                'primary_cta': {'label': fv['primaryCta'], 'route': '/rota-space',
                                'external_url': '', 'page': None},
                'secondary_cta': {'label': fv.get('secondaryCta', ''), 'route': '',
                                  'external_url': fv.get('secondaryCtaHref', ''),
                                  'page': None}}),
        ]

        pagina = StandardPage.objects.filter(slug='progetto', locale=locale).first()
        if pagina is None:
            pagina = StandardPage(title='Chi siamo', slug='progetto', locale=locale)
            home.add_child(instance=pagina)
        pagina.body = corpo
        pagina.save()
        pagina.save_revision().publish()
        n = sum(len(b[1].get('items', [])) for b in corpo if isinstance(b[1], dict))
        self.stdout.write(self.style.SUCCESS(
            f'/progetto creata con {len(corpo)} blocchi e {n} schede.'))
