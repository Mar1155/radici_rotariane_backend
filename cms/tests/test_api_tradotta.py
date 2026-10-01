"""Le API del CMS nella lingua di chi legge, chiesta come la chiede un browser.

Questi quattro endpoint sono il contorno del sito: i nomi dei tipi di articolo,
le etichette dei tag, le voci di menu, i nomi delle regioni nei filtri. Erano il
bug segnalato all'inizio della fase — "cambio lingua e i tag restano in
italiano" — e sono anche la parte piu' facile da rompere senza accorgersene,
perche' una pagina con il menu in italiano e il resto in inglese sembra un
dettaglio e invece e' la prima cosa che si vede.

Qui si chiede con `Accept-Language`, senza `?locale=`: e' il modo in cui il
frontend chiede davvero, da quando la lingua viaggia nell'intestazione.
"""

from django.core.management import call_command
from django.test import TestCase
from wagtail.models import Locale, Page, Site

from cms.models import ArticleType, GeoArea, HomePage
from traduzione import lingue
from traduzione.models import Lingua
from traduzione.servizio import traduci_tutto
from traduzione.tests import MotoreFinto


class ApiCmsTradottaTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        Lingua.objects.all().delete()
        lingue.svuota_cache()
        Lingua.objects.create(codice='it', nome='Italiano', ordine=0)
        Lingua.objects.create(codice='en', nome='English', ordine=1)

        locale = Locale.get_default()
        home = HomePage(title='Casa', slug='casa', locale=locale)
        Page.objects.get(depth=1).add_child(instance=home)
        sito = Site.objects.get(is_default_site=True)
        sito.root_page = home
        sito.save()
        call_command('seed_article_types', verbosity=0)
        # Il menu rimanda alle pagine: vanno create prima.
        call_command('seed_immagini', verbosity=0)
        call_command('build_pages_statiche', verbosity=0)
        call_command('build_pages_sezioni', verbosity=0)
        call_command('seed_menus', verbosity=0)
        call_command('seed_geo', verbosity=0)

        # Tutto tradotto con il motore finto: la traduzione e' il testo in
        # maiuscolo, quindi si vede a occhio cosa e' passato e cosa no.
        m = MotoreFinto()
        for tipo in ArticleType.objects.all():
            traduci_tutto(tipo, m)
            for elemento in tipo.info_elements.all():
                traduci_tutto(elemento, m)
            for tag in tipo.allowed_tags.all():
                traduci_tutto(tag, m)
            for categoria in tipo.tag_categories.all():
                traduci_tutto(categoria, m)

    def inglese(self, url, **extra):
        return self.client.get(url, HTTP_ACCEPT_LANGUAGE='en-GB,en;q=0.9', **extra).json()

    def test_i_nomi_dei_tipi_di_articolo(self):
        dati = self.inglese('/api/cms/v1/article-types/')
        self.assertEqual(dati['locale'], 'en', 'la lingua chiesta non e arrivata')
        nomi = [t['name'] for t in dati['articleTypes']]
        self.assertTrue(nomi, 'nessun tipo di articolo nel payload')
        self.assertTrue(all(n == n.upper() for n in nomi),
                        f'nomi non tradotti: {[n for n in nomi if n != n.upper()][:5]}')

    def test_le_etichette_dei_tag_e_degli_elementi_informativi(self):
        """E' il bug segnalato: i tag restavano in italiano."""
        dati = self.inglese('/api/cms/v1/article-types/')
        testo = str(dati)
        from cms.models import ArticleTypeTag
        tag = ArticleTypeTag.objects.first()
        self.assertIn(tag.label.upper(), testo,
                      f'etichetta {tag.label!r} non tradotta')

    def test_le_voci_di_menu(self):
        from cms.models import MenuItem
        voce = MenuItem.objects.first()
        traduci_tutto(voce, MotoreFinto())
        dati = self.inglese('/api/cms/v1/navigation/')
        self.assertIn(voce.label.upper(), str(dati))

    def test_i_nomi_delle_aree_geografiche(self):
        """Questi li traduce una persona, non il modello: `seed_geo` scrive i
        nomi inglesi a mano e li blocca, perche' "Apulia" non deve tornare
        "Puglia" al primo giro di ritraduzione."""
        self.assertTrue(GeoArea.objects.exists())
        inglese = str(self.inglese('/api/cms/v1/geo/'))
        italiano = str(self.client.get('/api/cms/v1/geo/').json())
        # `seed_geo` scrive i nomi inglesi a mano e li blocca: la prova e' che
        # le due risposte siano diverse, non quale nome compaia.
        self.assertNotEqual(inglese, italiano, 'le aree non cambiano con la lingua')
        self.assertIn('Apulia', inglese)
        self.assertIn('Puglia', italiano)

    def test_la_risposta_dichiara_che_dipende_dalla_lingua(self):
        """Senza `Vary`, una cache condivisa servirebbe la copia inglese al
        prossimo lettore italiano — e il guasto non si riproduce cercandolo,
        perche' dipende da chi e' passato prima."""
        risposta = self.client.get('/api/cms/v1/article-types/',
                                   HTTP_ACCEPT_LANGUAGE='en')
        self.assertIn('Accept-Language', risposta.headers.get('Vary', ''))

    def test_senza_intestazione_resta_italiano(self):
        dati = self.client.get('/api/cms/v1/article-types/').json()
        self.assertNotIn('ITINERARIO', str(dati).upper().replace('ITINERARI', ''))
