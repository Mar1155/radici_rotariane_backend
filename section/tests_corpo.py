"""Il corpo di un articolo come documento, e le immagini fuori dal testo.

Sono i test della fase che ha sostituito l'editor. Due cose da dimostrare: che
un documento malevolo non passa, e che le immagini non tornano dentro il testo.
"""

import json
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient
from wagtail.models import Locale, Page, Site

from cms.models import ArticleType, HomePage
from section.media import ImmagineNonValida, normalizza
from section.media_refs import identificativi_media
from section.models import Card, MediaAsset
from section.schema import CorpoNonValido, pulisci_corpo, testo_semplice

User = get_user_model()


def immagine(colore='#17458f', dimensioni=(400, 300), formato='JPEG'):
    buf = BytesIO()
    Image.new('RGB', dimensioni, colore).save(buf, format=formato)
    return SimpleUploadedFile('prova.jpg', buf.getvalue(), 'image/jpeg')


def paragrafo(testo):
    return {'type': 'paragraph', 'content': [{'type': 'text', 'text': testo}]}


class SchemaTest(TestCase):
    """Il documento si ricostruisce copiando il previsto, non ripulendo il resto."""

    TUTTO = ['paragraph', 'heading', 'image', 'gallery', 'quote', 'list', 'embed']

    def test_un_nodo_sconosciuto_non_viene_copiato(self):
        doc = {'type': 'doc', 'content': [
            paragrafo('buono'),
            {'type': 'script', 'content': [{'type': 'text', 'text': 'alert(1)'}]},
        ]}
        pulito = pulisci_corpo(doc, self.TUTTO)
        self.assertEqual([n['type'] for n in pulito['content']], ['paragraph'])

    def test_un_link_javascript_cade_ma_il_testo_resta(self):
        doc = {'type': 'doc', 'content': [{'type': 'paragraph', 'content': [
            {'type': 'text', 'text': 'clicca',
             'marks': [{'type': 'link', 'attrs': {'href': 'javascript:alert(1)'}}]},
        ]}]}
        pulito = pulisci_corpo(doc, self.TUTTO)
        testo = pulito['content'][0]['content'][0]
        self.assertEqual(testo['text'], 'clicca')
        self.assertNotIn('marks', testo)

    def test_un_link_normale_sopravvive(self):
        doc = {'type': 'doc', 'content': [{'type': 'paragraph', 'content': [
            {'type': 'text', 'text': 'Rotary',
             'marks': [{'type': 'link', 'attrs': {'href': 'https://rotary.org'}}]},
        ]}]}
        pulito = pulisci_corpo(doc, self.TUTTO)
        self.assertEqual(pulito['content'][0]['content'][0]['marks'][0]['attrs']['href'],
                         'https://rotary.org')

    def test_la_palette_del_tipo_decide(self):
        """Il frontend nasconde i pulsanti, ma e' il server a decidere."""
        doc = {'type': 'doc', 'content': [
            paragrafo('testo'),
            {'type': 'blockquote', 'content': [paragrafo('citazione')]},
        ]}
        senza = pulisci_corpo(doc, ['paragraph'])
        self.assertEqual([n['type'] for n in senza['content']], ['paragraph'])
        con = pulisci_corpo(doc, ['paragraph', 'quote'])
        self.assertEqual([n['type'] for n in con['content']], ['paragraph', 'blockquote'])

    def test_un_titolo_fuori_scala_rientra(self):
        doc = {'type': 'doc', 'content': [
            {'type': 'heading', 'attrs': {'level': 9},
             'content': [{'type': 'text', 'text': 'x'}]}]}
        pulito = pulisci_corpo(doc, self.TUTTO)
        self.assertEqual(pulito['content'][0]['attrs']['level'], 2)

    def test_un_immagine_senza_riferimento_non_e_un_immagine(self):
        doc = {'type': 'doc', 'content': [
            {'type': 'image', 'attrs': {'src': 'data:image/png;base64,AAAA'}}]}
        self.assertIsNone(pulisci_corpo(doc, self.TUTTO))

    def test_l_annidamento_ha_un_fondo(self):
        nodo = paragrafo('fondo')
        for _ in range(40):
            nodo = {'type': 'blockquote', 'content': [nodo]}
        pulito = pulisci_corpo({'type': 'doc', 'content': [nodo]}, self.TUTTO)
        profondita = 0
        corrente = pulito
        while corrente and corrente.get('content'):
            corrente = corrente['content'][0]
            profondita += 1
        self.assertLess(profondita, 20)

    def test_un_corpo_che_non_e_un_documento_e_un_errore(self):
        with self.assertRaises(CorpoNonValido):
            pulisci_corpo({'type': 'paragraph'}, self.TUTTO)

    def test_il_corpo_vuoto_e_ammesso(self):
        self.assertIsNone(pulisci_corpo(None, self.TUTTO))
        self.assertIsNone(pulisci_corpo({'type': 'doc', 'content': []}, self.TUTTO))

    def test_il_testo_si_estrae_per_la_traduzione(self):
        doc = {'type': 'doc', 'content': [
            paragrafo('Prima riga'),
            {'type': 'heading', 'attrs': {'level': 2},
             'content': [{'type': 'text', 'text': 'Titolo'}]},
        ]}
        self.assertEqual(testo_semplice(doc), 'Prima riga\nTitolo')


class NormalizzazioneTest(TestCase):
    """Decodificare e ri-codificare e' cio' che protegge, non l'estensione."""

    def test_un_jpeg_diventa_webp(self):
        file, meta = normalizza(immagine())
        self.assertEqual(Image.open(BytesIO(file.read())).format, 'WEBP')
        self.assertEqual((meta['width'], meta['height']), (400, 300))

    def test_le_immagini_enormi_si_ridimensionano(self):
        _, meta = normalizza(immagine(dimensioni=(5000, 3000)))
        self.assertLessEqual(max(meta['width'], meta['height']), 2000)

    def test_un_file_che_non_e_un_immagine_e_rifiutato(self):
        finto = SimpleUploadedFile('finta.jpg', b'non sono una immagine', 'image/jpeg')
        with self.assertRaises(ImmagineNonValida):
            normalizza(finto)

    def test_lo_stesso_file_da_sempre_la_stessa_impronta(self):
        """E' cio' che permette di non duplicare un caricamento ripetuto.

        Vale per lo stesso file, non per "la stessa immagine": un JPEG e un PNG
        dello stesso soggetto danno pixel diversi, perche' il JPEG ha perdita.
        """
        _, a = normalizza(immagine())
        _, b = normalizza(immagine())
        self.assertEqual(a['checksum'], b['checksum'])

    def test_immagini_diverse_hanno_impronte_diverse(self):
        _, a = normalizza(immagine(colore='#17458f'))
        _, b = normalizza(immagine(colore='#f7a81b'))
        self.assertNotEqual(a['checksum'], b['checksum'])


class UploadTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.socio = User.objects.create_user(
            username='autore', email='autore@prova.it', password='prova12345')
        cls.socio.email_verified_at = timezone.now()
        cls.socio.save()

    def client_autenticato(self):
        c = APIClient()
        c.force_authenticate(user=self.socio)
        return c

    def test_serve_l_accesso(self):
        r = self.client.post('/api/section/media/upload/', {'file': immagine()})
        self.assertEqual(r.status_code, 401)

    def test_carica_e_restituisce_un_identificativo(self):
        r = self.client_autenticato().post(
            '/api/section/media/upload/', {'file': immagine()})
        self.assertEqual(r.status_code, 201)
        self.assertIn('id', r.json())
        self.assertTrue(r.json()['url'].endswith('.webp'))

    def test_la_stessa_immagine_non_si_duplica(self):
        c = self.client_autenticato()
        primo = c.post('/api/section/media/upload/', {'file': immagine()}).json()
        secondo = c.post('/api/section/media/upload/', {'file': immagine()})
        self.assertEqual(secondo.status_code, 200)
        self.assertEqual(primo['id'], secondo.json()['id'])
        self.assertEqual(MediaAsset.objects.count(), 1)


class CorpoNellaApiTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        locale = Locale.get_default()
        home = HomePage(title='Casa', slug='casa', locale=locale)
        Page.objects.get(depth=1).add_child(instance=home)
        sito = Site.objects.get(is_default_site=True)
        sito.root_page = home
        sito.save()
        call_command('seed_article_types', verbosity=0)
        cls.socio = User.objects.create_user(
            username='a2', email='a2@prova.it', password='prova12345')
        cls.socio.email_verified_at = timezone.now()
        cls.socio.save()

    def test_creare_un_articolo_con_corpo_strutturato(self):
        c = APIClient()
        c.force_authenticate(user=self.socio)
        asset = c.post('/api/section/media/upload/', {'file': immagine()}).json()
        doc = {'type': 'doc', 'content': [
            paragrafo('Il corpo'),
            {'type': 'image', 'attrs': {'assetId': asset['id'], 'alt': 'foto'}},
        ]}
        r = c.post('/api/section/articles/storia/create', {
            'title': 'Con corpo', 'subtitle': 'Sottotitolo',
            'body': json.dumps(doc), 'tags': '[]', 'infoValues': '{}',
            'coverImage': immagine(),
        })
        self.assertEqual(r.status_code, 201, r.content[:300])
        card = Card.objects.get(slug='con-corpo')
        self.assertEqual([n['type'] for n in card.body['content']],
                         ['paragraph', 'image'])
        self.assertEqual(identificativi_media(card.body), [asset['id']])

    def test_il_corpo_non_contiene_indirizzi_ma_identificativi(self):
        """Se i file si spostano, gli articoli non vanno toccati."""
        c = APIClient()
        c.force_authenticate(user=self.socio)
        asset = c.post('/api/section/media/upload/', {'file': immagine()}).json()
        doc = {'type': 'doc', 'content': [
            {'type': 'image', 'attrs': {'assetId': asset['id']}}]}
        c.post('/api/section/articles/storia/create', {
            'title': 'Solo immagine', 'subtitle': 's',
            'body': json.dumps(doc), 'tags': '[]', 'infoValues': '{}',
            'coverImage': immagine(),
        })
        card = Card.objects.get(slug='solo-immagine')
        self.assertNotIn('http', json.dumps(card.body))
        # L'indirizzo lo aggiunge l'API, accanto al documento.
        d = self.client.get(f'/api/section/cards/{card.slug}').json()
        self.assertIn(str(asset['id']), d['assets'])

    def test_l_elenco_non_porta_il_corpo(self):
        """Il corpo di un articolo non serve a chi guarda una griglia."""
        r = self.client.get('/api/section/articles/')
        if r.json():
            self.assertNotIn('body', r.json()[0])

class BiografiaTest(TestCase):
    """La biografia e' HTML scritto da una persona, e va ripulita in scrittura.

    Veniva salvata cosi' com'era e resa con `dangerouslySetInnerHTML` sul
    profilo, sulla pagina del club e su /skills: bastava mettere uno <script>
    nella propria bio perche' girasse a chiunque le aprisse.
    """

    def setUp(self):
        self.utente = User.objects.create_user(
            username='bio', email='bio@prova.it', password='prova12345')
        self.utente.email_verified_at = timezone.now()
        self.utente.save()
        self.client_auth = APIClient()
        self.client_auth.force_authenticate(user=self.utente)

    def _salva(self, bio):
        r = self.client_auth.patch('/api/users/me/', {'bio': bio}, format='json')
        self.assertEqual(r.status_code, 200, r.content[:200])
        return r.json()['bio']

    def test_uno_script_non_sopravvive(self):
        self.assertNotIn('<script', self._salva('<p>ciao</p><script>alert(1)</script>'))

    def test_un_gestore_di_evento_non_sopravvive(self):
        salvata = self._salva('<img src=x onerror=alert(1)>')
        self.assertNotIn('onerror', salvata)
        self.assertNotIn('<img', salvata)

    def test_la_formattazione_normale_sopravvive(self):
        salvata = self._salva('<p>Sono <strong>Anna</strong> e faccio <em>questo</em>.</p>')
        self.assertIn('<strong>Anna</strong>', salvata)
        self.assertIn('<em>questo</em>', salvata)

class BozzeEGeografiaTest(TestCase):
    """I difetti che hanno reso inutilizzabile la creazione articoli.

    Erano quattro, e tre avevano una causa diversa da quella che sembrava.
    """

    @classmethod
    def setUpTestData(cls):
        locale = Locale.get_default()
        home = HomePage(title='Casa', slug='casa', locale=locale)
        Page.objects.get(depth=1).add_child(instance=home)
        sito = Site.objects.get(is_default_site=True)
        sito.root_page = home
        sito.save()
        # La geografia prima dei tipi, come in `build_site`: e' da li' che
        # `seed_article_types` capisce quali tag sono in realta' luoghi.
        call_command('seed_geo', verbosity=0)
        call_command('seed_article_types', verbosity=0)
        cls.socio = User.objects.create_user(
            username='a3', email='a3@prova.it', password='prova12345')
        cls.socio.email_verified_at = timezone.now()
        cls.socio.save()

    def client_auth(self):
        c = APIClient()
        c.force_authenticate(user=self.socio)
        return c

    def test_una_bozza_col_solo_titolo_si_salva(self):
        """Il server validava anche le bozze, e "salva bozza" rispondeva
        chiedendo campi che stanno in un'altra parte del form."""
        r = self.client_auth().post('/api/section/articles/storia/create', {
            'title': 'Appena iniziata', 'isPublished': 'false',
            'tags': '[]', 'infoValues': '{}',
        })
        self.assertEqual(r.status_code, 201, r.content[:300])
        self.assertFalse(Card.objects.get(slug='appena-iniziata').is_published)

    def test_pubblicare_invece_valida(self):
        r = self.client_auth().post('/api/section/articles/storia/create', {
            'title': 'Incompleta', 'isPublished': 'true',
            'tags': '[]', 'infoValues': '{}',
        })
        self.assertEqual(r.status_code, 400)

    def test_nessun_tipo_chiede_cio_che_non_si_puo_dare(self):
        """`itinerario` aveva i tag obbligatori e zero tag ammessi: nessuno
        poteva pubblicare, e dal form non si capiva perche'."""
        for tipo in ArticleType.objects.all():
            if 'tags' in (tipo.required_fields or []):
                self.assertTrue(tipo.allowed_tags.exists(),
                                f'{tipo.key}: tag obbligatori ma nessuno ammesso')
            if 'infoElements' in (tipo.required_fields or []):
                self.assertTrue(tipo.info_elements.exists(), tipo.key)

    def test_il_modello_rifiuta_lo_stato_impossibile(self):
        from django.core.exceptions import ValidationError
        tipo = ArticleType.objects.get(key='storia')
        tipo.allowed_tags.all().delete()
        tipo.active_fields = list(set(tipo.active_fields) | {'tags'})
        tipo.required_fields = list(set(tipo.required_fields) | {'tags'})
        with self.assertRaises(ValidationError):
            tipo.full_clean()

    def test_l_area_geografica_si_puo_impostare(self):
        """La tassonomia e il filtro esistevano dalla fase 4, ma un articolo
        scritto dall'app non poteva avere un'area: non era impostabile."""
        r = self.client_auth().post('/api/section/articles/itinerario/create', {
            'title': 'Con area', 'subtitle': 's', 'location': 'Siena',
            'geoArea': 'siena', 'tags': '[]', 'infoValues': '{"giorni":"3"}',
            'coverImage': immagine(), 'isPublished': 'false',
        })
        self.assertEqual(r.status_code, 201, r.content[:300])
        card = Card.objects.get(slug='con-area')
        self.assertIsNotNone(card.geo_area)
        self.assertEqual(card.geo_area.key, 'siena')

    def test_il_filtro_geografico_e_gerarchico(self):
        c = self.client_auth()
        r = c.post('/api/section/articles/itinerario/create', {
            'title': 'In Toscana', 'subtitle': 's', 'location': 'Siena',
            'geoArea': 'siena', 'tags': '[]', 'infoValues': '{"giorni":"3"}',
            'coverImage': immagine(),
            'body': json.dumps({'type': 'doc', 'content': [paragrafo('Il percorso')]}),
        })
        self.assertEqual(r.status_code, 201, r.content[:300])
        def slugs(area):
            return [x['slug'] for x in
                    self.client.get('/api/section/articles/', {'geo': area}).json()]
        self.assertIn('in-toscana', slugs('siena'))
        self.assertIn('in-toscana', slugs('toscana'))   # la regione contiene la provincia
        self.assertNotIn('in-toscana', slugs('lombardia'))

class BozzeVisibiliTest(TestCase):
    """Salvare una bozza senza poterla ritrovare e' mezza funzione.

    Una bozza e' un articolo con `is_published=False`: nessun modello nuovo. Il
    server e' l'unico a sapere cosa sia, e la restituisce solo al suo autore.
    """

    @classmethod
    def setUpTestData(cls):
        locale = Locale.get_default()
        home = HomePage(title='Casa', slug='casa', locale=locale)
        Page.objects.get(depth=1).add_child(instance=home)
        sito = Site.objects.get(is_default_site=True)
        sito.root_page = home
        sito.save()
        call_command('seed_geo', verbosity=0)
        call_command('seed_article_types', verbosity=0)

        cls.autore = User.objects.create_user(
            username='au', email='au@prova.it', password='prova12345')
        cls.autore.email_verified_at = timezone.now()
        cls.autore.save()
        cls.estraneo = User.objects.create_user(
            username='es', email='es@prova.it', password='prova12345')

        tipo = ArticleType.objects.get(key='storia')
        # Completa: una bozza a meta' non si puo' pubblicare, ed e' giusto cosi'.
        cls.bozza = Card.objects.create(
            slug='mia-bozza', title='Mia bozza', subtitle='Sottotitolo',
            body={'type': 'doc', 'content': [paragrafo('Il corpo')]},
            cover_image='cards/covers/finta.jpg',
            article_type=tipo, author=cls.autore, is_published=False)
        cls.pubblicato = Card.objects.create(
            slug='mio-pubblicato', title='Pubblicato', article_type=tipo,
            author=cls.autore, is_published=True)

    def elenco(self, client, **params):
        params.setdefault('user_id', self.autore.id)
        return [c['slug'] for c in client.get('/api/section/cards/user/', params).json()]

    def _suo(self):
        c = APIClient()
        c.force_authenticate(user=self.autore)
        return c

    def test_l_autore_ritrova_le_proprie_bozze(self):
        self.assertEqual(self.elenco(self._suo(), stato='bozze'), ['mia-bozza'])

    def test_le_pubblicazioni_non_contengono_bozze(self):
        """Mescolarle non lascia capire cosa e' online."""
        self.assertEqual(self.elenco(self._suo(), stato='pubblicati'), ['mio-pubblicato'])

    def test_un_estraneo_non_vede_le_bozze(self):
        c = APIClient()
        c.force_authenticate(user=self.estraneo)
        self.assertEqual(self.elenco(c, stato='pubblicati'), ['mio-pubblicato'])
        self.assertNotIn('mia-bozza', self.elenco(c))

    def test_a_un_estraneo_che_chiede_le_bozze_si_risponde_vuoto(self):
        """Non il pubblicato al loro posto: chiedeva bozze, non altro."""
        self.assertEqual(self.elenco(self.client, stato='bozze'), [])

    def test_si_possono_chiedere_le_bozze_di_un_tipo_solo(self):
        """E' cio' che permette di chiedere "hai itinerari non finiti?"."""
        self.assertEqual(self.elenco(self._suo(), stato='bozze', type='storia'),
                         ['mia-bozza'])
        self.assertEqual(self.elenco(self._suo(), stato='bozze', type='evento'), [])

    def test_pubblicare_una_bozza_la_fa_uscire(self):
        c = self._suo()
        r = c.patch(f'/api/section/cards/{self.bozza.slug}',
                    {'isPublished': True}, format='json')
        self.assertEqual(r.status_code, 200, r.content[:200])
        self.bozza.refresh_from_db()
        self.assertTrue(self.bozza.is_published)
        pubblici = [x['slug'] for x in self.client.get('/api/section/articles/').json()]
        self.assertIn('mia-bozza', pubblici)

    def test_le_bozze_si_ordinano_per_ultima_modifica(self):
        """Si riprende quella che si stava scrivendo, non la piu' vecchia."""
        tipo = ArticleType.objects.get(key='storia')
        Card.objects.create(slug='piu-recente', title='Recente', article_type=tipo,
                            author=self.autore, is_published=False)
        self.assertEqual(self.elenco(self._suo(), stato='bozze')[0], 'piu-recente')
