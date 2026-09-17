"""Chi puo' fare cosa.

Sono i test che si sarebbero accorti dei buchi trovati in questa fase: la
creazione articoli rifiutata dalla protezione CSRF, le rotte senza permessi, e
il profilo che restituiva l'email di chiunque a chiunque.
"""

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from wagtail.models import Locale, Page, Site

from cms.models import ArticleType, HomePage
from users.permissions import ADMIN, ANONIMO, CLUB, SOCIO, ruolo_applicativo

User = get_user_model()


def utente(email, **extra):
    u = User.objects.create_user(username=email.split('@')[0], email=email,
                                 password='prova12345', **extra)
    u.email_verified_at = timezone.now()
    u.save(update_fields=['email_verified_at'])
    return u


class RuoloApplicativoTest(TestCase):
    """La derivazione era invertita: guardava `user.club`, vuoto sui club."""

    def test_anonimo(self):
        from django.contrib.auth.models import AnonymousUser
        self.assertEqual(ruolo_applicativo(AnonymousUser()), ANONIMO)

    def test_un_club_e_un_club(self):
        u = utente('c@prova.it', user_type=User.Types.CLUB)
        self.assertEqual(ruolo_applicativo(u), CLUB)

    def test_un_socio_con_club_resta_socio(self):
        club = utente('c2@prova.it', user_type=User.Types.CLUB)
        socio = utente('s@prova.it', club=club)
        self.assertEqual(ruolo_applicativo(socio), SOCIO)

    def test_lo_staff_e_amministratore(self):
        u = utente('a@prova.it', is_staff=True)
        self.assertEqual(ruolo_applicativo(u), ADMIN)


class ProfiloPubblicoTest(TestCase):
    """`/api/users/<id>/` e' aperto perche' le pagine dei club lo sono.

    Bastava incrementare un numero per raccogliere email e Rotary ID di ogni
    socio.
    """

    @classmethod
    def setUpTestData(cls):
        cls.socio = utente('socio@prova.it', rotary_id='RID-1',
                           first_name='Anna', last_name='Bianchi')
        cls.club = utente('club@prova.it', user_type=User.Types.CLUB,
                          rotary_id='RID-2', club_name='RC Prova')

    def test_un_anonimo_non_vede_l_email_di_un_socio(self):
        d = self.client.get(f'/api/users/{self.socio.id}/').json()
        self.assertIsNone(d['email'])
        self.assertEqual(d['first_name'], 'Anna')

    def test_un_anonimo_vede_l_email_di_un_club(self):
        """E' un recapito istituzionale: la mappa dei club lo mostra."""
        d = self.client.get(f'/api/users/{self.club.id}/').json()
        self.assertEqual(d['email'], 'club@prova.it')

    def test_il_rotary_id_non_si_mostra_mai_agli_anonimi(self):
        for u in (self.socio, self.club):
            d = self.client.get(f'/api/users/{u.id}/').json()
            self.assertNotIn('rotary_id', d)
            self.assertNotIn('is_superuser', d)

    def test_chi_ha_fatto_accesso_vede_il_profilo_intero(self):
        # Si guarda il profilo di un ALTRO: la vista esclude se stessi dalla
        # queryset, perche' per il proprio profilo c'e' /api/users/me/.
        c = APIClient()
        c.force_authenticate(user=self.club)
        d = c.get(f'/api/users/{self.socio.id}/').json()
        self.assertEqual(d['email'], 'socio@prova.it')
        self.assertIn('rotary_id', d)


class PermessiArticoliTest(TestCase):
    """Le rotte degli articoli non dichiaravano alcun permesso."""

    @classmethod
    def setUpTestData(cls):
        locale = Locale.get_default()
        home = HomePage(title='Casa', slug='casa', locale=locale)
        Page.objects.get(depth=1).add_child(instance=home)
        sito = Site.objects.get(is_default_site=True)
        sito.root_page = home
        sito.save()
        call_command('seed_article_types', verbosity=0)
        cls.socio = utente('autore@prova.it')

    def test_l_elenco_e_pubblico(self):
        self.assertEqual(self.client.get('/api/section/articles/').status_code, 200)

    def test_creare_senza_accesso_e_rifiutato(self):
        r = self.client.post('/api/section/articles/storia/create', {'title': 'x'})
        self.assertEqual(r.status_code, 401)

    def test_creare_risponde_in_json_non_con_una_pagina_csrf(self):
        """Non era una vista DRF: Django rifiutava ogni POST con un 403 HTML,
        e nessuno poteva pubblicare niente."""
        r = self.client.post('/api/section/articles/storia/create', {'title': 'x'})
        self.assertEqual(r['Content-Type'].split(';')[0], 'application/json')

    def test_un_socio_non_pubblica_dove_non_gli_compete(self):
        """Il tipo dice chi puo' pubblicare: `eccellenza` e' solo per gli admin."""
        tipo = ArticleType.objects.get(key='eccellenza')
        self.assertNotIn(SOCIO, tipo.can_publish)
        c = APIClient()
        c.force_authenticate(user=self.socio)
        r = c.post('/api/section/articles/eccellenza/create', {'title': 'x'})
        self.assertEqual(r.status_code, 403)

    def test_i_salvati_richiedono_l_accesso(self):
        self.assertEqual(self.client.get('/api/section/cards/saved/').status_code, 401)


class ChiusoPerDifettoTest(TestCase):
    """Una vista nuova nasce protetta: e' l'impostazione globale a dirlo."""

    def test_il_permesso_predefinito_e_autenticato(self):
        from django.conf import settings
        self.assertIn('rest_framework.permissions.IsAuthenticated',
                      settings.REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'])

    def test_le_durate_dei_token_non_sono_invertite(self):
        from django.conf import settings
        jwt = settings.SIMPLE_JWT
        self.assertLess(jwt['ACCESS_TOKEN_LIFETIME'], jwt['REFRESH_TOKEN_LIFETIME'],
                        'un access che vive piu del refresh rende la rotazione inutile')
        self.assertTrue(jwt['ROTATE_REFRESH_TOKENS'])
        self.assertTrue(jwt['BLACKLIST_AFTER_ROTATION'],
                        'senza blacklist la rotazione non revoca niente')
