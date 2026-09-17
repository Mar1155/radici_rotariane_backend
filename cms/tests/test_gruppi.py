"""I due ruoli del pannello CMS.

Redazione e' il cliente: compone pagine, carica immagini, cambia i menu.
Gestione tipi e' chi sviluppa: definisce i tipi di articolo e la geografia.

I permessi di Wagtail su immagini e pagine **non** sono permessi di gruppo
normali: vanno legati a una collezione e a un ramo dell'albero. Un gruppo puo'
quindi sembrare configurato e non poter fare niente, ed e' esattamente cio' che
succedeva. Questi test guardano cosa la policy risponde, non cosa c'e' scritto.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from wagtail.documents.permissions import permission_policy as policy_documenti
from wagtail.images.permissions import permission_policy as policy_immagini
from wagtail.models import Page

from cms.models import HomePage

User = get_user_model()


class GruppiCmsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_cms_groups', verbosity=0)
        cls.redattore = User.objects.create_user(
            username='red', email='red@prova.it', password='prova12345', is_staff=True)
        cls.redattore.groups.add(Group.objects.get(name='Redazione'))

    def test_esistono_i_due_gruppi(self):
        self.assertTrue(Group.objects.filter(name='Redazione').exists())
        self.assertTrue(Group.objects.filter(name='Gestione tipi').exists())

    def test_la_redazione_puo_caricare_immagini(self):
        """Non basta il permesso: va legato a una collezione."""
        self.assertTrue(policy_immagini.user_has_any_permission(
            self.redattore, ['add', 'change', 'delete']))

    def test_la_redazione_puo_caricare_documenti(self):
        self.assertTrue(policy_documenti.user_has_any_permission(
            self.redattore, ['add', 'change', 'delete']))

    def test_la_redazione_puo_pubblicare_pagine(self):
        """Il permesso sulle pagine si da' per ramo dell'albero."""
        home = HomePage.objects.first()
        self.assertIsNotNone(home, 'seed_cms_groups deve creare la radice')
        permessi = home.permissions_for_user(self.redattore)
        self.assertTrue(permessi.can_add_subpage())
        self.assertTrue(permessi.can_publish())

    def test_la_redazione_puo_cambiare_i_menu(self):
        """E' il primo obiettivo: il cliente modifica il menu da se'."""
        self.assertTrue(self.redattore.has_perm('cms.change_menu'))

    def test_la_redazione_non_tocca_i_tipi_di_articolo(self):
        """Stanno in un'area separata, riservata a chi sviluppa."""
        for p in ('cms.change_articletype', 'cms.add_articletype',
                  'cms.delete_articletype', 'cms.change_geoarea'):
            self.assertFalse(self.redattore.has_perm(p), p)

    def test_la_redazione_non_tocca_utenti_e_gruppi(self):
        for p in ('auth.change_user', 'auth.add_user', 'auth.change_group'):
            self.assertFalse(self.redattore.has_perm(p), p)

    def test_gestione_tipi_tocca_i_tipi(self):
        sviluppatore = User.objects.create_user(
            username='dev', email='dev@prova.it', password='prova12345', is_staff=True)
        sviluppatore.groups.add(Group.objects.get(name='Gestione tipi'))
        sviluppatore = User.objects.get(pk=sviluppatore.pk)   # la cache dei permessi
        self.assertTrue(sviluppatore.has_perm('cms.change_articletype'))

    def test_rilanciare_non_duplica(self):
        call_command('seed_cms_groups', verbosity=0)
        self.assertEqual(Group.objects.filter(name='Redazione').count(), 1)
