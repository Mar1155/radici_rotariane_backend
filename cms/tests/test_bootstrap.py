"""La radice del sito su un database appena migrato.

Gli altri test partono da un Site gia' sistemato a mano. Questo no: parte da
com'e' il database subito dopo `migrate`, che e' la condizione della prima
installazione e dell'unica che contera' davvero, quella in produzione.
"""

from django.test import TestCase
from wagtail.models import Page, Site

from cms.bootstrap import assicura_homepage
from cms.models import HomePage


class BootstrapTest(TestCase):
    def test_pagina_di_benvenuto_sostituita(self):
        """La pagina installata dalle migrazioni lascia il posto alla nostra."""
        radice = Page.objects.get(depth=1)
        self.assertTrue(Page.objects.child_of(radice).filter(slug='home').exists())

        home = assicura_homepage()

        self.assertIsInstance(home, HomePage)
        self.assertEqual(Page.objects.child_of(radice).filter(slug='home').count(), 1)

    def test_il_sito_sopravvive(self):
        """Cancellare la pagina di benvenuto cancella il Site a cascata.

        Site.root_page e' una FK con on_delete=CASCADE, quindi togliere di
        mezzo la pagina di Wagtail si porta via anche il sito. Senza sito,
        l'API risponde 404 a ogni percorso.
        """
        home = assicura_homepage()

        sito = Site.objects.get(is_default_site=True)
        self.assertEqual(sito.root_page_id, home.pk)

    def test_le_pagine_figlie_si_risolvono(self):
        """La prova che conta: una pagina creata dopo risponde all'API."""
        from wagtail.models import Locale
        from cms.models import StandardPage

        home = assicura_homepage()
        pagina = StandardPage(title='Partner', slug='partner', locale=Locale.get_default())
        home.add_child(instance=pagina)
        pagina.save_revision().publish()

        risposta = self.client.get('/api/cms/v1/page/?path=/partner')

        self.assertEqual(risposta.status_code, 200)
        self.assertEqual(risposta.json()['title'], 'Partner')

    def test_chiamarlo_due_volte_non_cambia_niente(self):
        prima = assicura_homepage()
        dopo = assicura_homepage()

        self.assertEqual(prima.pk, dopo.pk)
        self.assertEqual(Site.objects.filter(is_default_site=True).count(), 1)
