"""Le pagine a contenuto fisso: /partner, /cip, /progetto.

Vengono da file JSON versionati in `cms/contenuti/`. Prima il contenuto
arrivava da file estratti al volo e passati con `--content`: cancellati quelli,
le pagine non erano piu' ricostruibili. Questi test verificano che ora lo siano.
"""

import json

from django.core.management import call_command
from django.test import TestCase
from wagtail.models import Locale, Page, Site

from cms.management.commands.build_pages_statiche import CONTENUTI, PAGINE
from cms.models import HomePage, StandardPage


class PagineeStaticheTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        locale = Locale.get_default()
        home = HomePage(title='Casa', slug='casa', locale=locale)
        Page.objects.get(depth=1).add_child(instance=home)
        sito = Site.objects.get(is_default_site=True)
        sito.root_page = home
        sito.save()
        call_command('build_pages_statiche', verbosity=0)

    def test_le_tre_pagine_esistono(self):
        self.assertEqual(sorted(StandardPage.objects.values_list('slug', flat=True)),
                         sorted(slug for slug, _ in PAGINE))

    def test_il_contenuto_e_versionato_nel_repo(self):
        """Ricostruibile dopo un azzeramento, senza file esterni."""
        for slug, _ in PAGINE:
            self.assertTrue((CONTENUTI / f'{slug}.json').exists(), slug)

    def test_cip_ha_la_sua_targhetta(self):
        cip = StandardPage.objects.get(slug='cip')
        self.assertEqual(cip.body[0].block_type, 'hero')
        self.assertEqual(cip.body[0].value['tag'], 'CIP')

    def test_progetto_ha_la_sezione_del_team(self):
        prog = StandardPage.objects.get(slug='progetto')
        team = [b for b in prog.body if b.block_type == 'people_grid']
        self.assertEqual(len(team), 1)
        self.assertEqual(team[0].value['title'], 'Il nostro Team')
        self.assertGreaterEqual(len(team[0].value['items']), 7)

    def test_le_immagini_sono_riferite_per_titolo(self):
        """Le chiavi numeriche non sopravvivono a un azzeramento; i titoli si'."""
        grezzo = json.loads((CONTENUTI / 'partner.json').read_text(encoding='utf-8'))
        testo = json.dumps(grezzo)
        self.assertNotRegex(testo, r'"logo":\s*\d+')
        self.assertIn('"logo": "@', testo)

    def test_ricostruire_non_duplica(self):
        call_command('build_pages_statiche', verbosity=0)
        self.assertEqual(StandardPage.objects.count(), len(PAGINE))
