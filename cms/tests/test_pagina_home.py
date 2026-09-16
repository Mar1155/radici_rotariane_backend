"""La homepage nel CMS.

E' l'unica pagina che il frontend non puo' far sparire cancellandone la
cartella — `/` non e' un segmento, nessun catch-all lo intercetta — quindi
conta soprattutto che l'API la risolva a `/` e che i suoi rimandi reggano.
"""

from django.core.management import call_command
from django.test import TestCase
from wagtail.models import Locale, Page, Site

from cms.models import HomePage, StandardPage

# Le pagine a cui la homepage rimanda.
RIMANDI = [
    'adotta-un-progetto', 'storie-e-radici', 'eccellenze-calabresi',
    'calendario-delle-radici', 'scopri-la-calabria', 'scambi-e-mobilita',
    'archivio', 'progetto', 'cip', 'partner',
]


class PaginaHomeTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        locale = Locale.get_default()
        home = HomePage(title='Casa', slug='casa', locale=locale)
        Page.objects.get(depth=1).add_child(instance=home)
        sito = Site.objects.get(is_default_site=True)
        sito.root_page = home
        sito.save()
        for slug in RIMANDI:
            home.add_child(instance=StandardPage(title=slug, slug=slug, locale=locale))
        call_command('build_page_home', verbosity=0)
        cls.home = HomePage.objects.get(pk=home.pk)

    def test_i_sei_blocchi_della_homepage(self):
        self.assertEqual(
            [b.block_type for b in self.home.body],
            ['split_hero', 'icon_card_grid', 'numbered_steps',
             'section_tiles', 'stats_bar', 'cta_banner'])

    def test_si_risolve_alla_radice(self):
        r = self.client.get('/api/cms/v1/page/', {'path': '/', 'locale': 'it'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual([b['type'] for b in r.json()['body']][0], 'split_hero')

    def test_il_registrati_non_si_mostra_a_chi_ha_gia_un_account(self):
        """La regola viaggia col collegamento, non col markup."""
        r = self.client.get('/api/cms/v1/page/', {'path': '/', 'locale': 'it'})
        anonimi = [
            v[k]['label']
            for b in r.json()['body'] for v in [b['value']]
            for k in ('primary_cta', 'cta')
            if isinstance(v.get(k), dict) and v[k].get('visibility') == 'anonymous'
        ]
        self.assertEqual(len(anonimi), 3, f'attesi tre inviti a iscriversi, trovati {anonimi}')

    def test_i_riquadri_puntano_a_pagine_non_a_indirizzi(self):
        """Se il cliente rinomina una pagina, i riquadri la seguono."""
        riquadri = next(b for b in self.home.body if b.block_type == 'section_tiles')
        tiles = riquadri.value['tiles']
        verso_pagine = [t for t in tiles if t['link']['page']]
        # Nove su dieci: solo Skills Network e' una rotta dell'app, non una pagina.
        self.assertEqual(len(verso_pagine), 9)
        self.assertEqual([t['label'] for t in tiles if not t['link']['page']],
                         ['Skills Network'])

    def test_i_numeri_dichiarano_il_dato_non_il_valore(self):
        fascia = next(b for b in self.home.body if b.block_type == 'stats_bar')
        self.assertEqual([n['source'] for n in fascia.value['items']],
                         ['clubs', 'rotarians', 'countries', 'projects'])

    def test_ricostruire_non_crea_una_seconda_home(self):
        call_command('build_page_home', verbosity=0)
        self.assertEqual(HomePage.objects.count(), 1)

    def test_si_ferma_se_una_pagina_a_cui_rimanda_non_esiste(self):
        StandardPage.objects.get(slug='partner').delete()
        with self.assertRaises(ValueError):
            call_command('build_page_home', verbosity=0)
