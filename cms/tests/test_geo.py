"""La tassonomia geografica e il filtro gerarchico."""

from django.core.management import call_command
from django.test import TestCase

from cms.models import GeoArea
from section.models import Card


class GeoTreeTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_geo', verbosity=0)

    def test_struttura(self):
        self.assertEqual(GeoArea.objects.filter(level='country').count(), 1)
        self.assertEqual(GeoArea.objects.filter(level='region').count(), 20)
        self.assertEqual(GeoArea.objects.filter(level='province').count(), 107)

    def test_percorsi(self):
        bari = GeoArea.objects.get(key='bari')
        self.assertEqual(bari.path, 'it/puglia/bari')
        self.assertEqual(GeoArea.objects.get(key='rende').path,
                         'it/calabria/cosenza/rende')

    def test_discendenti(self):
        calabria = GeoArea.objects.get(key='calabria')
        # 5 province + il comune di Rende
        self.assertEqual(calabria.discendenti().count(), 6)
        self.assertEqual(calabria.con_discendenti().count(), 7)

    def test_traduzioni_senza_locale_wagtail(self):
        """Le etichette non dipendono dalle righe Locale: sono un JSONField."""
        self.assertEqual(GeoArea.objects.get(key='puglia').label('en'), 'Apulia')
        self.assertEqual(GeoArea.objects.get(key='puglia').label('it'), 'Puglia')
        # senza traduzione si ricade sul nome italiano
        self.assertEqual(GeoArea.objects.get(key='veneto').label('en'), 'Veneto')

    def test_spostare_un_nodo_riallinea_i_discendenti(self):
        rende = GeoArea.objects.get(key='rende')
        catanzaro = GeoArea.objects.get(key='catanzaro')
        rende.parent = catanzaro
        rende.save()
        rende.refresh_from_db()
        self.assertEqual(rende.path, 'it/calabria/catanzaro/rende')

    def test_nome_completo_disambigua(self):
        self.assertEqual(GeoArea.objects.get(key='bari').nome_completo, 'Bari (Puglia)')


class GeoFilterTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_geo', verbosity=0)
        cls.bari = GeoArea.objects.get(key='bari')
        cls.lecce = GeoArea.objects.get(key='lecce')
        cls.milano = GeoArea.objects.get(key='milano')
        comune = dict(section='storie-e-radici', tab='storie', is_published=True)
        cls.c_bari = Card.objects.create(title='A Bari', geo_area=cls.bari, **comune)
        cls.c_lecce = Card.objects.create(title='A Lecce', geo_area=cls.lecce, **comune)
        cls.c_milano = Card.objects.create(title='A Milano', geo_area=cls.milano, **comune)
        cls.c_nessuna = Card.objects.create(title='Senza luogo', **comune)

    def _titoli(self, geo=None):
        url = '/api/section/storie-e-radici/storie/cards'
        if geo:
            url += f'?geo={geo}'
        return sorted(c['title'] for c in self.client.get(url).json())

    def test_senza_filtro_tutti(self):
        self.assertEqual(len(self._titoli()), 4)

    def test_filtro_su_provincia(self):
        self.assertEqual(self._titoli('bari'), ['A Bari'])

    def test_filtro_su_regione_include_le_province(self):
        """Il punto dell'albero: la Puglia comprende Bari e Lecce."""
        self.assertEqual(self._titoli('puglia'), ['A Bari', 'A Lecce'])

    def test_filtro_su_nazione_include_tutto_il_paese(self):
        self.assertEqual(self._titoli('it'), ['A Bari', 'A Lecce', 'A Milano'])

    def test_area_inesistente_non_restituisce_tutto(self):
        """Un filtro sbagliato deve dare zero, non l'intero elenco."""
        self.assertEqual(self._titoli('atlantide'), [])

    def test_serializer_espone_il_percorso(self):
        dati = self.client.get(
            '/api/section/storie-e-radici/storie/cards?geo=bari').json()
        self.assertEqual(dati[0]['geo_area']['path'], 'it/puglia/bari')
