"""La traduzione di pagine e articoli.

Il punto da dimostrare non e' che il traduttore traduca — quello e' compito suo
— ma che la **struttura sopravviva**: grassetti, link e immagini non passano mai
dal traduttore, e devono ritrovarsi identici dall'altra parte.
"""

import json

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings
from wagtail.models import Locale, Page, Site

from cms.models import ArticleType, HomePage
from section.models import Card
from section.schema import estrai_testi, reinserisci_testi
from traduzione import lingue
from traduzione.models import Lingua, Traduzione
from traduzione.percorsi import applica, estrai
from traduzione.servizio import traduci, traduci_tutto
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
        self.assertEqual([t.target_language for t in traduci_tutto(card, MotoreFinto())],
                         ['en'])

    def test_titolo_corpo_e_informazioni_viaggiano_insieme(self):
        """Il traduttore vede tutto l'articolo in una volta, quindi puo' essere
        coerente fra il titolo e il testo."""
        finto = MotoreFinto()
        traduci(self.crea(), 'en', finto)
        inviati, da, a = finto.chiamate[0]
        self.assertEqual((da, a), ('it', 'en'))
        self.assertIn('title', inviati)
        self.assertIn('body:0.1', inviati)
        self.assertIn('info_values:giorni', inviati)

    def test_la_struttura_sopravvive_alla_traduzione(self):
        """La formattazione non passa mai dal traduttore, quindi non torna rotta."""
        card = self.crea()
        traduci(card, 'en', MotoreFinto())
        t = card.traduzioni.get(target_language='en')

        dati = applica(card, t.texts)
        para = dati['body']['content'][0]['content']
        self.assertEqual(para[1]['text'], 'GRASSETTO')
        self.assertEqual(para[1]['marks'], [{'type': 'bold'}])
        self.assertEqual(para[2]['marks'][0]['attrs']['href'], 'https://rotary.org')
        self.assertEqual(dati['body']['content'][1]['attrs']['assetId'], 7)
        self.assertEqual(dati['title'], 'IL TITOLO')
        self.assertEqual(dati['info_values'], {'giorni': '3'})

    def test_una_correzione_a_mano_non_viene_sovrascritta(self):
        """Chi l'ha scritta ne sapeva piu' della macchina.

        E il blocco e' per percorso, non per oggetto: il resto dell'articolo
        continua a rinfrescarsi.
        """
        card = self.crea()
        Traduzione.objects.create(
            content_type=ContentType.objects.get_for_model(card),
            object_id=str(card.pk), target_language='en', source_language='it',
            texts={'title': 'Scritto da una persona'},
            locked_paths=['title'], provider='umano')

        traduci(card, 'en', MotoreFinto())

        t = card.traduzioni.get(target_language='en')
        self.assertEqual(t.texts['title'], 'Scritto da una persona')
        self.assertEqual(t.texts['subtitle'], 'IL SOTTOTITOLO',
                         'il resto deve essersi tradotto lo stesso')

    def test_col_motore_di_identita_finisce_in_revisione(self):
        t = traduci(self.crea(), 'en', MotoreIdentita())
        self.assertTrue(t.needs_review)
        self.assertEqual(t.provider, 'identita')

    def test_l_api_serve_la_lingua_richiesta(self):
        card = self.crea()
        traduci(card, 'en', MotoreFinto())
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
        traduci(card, 'en', MotoreFinto())
        prima = card.traduzioni.get(target_language='en').updated_at
        call_command('translate_pending', verbosity=0)
        dopo = card.traduzioni.get(target_language='en').updated_at
        self.assertEqual(prima, dopo)

    def test_ma_ritraduce_se_l_originale_e_cambiato(self):
        """Il buco che c'era prima: modificare un articolo lasciava l'inglese
        fermo per sempre, perche' bastava che una traduzione esistesse."""
        card = self.crea()
        traduci(card, 'en', MotoreFinto())
        self.assertEqual(card.traduzioni.get(target_language='en').texts['title'],
                         'IL TITOLO')

        card.title = 'Un titolo nuovo'
        card.save()
        traduci(card, 'en', MotoreFinto())

        self.assertEqual(card.traduzioni.get(target_language='en').texts['title'],
                         'UN TITOLO NUOVO')

    def test_una_frase_cancellata_sparisce_dalla_traduzione(self):
        card = self.crea()
        traduci(card, 'en', MotoreFinto())
        self.assertIn('subtitle', card.traduzioni.get(target_language='en').texts)

        card.subtitle = ''
        card.save()
        traduci(card, 'en', MotoreFinto())

        self.assertNotIn('subtitle', card.traduzioni.get(target_language='en').texts,
                         'una traduzione non conserva frasi che l autore ha tolto')


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


class FlussoTest(TestCase):
    """Le pagine del CMS: uno StreamField non e' una stringa.

    Questi tre test coprono i modi in cui il lavoro puo' fallire **in
    silenzio**: il testo resta in italiano, e in italiano assomiglia molto a
    una traduzione non ancora fatta, quindi nessuno lo segnala.
    """

    @classmethod
    def setUpTestData(cls):
        call_command('seed_lingue', verbosity=0)
        locale = Locale.get_default()
        home = HomePage(title='Casa', slug='casa', locale=locale)
        Page.objects.get(depth=1).add_child(instance=home)
        sito = Site.objects.get(is_default_site=True)
        sito.root_page = home
        sito.save()
        cls.home = home

    def pagina(self, corpo):
        from cms.models import StandardPage
        p = StandardPage(title='Prova', slug='prova', locale=Locale.get_default(),
                         body=corpo)
        self.home.add_child(instance=p)
        p.save_revision().publish()
        return StandardPage.objects.get(pk=p.pk)

    def corpo_di_prova(self):
        return [
            ('hero', {'title': 'Il titolo', 'description': 'La descrizione',
                      'tag': 'etichetta', 'surface': 'white',
                      'scroll_to_id': 'ancora-che-non-si-traduce'}),
            ('quote', {'quote': 'Una citazione', 'author': 'Chi l ha detta'}),
        ]

    def test_gli_identificatori_non_si_traducono(self):
        """Tradurre `ancora-che-non-si-traduce` romperebbe il collegamento
        che ci punta, e lo romperebbe in silenzio."""
        p = self.pagina(self.corpo_di_prova())
        testi = estrai(p)

        self.assertTrue(any(v == 'Il titolo' for v in testi.values()))
        self.assertNotIn('ancora-che-non-si-traduce', testi.values())

    def test_riordinare_i_blocchi_non_perde_la_traduzione(self):
        """I percorsi sono gli id dei blocchi, non la loro posizione."""
        p = self.pagina(self.corpo_di_prova())
        traduci(p, 'en', MotoreFinto())
        prima = applica(p, p.traduzioni.get(target_language='en').texts)['body']
        titolo_tradotto = [b for b in prima if b['type'] == 'hero'][0]['value']['title']
        self.assertEqual(titolo_tradotto, 'IL TITOLO')

        # Si scambiano i due blocchi, tenendo i loro id.
        grezzo = list(p.body.raw_data)
        p.body = [grezzo[1], grezzo[0]]
        p.save()

        dopo = applica(p, p.traduzioni.get(target_language='en').texts)['body']
        self.assertEqual(dopo[0]['type'], 'quote', 'i blocchi sono davvero scambiati')
        self.assertEqual([b for b in dopo if b['type'] == 'hero'][0]['value']['title'],
                         'IL TITOLO', 'la traduzione e rimasta attaccata al suo blocco')

    def test_un_blocco_nuovo_compare_nella_lingua_originale(self):
        """Non omesso: in italiano dentro una pagina inglese, finche' il cron
        non passa. Un paragrafo che sparisce sarebbe peggio."""
        p = self.pagina(self.corpo_di_prova())
        traduci(p, 'en', MotoreFinto())

        grezzo = list(p.body.raw_data)
        grezzo.append({'type': 'quote', 'id': 'nuovo-blocco',
                       'value': {'quote': 'Aggiunta dopo', 'author': 'X'}})
        p.body = grezzo
        p.save()

        corpo = applica(p, p.traduzioni.get(target_language='en').texts)['body']
        nuovo = [b for b in corpo if b.get('id') == 'nuovo-blocco'][0]
        self.assertEqual(nuovo['value']['quote'], 'Aggiunta dopo')

    def test_ogni_blocco_del_catalogo_e_classificato(self):
        """Il controllo di sistema, eseguito come test.

        Un blocco con un tipo di campo mai visto non verrebbe ne tradotto ne
        saltato: cadrebbe fuori, e il suo testo non arriverebbe mai al motore.
        """
        from traduzione.checks import controlla_catalogo_blocchi
        self.assertEqual(controlla_catalogo_blocchi(None), [])


class RiccoTest(TestCase):
    """L'HTML: i tag non passano dal traduttore, quindi non tornano rotti."""

    def test_i_tag_restano_dove_sono(self):
        from traduzione.generi import RICCO
        html = '<p>Ciao <b>mondo</b> e <a href="https://rotary.org">link</a></p>'

        testi = RICCO.estrai(html)
        tradotto = RICCO.reinserisci(html, {k: v.upper() for k, v in testi.items()})

        self.assertIn('<b>MONDO</b>', tradotto)
        self.assertIn('href="https://rotary.org"', tradotto)
        self.assertIn('CIAO', tradotto)

    def test_il_corpo_di_un_post_si_traduce(self):
        """Prima no: in inglese si leggevano titolo e sommario tradotti e il
        corpo in italiano."""
        from traduzione.traducibili import TRADUCIBILI
        from traduzione.generi import RICCO
        self.assertIs(TRADUCIBILI['forum.Post']['content_html'], RICCO)


class SenzaUnaQueryPerRiga(TestCase):
    """Servire una lista tradotta non deve costare una query per articolo.

    E' il modo piu' facile di peggiorare le cose senza accorgersene: tutto
    funziona, e il sito diventa lento solo quando i contenuti crescono.
    """

    @classmethod
    def setUpTestData(cls):
        call_command('seed_lingue', verbosity=0)
        locale = Locale.get_default()
        home = HomePage(title='Casa', slug='casa', locale=locale)
        Page.objects.get(depth=1).add_child(instance=home)
        sito = Site.objects.get(is_default_site=True)
        sito.root_page = home
        sito.save()
        call_command('seed_article_types', verbosity=0)
        autore = User.objects.create_user(
            username='q', email='q@prova.it', password='prova12345')
        tipo = ArticleType.objects.get(key='itinerario')
        for i in range(12):
            card = Card.objects.create(
                slug=f'articolo-{i}', title=f'Titolo {i}', subtitle='Sottotitolo',
                body=documento(), article_type=tipo, author=autore,
                is_published=True, source_locale='it')
            traduci(card, 'en', MotoreFinto())

    def query_di_traduzione(self):
        """Quante volte si interroga la tabella delle traduzioni.

        Si contano solo quelle: il resto della vista ha un N+1 suo, su allegati
        e salvataggi, che c'era gia' prima e non riguarda questo lavoro.
        """
        import re
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as c:
            r = self.client.get('/api/section/articles/',
                                {'type': 'itinerario', 'locale': 'en'})
            self.assertEqual(r.status_code, 200)
        return sum(1 for q in c.captured_queries
                   if re.search(r'FROM "traduzione_traduzione"', q['sql']))

    def test_una_query_sola_per_tutte_le_traduzioni(self):
        """Non una per articolo: e' il senso del prefetch."""
        self.assertEqual(self.query_di_traduzione(), 1)

        # E resta una anche con quattro volte gli articoli.
        Card.objects.filter(slug__startswith='articolo-').update(is_published=True)
        self.assertEqual(self.query_di_traduzione(), 1)

    def test_la_lista_e_davvero_tradotta(self):
        r = self.client.get('/api/section/articles/',
                            {'type': 'itinerario', 'locale': 'en'})
        titoli = [c['title'] for c in r.json()]
        self.assertTrue(titoli, 'la lista non deve essere vuota')
        self.assertTrue(all(t == t.upper() for t in titoli),
                        f'qualche titolo non e tradotto: {titoli[:3]}')


class CodaDiRevisioneTest(TestCase):
    """La correzione a mano, e cosa le succede dopo.

    E' il punto in cui una persona sa piu' della macchina, e la macchina deve
    smettere di insistere — ma solo sulla frase che la persona ha toccato.
    """

    @classmethod
    def setUpTestData(cls):
        call_command('seed_lingue', verbosity=0)
        locale = Locale.get_default()
        home = HomePage(title='Casa', slug='casa', locale=locale)
        Page.objects.get(depth=1).add_child(instance=home)
        sito = Site.objects.get(is_default_site=True)
        sito.root_page = home
        sito.save()
        call_command('seed_article_types', verbosity=0)
        cls.autore = User.objects.create_user(
            username='rev', email='rev@prova.it', password='prova12345')

    def articolo(self):
        return Card.objects.create(
            slug='da-rivedere', title='Il titolo', subtitle='Il sottotitolo',
            article_type=ArticleType.objects.get(key='itinerario'),
            author=self.autore, is_published=True, source_locale='it')

    def test_il_form_mostra_una_riga_per_frase_con_l_originale(self):
        from cms.forms import form_traduzione
        card = self.articolo()
        traduci(card, 'en', MotoreFinto())

        form = form_traduzione()(instance=card.traduzioni.get(target_language='en'))

        campi = [n for n in form.fields if n.startswith('testo__')]
        self.assertIn('testo__title', campi)
        self.assertIn('testo__subtitle', campi)
        # L'aiuto e' il testo di partenza: e' l'unica cosa che serve per correggere.
        self.assertEqual(form.fields['testo__title'].help_text, 'Il titolo')
        self.assertEqual(form.fields['testo__title'].initial, 'IL TITOLO')

    def test_correggere_una_frase_blocca_quella_e_non_le_altre(self):
        from cms.forms import form_traduzione
        card = self.articolo()
        traduci(card, 'en', MotoreFinto())
        t = card.traduzioni.get(target_language='en')

        form = form_traduzione()(
            instance=t,
            data={'testo__title': 'A proper English title',
                  'testo__subtitle': t.texts['subtitle'],
                  'needs_review': False})
        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        t.refresh_from_db()
        self.assertEqual(t.locked_paths, ['title'])
        self.assertTrue(t.human_locked)
        self.assertFalse(t.needs_review)

        # E la correzione sopravvive a una ritraduzione forzata, mentre il
        # resto si rinfresca.
        card.subtitle = 'Un sottotitolo nuovo'
        card.save()
        traduci(card, 'en', MotoreFinto(), forza=True)

        t.refresh_from_db()
        self.assertEqual(t.texts['title'], 'A proper English title')
        self.assertEqual(t.texts['subtitle'], 'UN SOTTOTITOLO NUOVO')

    def test_svuotare_un_campo_lo_sblocca(self):
        """Ripensarci deve essere possibile quanto correggere."""
        from cms.forms import form_traduzione
        card = self.articolo()
        traduci(card, 'en', MotoreFinto())
        t = card.traduzioni.get(target_language='en')
        form_traduzione()(instance=t, data={'testo__title': 'Mio', 'needs_review': False}).save()
        self.assertIn('title', t.locked_paths)

        form_traduzione()(instance=t, data={'testo__title': '', 'needs_review': False}).save()

        t.refresh_from_db()
        self.assertNotIn('title', t.locked_paths)
        self.assertNotIn('title', t.texts)
