"""I menu come dati, e la fine della navigazione scritta due volte."""

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from wagtail.models import Locale

from cms.models import Menu, MenuItem


class MenuSeedTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_menus', verbosity=0)

    def test_due_menu_ciascuno_definito_una_volta(self):
        self.assertEqual(
            sorted(Menu.objects.values_list('key', flat=True)),
            ['esplora', 'servizi'])

    def test_esplora_ha_le_undici_voci_della_navbar(self):
        self.assertEqual(Menu.objects.get(key='esplora').items.count(), 11)

    def test_voce_solo_per_anonimi(self):
        accedi = MenuItem.objects.get(menu__key='servizi', label='Accedi')
        self.assertEqual(accedi.visibility, MenuItem.Visibilita.ANONIMI)


class MenuItemTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.locale = Locale.get_default()
        cls.menu = Menu.objects.create(key='prova', name='Prova', locale=cls.locale)

    def _voce(self, **kw):
        return MenuItem(menu=self.menu, label='X', locale=self.locale, **kw)

    def test_serve_una_destinazione(self):
        with self.assertRaises(ValidationError):
            self._voce().full_clean()

    def test_una_sola_destinazione(self):
        voce = self._voce(route='/a', external_url='https://esempio.it')
        with self.assertRaises(ValidationError):
            voce.full_clean()

    def test_un_menu_non_puo_contenere_se_stesso(self):
        voce = self._voce(submenu=self.menu)
        with self.assertRaises(ValidationError):
            voce.full_clean()

    def test_href_dai_diversi_tipi_di_destinazione(self):
        self.assertEqual(self._voce(route='/rota-space').href, '/rota-space')
        self.assertEqual(self._voce(external_url='https://rotary.org').href,
                         'https://rotary.org')
        # una voce che apre un sottomenu non porta da nessuna parte
        self.assertIsNone(self._voce(submenu=Menu.objects.create(
            key='altro', name='Altro', locale=self.locale)).href)


class NavigationApiTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_menus', verbosity=0)

    def test_serve_entrambi_i_menu(self):
        dati = self.client.get('/api/cms/v1/navigation/').json()
        self.assertEqual(sorted(dati['menus']), ['esplora', 'servizi'])
        self.assertEqual(len(dati['menus']['esplora']['items']), 11)

    def test_le_voci_portano_href_risolti(self):
        dati = self.client.get('/api/cms/v1/navigation/').json()
        voci = {v['label']: v['href'] for v in dati['menus']['esplora']['items']}
        self.assertEqual(voci['Partner'], '/partner')
        self.assertEqual(voci['Homepage'], '/')

    def test_sottomenu_espanso_in_linea(self):
        """Chi consuma l'API non deve sapere che un menu ne referenzia un altro."""
        locale = Locale.get_default()
        contenitore = Menu.objects.create(key='barra', name='Barra', locale=locale)
        MenuItem.objects.create(menu=contenitore, label='Esplora', locale=locale,
                                submenu=Menu.objects.get(key='esplora'))
        dati = self.client.get('/api/cms/v1/navigation/').json()
        voce = dati['menus']['barra']['items'][0]
        self.assertIsNone(voce['href'])
        self.assertEqual(len(voce['children']), 11)
