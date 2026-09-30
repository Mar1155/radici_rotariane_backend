"""Le pagine a contenuto fisso: /partner, /cip, /progetto.

Vengono da file JSON versionati in `cms/contenuti/`. Prima il contenuto
arrivava da file estratti al volo e passati con `--content`: cancellati quelli,
le pagine non erano piu' ricostruibili. Questi test verificano che ora lo siano.
"""

import json
import re

from django.core.management import call_command
from django.test import TestCase
from wagtail.models import Locale, Page, Site

from cms.management.commands.build_pages_statiche import (CONTENUTI, PAGINE,
                                                          risolvi_immagini, verifica)
from cms.models import CMSImage, HomePage, StandardPage
from traduzione.percorsi import estrai


class PagineeStaticheTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        locale = Locale.get_default()
        home = HomePage(title='Casa', slug='casa', locale=locale)
        Page.objects.get(depth=1).add_child(instance=home)
        sito = Site.objects.get(is_default_site=True)
        sito.root_page = home
        sito.save()
        call_command('build_pages_statiche', verbosity=0)

    def test_le_tre_pagine_esistono(self):
        self.assertEqual(sorted(StandardPage.objects.values_list('slug', flat=True)),
                         sorted(slug for slug, _ in PAGINE))

    def test_il_contenuto_e_versionato_nel_repo(self):
        """Ricostruibile dopo un azzeramento, senza file esterni."""
        for slug, _ in PAGINE:
            self.assertTrue((CONTENUTI / f'{slug}.json').exists(), slug)

    def test_cip_ha_la_sua_targhetta(self):
        cip = StandardPage.objects.get(slug='cip')
        self.assertEqual(cip.body[0].block_type, 'hero')
        self.assertEqual(cip.body[0].value['tag'], 'CIP')

    def test_progetto_ha_la_sezione_del_team(self):
        prog = StandardPage.objects.get(slug='progetto')
        team = [b for b in prog.body if b.block_type == 'people_grid']
        self.assertEqual(len(team), 1)
        self.assertEqual(team[0].value['title'], 'Il nostro Team')
        self.assertGreaterEqual(len(team[0].value['items']), 7)

    def test_progetto_offre_la_spiegazione_del_logo(self):
        """Il pulsante che scarica il PDF c'era nella pagina scritta a mano.

        Passando al CMS era finito in coda, dopo i ringraziamenti, dove nessuno
        andava a cercarlo. Qui si controlla che ci sia **e** che stia accanto
        alla sezione che parla della piattaforma, come prima.
        """
        prog = StandardPage.objects.get(slug='progetto')
        blocchi = list(prog.body)
        logo = [i for i, b in enumerate(blocchi)
                if b.block_type == 'cta_banner'
                and b.value['primary_cta']['route'] == '/spiegazione-logo.pdf']
        self.assertEqual(len(logo), 1)
        precedente = blocchi[logo[0] - 1]
        self.assertTrue(precedente.value['title'].startswith("Cos'è la Piattaforma"),
                        f'il riquadro del logo segue {precedente.value["title"]!r}')

    def test_le_immagini_sono_riferite_per_titolo(self):
        """Le chiavi numeriche non sopravvivono a un azzeramento; i titoli si'."""
        grezzo = json.loads((CONTENUTI / 'partner.json').read_text(encoding='utf-8'))
        testo = json.dumps(grezzo)
        self.assertNotRegex(testo, r'"logo":\s*\d+')
        self.assertIn('"logo": "@', testo)

    def test_ogni_contenuto_versionato_e_accettato_dai_blocchi(self):
        """Assegnare un corpo a uno StreamField non lo valida: il JSON entra nel
        database qualunque cosa contenga.

        E' costato tre sintomi lontani dalla causa — un'icona che sul sito non
        compariva, una tendina vuota nel pannello, una pubblicazione rifiutata
        per un blocco che nessuno aveva aggiunto — e nessun errore da nessuna
        parte. Questo test e' la stessa domanda che ora fa il comando.
        """
        immagini = {i.title: i.pk for i in CMSImage.objects.all()}
        for slug, _ in PAGINE:
            corpo = json.loads((CONTENUTI / f'{slug}.json').read_text(encoding='utf-8'))
            problemi = verifica(risolvi_immagini(corpo, immagini, set()))
            self.assertEqual(problemi, [], f'{slug}.json: ' + '; '.join(problemi))

    def test_i_contenuti_sono_scritti_in_italiano_con_gli_accenti(self):
        """Nei commenti del codice scrivo `perche'` e `piu'` senza accento di
        proposito. In una pagina pubblica la stessa abitudine e' un errore di
        ortografia, ed e' arrivata in produzione: "Funzionalita del Rota-Space",
        "Perche usare il Rota-Space".

        Cosa sia prosa e cosa un identificatore lo decide `traduzione.percorsi`,
        che lo sa gia' — un'ancora come `funzionalita` deve restare ASCII, e un
        elenco di campi da saltare scritto qui divergerebbe dal suo.
        """
        atteso = re.compile(r'\b(' + '|'.join([
            'piu', 'puo', 'perche', 'cosi', 'gia', 'pero', 'cio', 'funzionalita',
            'attivita', 'citta', 'qualita', 'comunita', 'universita', 'identita',
            'novita', 'societa', 'verita', 'possibilita', 'opportunita', 'realta',
        ]) + r')\b', re.IGNORECASE)
        for pagina in StandardPage.objects.all():
            for percorso, testo in estrai(pagina).items():
                trovato = atteso.search(testo)
                self.assertIsNone(
                    trovato, f'{pagina.slug} {percorso}: '
                             f'"{trovato.group(0) if trovato else ""}" senza accento')

    def test_ricostruire_non_duplica(self):
        call_command('build_pages_statiche', verbosity=0)
        self.assertEqual(StandardPage.objects.count(), len(PAGINE))
