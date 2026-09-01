"""Le pagine composte a blocchi e la loro API."""

from django.core.management import call_command
from django.test import TestCase
from wagtail.models import Locale, Page, Site

from cms.models import HomePage, StandardPage


class PageApiTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        locale = Locale.get_default()
        radice = Page.objects.get(depth=1)
        cls.home = HomePage(title='Casa', slug='casa', locale=locale)
        radice.add_child(instance=cls.home)
        cls.home.save_revision().publish()
        sito = Site.objects.get(is_default_site=True)
        sito.root_page = cls.home
        sito.save()

        cls.pagina = StandardPage(title='Partner', slug='partner', locale=locale, body=[
            ('hero', {'title': 'I nostri partner', 'description': 'Chi ci sostiene.',
                      'tag': 'alleanze', 'surface': 'brand-gradient', 'scroll_to_id': 'g'}),
            ('cta_banner', {'title': 'Scrivici', 'description': '',
                            'surface': 'white',
                            'primary_cta': {'label': 'Contattaci', 'route': '/rota-space',
                                            'page': None, 'external_url': ''}}),
        ])
        cls.home.add_child(instance=cls.pagina)
        cls.pagina.save_revision().publish()

    def test_risoluzione_dal_percorso(self):
        d = self.client.get('/api/cms/v1/page/?path=/partner').json()
        self.assertEqual(d['title'], 'Partner')
        self.assertEqual(d['path'], '/partner')

    def test_i_blocchi_arrivano_come_dati_non_come_html(self):
        """Il CMS non produce impaginazione: solo dati che React disegna."""
        d = self.client.get('/api/cms/v1/page/?path=/partner').json()
        self.assertEqual([b['type'] for b in d['body']], ['hero', 'cta_banner'])
        hero = d['body'][0]['value']
        self.assertEqual(hero['title'], 'I nostri partner')
        self.assertEqual(hero['surface'], 'brand-gradient')
        self.assertNotIn('<', str(hero))

    def test_il_collegamento_arriva_gia_risolto(self):
        d = self.client.get('/api/cms/v1/page/?path=/partner').json()
        cta = d['body'][1]['value']['primary_cta']
        self.assertEqual(cta, {'label': 'Contattaci', 'href': '/rota-space', 'newTab': False})

    def test_percorso_inesistente(self):
        self.assertEqual(self.client.get('/api/cms/v1/page/?path=/inventata').status_code, 404)

    def test_pagina_non_pubblicata_non_si_vede(self):
        self.pagina.unpublish()
        self.assertEqual(self.client.get('/api/cms/v1/page/?path=/partner').status_code, 404)

    def test_elenco_percorsi(self):
        percorsi = self.client.get('/api/cms/v1/page-paths/').json()['paths']
        self.assertIn('/partner', percorsi)

    def test_home_dal_percorso_radice(self):
        d = self.client.get('/api/cms/v1/page/?path=/').json()
        self.assertEqual(d['title'], 'Casa')


class PreviewApiTest(TestCase):
    def test_token_inesistente(self):
        self.assertEqual(
            self.client.get('/api/cms/v1/preview/?token=inesistente').status_code, 404)

    def test_token_mancante(self):
        self.assertEqual(self.client.get('/api/cms/v1/preview/').status_code, 400)


class LinkBlockTest(TestCase):
    """Un collegamento facoltativo lasciato vuoto non deve bloccare il salvataggio."""

    def setUp(self):
        from cms.blocks import LinkBlock
        self.blocco = LinkBlock(required=False)

    def test_vuoto_e_ammesso(self):
        pulito = self.blocco.clean(self.blocco.to_python(
            {'label': '', 'route': '', 'external_url': '', 'page': None}))
        self.assertEqual(pulito['label'], '')

    def test_vuoto_non_finisce_nella_risposta(self):
        valore = self.blocco.to_python(
            {'label': '', 'route': '', 'external_url': '', 'page': None})
        self.assertIsNone(self.blocco.get_api_representation(valore))

    def test_destinazione_senza_etichetta_e_rifiutata(self):
        from django.core.exceptions import ValidationError
        valore = self.blocco.to_python(
            {'label': '', 'route': '/rota-space', 'external_url': '', 'page': None})
        with self.assertRaises(ValidationError):
            self.blocco.clean(valore)

    def test_collegamento_completo(self):
        valore = self.blocco.to_python(
            {'label': 'Contattaci', 'route': '/rota-space', 'external_url': '', 'page': None})
        self.assertEqual(self.blocco.get_api_representation(self.blocco.clean(valore)),
                         {'label': 'Contattaci', 'href': '/rota-space', 'newTab': False})
