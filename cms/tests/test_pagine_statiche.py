"""Le pagine a contenuto fisso: /partner, /cip, /progetto.

Vengono da file JSON versionati in `cms/contenuti/`. Prima il contenuto
arrivava da file estratti al volo e passati con `--content`: cancellati quelli,
le pagine non erano piu' ricostruibili. Questi test verificano che ora lo siano.
"""

import json
import re

from django.core.management import call_command
from django.core.management.base import CommandError
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

    def test_la_pillola_non_e_dello_stesso_colore_dello_sfondo(self):
        """Oro su oro non si vede, e non si vedeva: la pillola di /skills e di
        /rotariani-nel-mondo stava su un'intestazione gia' oro.

        La regola e' generale perche' il guasto lo era: non "queste due pagine
        usano il blu", ma "la pillola deve staccare da quello che ha dietro".
        Una pagina nuova che sceglie lo sfondo oro e lascia l'etichetta oro
        fallisce qui invece che davanti a chi la guarda.
        """
        # Di che colore e' cio' che sta dietro la pillola. La sfumatura parte
        # dal blu; con lo sfondo "della sezione" il colore e' l'accento.
        dietro = {'brand-primary': 'brand-primary',
                  'brand-secondary': 'brand-secondary',
                  'brand-gradient': 'brand-primary'}
        for pagina in StandardPage.objects.all():
            for blocco in pagina.body:
                if blocco.block_type != 'hero' or not blocco.value['tag']:
                    continue
                sfondo = blocco.value['surface']
                colore = (blocco.value['accent'] if sfondo == 'section'
                          else dietro.get(sfondo))
                self.assertNotEqual(
                    blocco.value['tag_color'], colore,
                    f"{pagina.slug}: l'etichetta {blocco.value['tag']!r} e' "
                    f'{colore} sopra uno sfondo {colore}: non si vede')

    def test_una_intestazione_senza_colore_detichetta_resta_oro(self):
        """Il campo e' nuovo, e le pagine scritte prima non lo nominano.

        Se il valore mancante non ricadesse sull'oro, le tre pagine che non
        sono state toccate cambierebbero aspetto da sole — ed e' il genere di
        cambiamento che nessuno collega al campo appena aggiunto.
        """
        grezzo = json.loads((CONTENUTI / 'progetto.json').read_text(encoding='utf-8'))
        self.assertNotIn('tag_color', grezzo[0]['value'],
                         'il test non prova piu' + chr(39) + ' niente: aggiorna la pagina di prova')
        prog = StandardPage.objects.get(slug='progetto')
        self.assertEqual(prog.body[0].value['tag_color'], 'brand-secondary')

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

    def test_un_contenuto_invalido_ferma_il_comando(self):
        """Il guardiano, provato sul guasto che e' davvero accaduto.

        Un'icona che non esiste nel vocabolario entrava nel database senza che
        nessuno dicesse niente: la pagina si costruiva, il comando diceva
        "pubblicate", e il guasto si vedeva tre posti piu' in la' — un blocco
        invisibile sul sito e una pubblicazione rifiutata dal pannello.
        """
        corpo = json.loads((CONTENUTI / 'progetto.json').read_text(encoding='utf-8'))
        corpo[1]['value']['items'][0]['value']['icon'] = 'IconaCheNonEsiste'
        problemi = verifica(corpo)
        self.assertTrue(problemi, 'un\'icona inventata e passata senza problemi')
        self.assertIn('IconaCheNonEsiste', ' '.join(problemi))
        # E dice **dove**: senza il percorso del blocco il messaggio non serve.
        self.assertRegex(problemi[0], r'^\[\d+\]')

    def test_il_comando_rifiuta_di_scrivere_un_contenuto_invalido(self):
        """Non basta accorgersene: non deve scriverlo."""
        file = CONTENUTI / 'progetto.json'
        originale = file.read_text(encoding='utf-8')
        corpo = json.loads(originale)
        corpo[0]['value']['surface'] = 'un-colore-inventato'
        prima = StandardPage.objects.get(slug='progetto').body[0].value['surface']
        try:
            file.write_text(json.dumps(corpo, indent=1, ensure_ascii=False) + '\n',
                            encoding='utf-8')
            with self.assertRaises(CommandError):
                call_command('build_pages_statiche', verbosity=0)
        finally:
            file.write_text(originale, encoding='utf-8')
        dopo = StandardPage.objects.get(slug='progetto').body[0].value['surface']
        self.assertEqual(prima, dopo, 'la pagina e stata scritta comunque')

    def test_nessun_apostrofo_al_posto_di_un_accento(self):
        """Un `sostenibilita'` in una pagina e' lo stesso errore di uno nei dati
        di prova, e l'elenco di parole del test accanto non lo prendeva."""
        troncamenti = {"po'", "un'", "l'", "d'", "all'", "dell'", "nell'",
                       "sull'", "quell'", "bell'", "sant'", "anch'", "dov'",
                       "cos'", "tutt'"}
        atteso = re.compile(r"\b([A-Za-z]{2,}[aeiou]')(?=[\s,.;:!?]|$)")
        for pagina in StandardPage.objects.all():
            for percorso, testo in estrai(pagina).items():
                for trovato in atteso.finditer(testo):
                    self.assertIn(trovato.group(1).lower(), troncamenti,
                                  f'{pagina.slug} {percorso}: {trovato.group(1)!r} '
                                  f"e' un accento scritto con l'apostrofo")

    def test_ricostruire_non_duplica(self):
        call_command('build_pages_statiche', verbosity=0)
        self.assertEqual(StandardPage.objects.count(), len(PAGINE))
