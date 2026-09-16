"""Gli articoli, ora indirizzati per tipo."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from rest_framework.test import APITestCase

from cms.models import ArticleType, GeoArea
from section.models import Card
from section.views import ruolo_applicativo


class BaseArticoli(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_geo', verbosity=0)
        call_command('seed_article_types', verbosity=0)
        U = get_user_model()
        cls.socio = U.objects.create_user(
            email='socio@prova.it', username='socio', password='Pr0va!Password#26')
        cls.itinerario = ArticleType.objects.get(key='itinerario')
        cls.eccellenza = ArticleType.objects.get(key='eccellenza')
        cls.progetto = ArticleType.objects.get(key='progetto')

    def _articolo(self, tipo, titolo='Titolo', **kw):
        return Card.objects.create(article_type=tipo, title=titolo,
                                   subtitle='Sottotitolo', is_published=True,
                                   author=self.socio, **kw)


class RuoloApplicativoTest(BaseArticoli):
    """La derivazione del ruolo era invertita e va tenuta ferma."""

    def test_socio(self):
        self.assertEqual(ruolo_applicativo(self.socio), 'user')

    def test_club_non_viene_scambiato_per_socio(self):
        U = get_user_model()
        club = U.objects.create_user(email='club@prova.it', username='club',
                                     password='Pr0va!Password#26', user_type='CLUB')
        self.assertEqual(ruolo_applicativo(club), 'club')

    def test_socio_con_club_resta_socio(self):
        U = get_user_model()
        club = U.objects.create_user(email='c2@prova.it', username='c2',
                                     password='Pr0va!Password#26', user_type='CLUB')
        self.socio.club = club
        self.socio.save()
        self.assertEqual(ruolo_applicativo(self.socio), 'user')

    def test_staff(self):
        self.socio.is_staff = True
        self.assertEqual(ruolo_applicativo(self.socio), 'admin')


class CoerenzaArticoloTest(BaseArticoli):
    def test_tag_non_previsti_dal_tipo_sono_rifiutati(self):
        art = Card(article_type=self.eccellenza, title='X', tags=['inventato'])
        with self.assertRaises(ValidationError) as ctx:
            art.full_clean()
        self.assertIn('tags', ctx.exception.message_dict)

    def test_elementi_informativi_sconosciuti_sono_rifiutati(self):
        art = Card(article_type=self.itinerario, title='X',
                   info_values={'inventato': '3'})
        with self.assertRaises(ValidationError) as ctx:
            art.full_clean()
        self.assertIn('info_values', ctx.exception.message_dict)

    def test_valori_informativi_per_chiave(self):
        art = self._articolo(self.itinerario, info_values={'giorni': '3'})
        art.refresh_from_db()
        self.assertEqual(art.info_values['giorni'], '3')

    def test_senza_tipo_non_si_salva(self):
        with self.assertRaises(ValidationError):
            Card(title='Orfano').full_clean()


class ElencoArticoliTest(BaseArticoli):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        bari = GeoArea.objects.get(key='bari')
        milano = GeoArea.objects.get(key='milano')
        cls.a = Card.objects.create(article_type=cls.itinerario, title='A Bari',
                                    geo_area=bari, is_published=True)
        cls.b = Card.objects.create(article_type=cls.itinerario, title='A Milano',
                                    geo_area=milano, is_published=True)
        cls.c = Card.objects.create(article_type=cls.eccellenza, title='Eccellenza',
                                    is_published=True)

    def _titoli(self, query=''):
        return sorted(x['title'] for x in
                      self.client.get(f'/api/section/articles/{query}').json())

    def test_filtro_per_tipo(self):
        self.assertEqual(self._titoli('?type=itinerario'), ['A Bari', 'A Milano'])
        self.assertEqual(self._titoli('?type=eccellenza'), ['Eccellenza'])

    def test_filtro_geografico_resta_gerarchico(self):
        self.assertEqual(self._titoli('?type=itinerario&geo=puglia'), ['A Bari'])

    def test_ricerca(self):
        self.assertEqual(self._titoli('?search=milano'), ['A Milano'])

    def test_limite(self):
        self.assertEqual(len(self._titoli('?type=itinerario&limit=1')), 1)

    def test_il_tipo_viaggia_come_chiave(self):
        dati = self.client.get('/api/section/articles/?type=eccellenza').json()
        self.assertEqual(dati[0]['article_type'], 'eccellenza')

    def test_le_liste_non_portano_il_corpo(self):
        self.assertNotIn('content', self.client.get('/api/section/articles/').json()[0])


class SalvataggioTest(BaseArticoli):
    def test_consentito_se_il_tipo_prevede_il_salvataggio(self):
        """`itinerario` non lo prevede, `progetto` si: e' il tipo a deciderlo."""
        self.assertNotIn('save', self.itinerario.active_fields)
        art = self._articolo(self.progetto)
        self.client.force_authenticate(self.socio)
        r = self.client.post(f'/api/section/cards/{art.slug}/save/')
        # 201: il salvataggio crea una riga SavedCard.
        self.assertIn(r.status_code, (200, 201))

    def test_bloccato_se_il_tipo_non_lo_prevede(self):
        """`eccellenza` non ha `save` fra i campi attivi."""
        self.assertNotIn('save', self.eccellenza.active_fields)
        art = self._articolo(self.eccellenza)
        self.client.force_authenticate(self.socio)
        r = self.client.post(f'/api/section/cards/{art.slug}/save/')
        self.assertEqual(r.status_code, 403)
