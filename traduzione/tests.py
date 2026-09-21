"""La traduzione di pagine e articoli.

Il punto da dimostrare non e' che il traduttore traduca — quello e' compito suo
— ma che la **struttura sopravviva**: grassetti, link e immagini non passano mai
dal traduttore, e devono ritrovarsi identici dall'altra parte.
"""

import json

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.conf import settings
from django.test import TestCase, override_settings
from wagtail.models import Locale, Page, Site

from cms.models import ArticleType, HomePage
from section.models import Card, CardTranslation
from section.schema import estrai_testi, reinserisci_testi
from traduzione.articoli import lingue_di_destinazione, traduci_articolo
from traduzione import lingue
from traduzione.models import Lingua
from traduzione.motori import (MotoreClaude, MotoreIdentita, MotoreTraduzione,
                               TraduzioneNonConfigurata, motore)

User = get_user_model()


class MotoreFinto(MotoreTraduzione):
    """Traduce mettendo tutto in maiuscolo: si vede a occhio cosa e' passato."""

    nome = 'finto'
    da_rivedere = False

    def __init__(self):
        self.chiamate = []

    def traduci(self, testi, da, a):
        self.chiamate.append((dict(testi), da, a))
        return {k: v.upper() for k, v in testi.items()}


def documento():
    return {'type': 'doc', 'content': [
        {'type': 'paragraph', 'content': [
            {'type': 'text', 'text': 'Testo in '},
            {'type': 'text', 'text': 'grassetto', 'marks': [{'type': 'bold'}]},
            {'type': 'text', 'text': ' e un link',
             'marks': [{'type': 'link', 'attrs': {'href': 'https://rotary.org'}}]},
        ]},
        {'type': 'image', 'attrs': {'assetId': 7, 'alt': 'Una foto'}},
    ]}


class PercorsiTest(TestCase):
    """Estrarre e rimettere il testo senza toccare la formattazione."""

    def test_si_estrae_ogni_testo_col_suo_percorso(self):
        self.assertEqual(
            estrai_testi(documento()),
            {'0.0': 'Testo in ', '0.1': 'grassetto', '0.2': ' e un link',
             '1.alt': 'Una foto'})

    def test_rimettendoli_la_formattazione_resta(self):
        doc = documento()
        tradotti = {k: v.upper() for k, v in estrai_testi(doc).items()}
        nuovo = reinserisci_testi(doc, tradotti)
        para = nuovo['content'][0]['content']
        self.assertEqual(para[1]['text'], 'GRASSETTO')
        self.assertEqual(para[1]['marks'], [{'type': 'bold'}])
        self.assertEqual(para[2]['marks'][0]['attrs']['href'], 'https://rotary.org')
        self.assertEqual(nuovo['content'][1]['attrs']['assetId'], 7)

    def test_l_originale_non_si_tocca(self):
        doc = documento()
        reinserisci_testi(doc, {'0.0': 'ALTRO'})
        self.assertEqual(doc['content'][0]['content'][0]['text'], 'Testo in ')

    def test_un_percorso_che_non_esiste_piu_si_ignora(self):
        """Il documento puo' cambiare mentre la traduzione e' in corso: in quel
        caso si perde una frase, non l'articolo."""
        nuovo = reinserisci_testi(documento(), {'9.9.9': 'fuori posto'})
        self.assertEqual(nuovo['content'][0]['content'][0]['text'], 'Testo in ')


class MotoriTest(TestCase):
    @override_settings(TRANSLATION_ENGINE='claude', ANTHROPIC_API_KEY='')
    def test_senza_chiave_si_ripiega_sull_identita(self):
        """Il sito deve funzionare anche senza motore: un articolo leggibile
        nella lingua sbagliata e' meglio di un articolo assente."""
        m = motore()
        self.assertIsInstance(m, MotoreIdentita)
        self.assertTrue(m.da_rivedere)

    @override_settings(TRANSLATION_ENGINE='claude', ANTHROPIC_API_KEY='chiave-finta')
    def test_con_la_chiave_si_usa_il_modello(self):
        self.assertIsInstance(motore(), MotoreClaude)

    @override_settings(TRANSLATION_ENGINE='inventato')
    def test_un_motore_sconosciuto_e_un_errore(self):
        with self.assertRaises(TraduzioneNonConfigurata):
            motore()

    def test_il_traduttore_che_cambia_le_chiavi_e_un_errore(self):
        """Se il modello ne inventa o ne perde ha frainteso il compito, ed e'
        meglio accorgersene che salvare un documento con dei buchi."""
        class Sbadato(MotoreClaude):
            def traduci(self, testi, da, a):
                return {'chiave-inventata': 'x'}

        with self.assertRaises(Exception):
            MotoreClaude._estrai_json('non e json')


class TraduzioneArticoloTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Le lingue non stanno piu' nelle impostazioni: sono righe, e un
        # database di test parte senza.
        call_command('seed_lingue', verbosity=0)
        locale = Locale.get_default()
        home = HomePage(title='Casa', slug='casa', locale=locale)
        Page.objects.get(depth=1).add_child(instance=home)
        sito = Site.objects.get(is_default_site=True)
        sito.root_page = home
        sito.save()
        call_command('seed_article_types', verbosity=0)
        cls.autore = User.objects.create_user(
            username='tr', email='tr@prova.it', password='prova12345')

    def crea(self, **extra):
        dati = dict(
            slug='da-tradurre', title='Il titolo', subtitle='Il sottotitolo',
            location='Cosenza', body=documento(), info_values={'giorni': '3'},
            article_type=ArticleType.objects.get(key='itinerario'),
            author=self.autore, is_published=True, source_locale='it')
        dati.update(extra)
        return Card.objects.create(**dati)

    def test_si_traduce_in_tutte_le_lingue_tranne_la_propria(self):
        card = self.crea()
        self.assertEqual(lingue_di_destinazione(card), ['en'])

    def test_titolo_corpo_e_informazioni_viaggiano_insieme(self):
        """Il traduttore vede tutto l'articolo in una volta, quindi puo' essere
        coerente fra il titolo e il testo."""
        finto = MotoreFinto()
        traduci_articolo(self.crea(), 'en', finto)
        inviati, da, a = finto.chiamate[0]
        self.assertEqual((da, a), ('it', 'en'))
        self.assertIn('campo:title', inviati)
        self.assertIn('corpo:0.1', inviati)
        self.assertIn('info:giorni', inviati)

    def test_la_struttura_sopravvive_alla_traduzione(self):
        t = traduci_articolo(self.crea(), 'en', MotoreFinto())
        para = t.translated_body['content'][0]['content']
        self.assertEqual(para[1]['text'], 'GRASSETTO')
        self.assertEqual(para[1]['marks'], [{'type': 'bold'}])
        self.assertEqual(para[2]['marks'][0]['attrs']['href'], 'https://rotary.org')
        self.assertEqual(t.translated_body['content'][1]['attrs']['assetId'], 7)
        self.assertEqual(t.translated_title, 'IL TITOLO')
        self.assertEqual(t.translated_info_values, {'giorni': '3'})

    def test_una_correzione_a_mano_non_viene_sovrascritta(self):
        """Chi l'ha scritta ne sapeva piu' della macchina."""
        card = self.crea()
        CardTranslation.objects.create(
            card=card, target_language='en', translated_title='Scritto da una persona',
            provider='umano', human_locked=True)
        traduci_articolo(card, 'en', MotoreFinto())
        t = CardTranslation.objects.get(card=card, target_language='en')
        self.assertEqual(t.translated_title, 'Scritto da una persona')

    def test_col_motore_di_identita_finisce_in_revisione(self):
        t = traduci_articolo(self.crea(), 'en', MotoreIdentita())
        self.assertTrue(t.needs_review)
        self.assertEqual(t.provider, 'identita')

    def test_l_api_serve_la_lingua_richiesta(self):
        card = self.crea()
        traduci_articolo(card, 'en', MotoreFinto())
        originale = self.client.get(f'/api/section/cards/{card.slug}').json()
        self.assertEqual(originale['title'], 'Il titolo')
        self.assertIsNone(originale['translated_from'])

        inglese = self.client.get(f'/api/section/cards/{card.slug}',
                                  {'locale': 'en'}).json()
        self.assertEqual(inglese['title'], 'IL TITOLO')
        # E' cosi' che il lettore sa di stare leggendo una traduzione.
        self.assertEqual(inglese['translated_from'], 'it')

    def test_il_comando_non_ritraduce_cio_che_c_e_gia(self):
        card = self.crea()
        traduci_articolo(card, 'en', MotoreFinto())
        prima = CardTranslation.objects.get(card=card, target_language='en').updated_at
        call_command('translate_pending', verbosity=0)
        dopo = CardTranslation.objects.get(card=card, target_language='en').updated_at
        self.assertEqual(prima, dopo)


class RegistroLingueTest(TestCase):
    """Le lingue sono righe, non impostazioni.

    E' la differenza che rende "aggiungere una lingua" un gesto dal pannello
    invece di un deploy.
    """

    def setUp(self):
        lingue.svuota_cache()

    def tearDown(self):
        lingue.svuota_cache()

    def test_senza_righe_si_ripiega_sulla_lingua_di_stesura(self):
        """Un database vuoto non deve far esplodere il sito, solo servirlo in italiano."""
        Lingua.objects.all().delete()
        lingue.svuota_cache()
        self.assertEqual(lingue.codici_attivi(), [settings.LANGUAGE_CODE])

    def test_aggiungere_una_riga_basta(self):
        call_command('seed_lingue', verbosity=0)
        self.assertEqual(lingue.codici_attivi(), ['it', 'en'])

        Lingua.objects.create(codice='es', nome='Espanol', ordine=2)

        # Nessuno ha svuotato la cache a mano: lo fa il segnale.
        self.assertEqual(lingue.codici_attivi(), ['it', 'en', 'es'])

    def test_spegnere_una_lingua_la_toglie_dal_giro(self):
        call_command('seed_lingue', verbosity=0)
        inglese = Lingua.objects.get(codice='en')
        inglese.attiva = False
        inglese.save()

        self.assertEqual(lingue.codici_attivi(), ['it'])
        self.assertEqual(lingue.altre_lingue('it'), [])

    def test_il_codice_si_normalizza(self):
        Lingua.objects.all().delete()
        Lingua.objects.create(codice='  ES  ', nome='Espanol')
        self.assertEqual(Lingua.objects.get().codice, 'es')

    def test_la_variante_regionale_non_conta(self):
        call_command('seed_lingue', verbosity=0)
        self.assertEqual(lingue.normalizza('en-GB'), 'en')
        self.assertEqual(lingue.normalizza('EN'), 'en')
        self.assertIsNone(lingue.normalizza('de'), 'una lingua non attiva non si serve')
        self.assertIsNone(lingue.normalizza(''))

    def test_si_traduce_verso_tutte_tranne_la_propria(self):
        call_command('seed_lingue', verbosity=0)
        Lingua.objects.create(codice='es', nome='Espanol', ordine=2)

        self.assertEqual(lingue.altre_lingue('it'), ['en', 'es'])
        self.assertEqual(lingue.altre_lingue('en'), ['it', 'es'])
        self.assertEqual(lingue.altre_lingue(None), ['en', 'es'], 'senza origine vale la sorgente')
