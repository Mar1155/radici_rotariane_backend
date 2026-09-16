"""Le 7 pagine che hanno sostituito le sezioni "Scopri".

Cio' che conta qui non e' la grafica ma il legame: ogni elenco deve puntare a
un tipo di articolo che esiste davvero. Un rimando rotto non si vede fino a
quando il visitatore apre la pagina e trova il vuoto.
"""

from django.core.management import call_command
from django.test import TestCase
from wagtail.models import Locale, Page, Site

from cms.models import ArticleType, HomePage, StandardPage

SLUG_ATTESI = [
    'adotta-un-progetto', 'storie-e-radici', 'eccellenze-calabresi',
    'calendario-delle-radici', 'scopri-la-calabria', 'scambi-e-mobilita',
    'archivio',
]


class PagineSezioneTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        locale = Locale.get_default()
        home = HomePage(title='Casa', slug='casa', locale=locale)
        Page.objects.get(depth=1).add_child(instance=home)
        sito = Site.objects.get(is_default_site=True)
        sito.root_page = home
        sito.save()
        call_command('seed_article_types', verbosity=0)
        call_command('build_pages_sezioni', verbosity=0)

    def test_sette_pagine_a_primo_livello(self):
        slug = list(StandardPage.objects.values_list('slug', flat=True))
        self.assertEqual(sorted(slug), sorted(SLUG_ATTESI))

    def test_ogni_pagina_comincia_con_una_intestazione(self):
        for pagina in StandardPage.objects.all():
            self.assertEqual(pagina.body[0].block_type, 'hero',
                             f'/{pagina.slug} non comincia con hero')

    def test_ogni_elenco_punta_a_un_tipo_esistente(self):
        chiavi = set(ArticleType.objects.values_list('key', flat=True))
        trovati = 0
        for pagina in StandardPage.objects.all():
            for blocco in pagina.body:
                if blocco.block_type == 'article_list':
                    trovati += 1
                    self.assertIn(blocco.value['article_type'].key, chiavi)
                elif blocco.block_type == 'tabbed_article_list':
                    for tab in blocco.value['tabs']:
                        trovati += 1
                        self.assertIn(tab['article_type'].key, chiavi)
        self.assertEqual(trovati, 12, 'i 12 tipi devono essere tutti raggiungibili')

    def test_ogni_tipo_di_articolo_compare_su_una_pagina(self):
        """Nessun tipo resta orfano: se esiste, si raggiunge dal sito."""
        raggiunti = set()
        for pagina in StandardPage.objects.all():
            for blocco in pagina.body:
                if blocco.block_type == 'article_list':
                    raggiunti.add(blocco.value['article_type'].key)
                elif blocco.block_type == 'tabbed_article_list':
                    raggiunti |= {t['article_type'].key for t in blocco.value['tabs']}
        self.assertEqual(raggiunti, set(ArticleType.objects.values_list('key', flat=True)))

    def test_il_calendario_e_una_modalita_dell_elenco(self):
        """Non esiste un blocco calendario: e' l'elenco eventi visto per data."""
        pagina = StandardPage.objects.get(slug='calendario-delle-radici')
        elenchi = [b for b in pagina.body if b.block_type == 'article_list']
        self.assertEqual(len(elenchi), 1)
        self.assertEqual(elenchi[0].value['layout'], 'calendar')

    def test_ricostruire_non_duplica(self):
        call_command('build_pages_sezioni', verbosity=0)
        self.assertEqual(StandardPage.objects.count(), len(SLUG_ATTESI))

    def test_le_pagine_sono_pubblicate(self):
        for pagina in StandardPage.objects.all():
            self.assertTrue(pagina.live, f'/{pagina.slug} non e pubblicata')
