"""I tag si dividono in categorie, e la divisione arriva fino al frontend.

Dieci tag in fila non sono una tendina: "Attivo" e "Educazione" rispondono a
due domande diverse e stavano nello stesso mucchio. Qui si verifica che il
gruppo sia un dato del tipo di articolo — quindi modificabile dal pannello,
senza deploy — e che l'API lo consegni in un ordine stabile.
"""

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from cms.models import ArticleType, ArticleTypeTag, ArticleTypeTagCategory


class CategorieDeiTagTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_lingue', verbosity=0)
        call_command('seed_geo', verbosity=0)
        call_command('seed_article_types', verbosity=0)

    def test_il_progetto_ha_le_tre_categorie(self):
        t = ArticleType.objects.get(key='progetto')
        self.assertEqual(
            [c.key for c in t.tag_categories.all()],
            ['stato', 'ambito', 'localizzazione'])

    def test_la_localizzazione_elenca_i_quattro_ambiti(self):
        t = ArticleType.objects.get(key='progetto')
        self.assertEqual(
            [g.key for g in t.allowed_tags.filter(category='localizzazione')],
            ['progetto-di-club', 'progetto-distrettuale',
             'progetto-nazionale', 'global-grant'])

    def test_stato_e_ambito_sono_separati(self):
        """La richiesta di partenza: "attivo/completato" non sono un ambito."""
        t = ArticleType.objects.get(key='progetto')
        per_categoria = {}
        for g in t.allowed_tags.all():
            per_categoria.setdefault(g.category, []).append(g.key)
        self.assertEqual(sorted(per_categoria['stato']),
                         ['attivo', 'completato', 'urgente'])
        self.assertIn('educazione', per_categoria['ambito'])
        self.assertNotIn('attivo', per_categoria['ambito'])

    def test_un_tipo_senza_gruppi_distinti_resta_piatto(self):
        """Inventare categorie dove non ce ne sono e' peggio dell'elenco piatto."""
        t = ArticleType.objects.get(key='tradizione')
        self.assertEqual(list(t.tag_categories.all()), [])
        self.assertTrue(t.allowed_tags.exists())
        self.assertEqual({g.category for g in t.allowed_tags.all()}, {''})

    def test_ogni_tag_punta_a_una_categoria_che_esiste(self):
        for t in ArticleType.objects.all():
            with self.subTest(t.key):
                definite = {c.key for c in t.tag_categories.all()}
                usate = {g.category for g in t.allowed_tags.all() if g.category}
                self.assertLessEqual(usate, definite)

    def test_una_categoria_inventata_non_si_salva(self):
        """L'errore si vede al salvataggio, non come un gruppo senza nome."""
        t = ArticleType.objects.get(key='evento')
        tag = t.allowed_tags.first()
        tag.category = 'inesistente'
        tag.save()
        with self.assertRaises(ValidationError) as ctx:
            t.full_clean()
        self.assertIn('inesistente', str(ctx.exception))

    def test_l_api_consegna_categorie_e_appartenenza(self):
        risposta = APIClient().get('/api/cms/v1/article-types/')
        self.assertEqual(risposta.status_code, 200)
        tipi = {t['key']: t for t in risposta.json()['articleTypes']}

        progetto = tipi['progetto']
        self.assertEqual([c['key'] for c in progetto['tagCategories']],
                         ['stato', 'ambito', 'localizzazione'])
        self.assertTrue(all(c['label'] for c in progetto['tagCategories']))

        per_chiave = {g['key']: g for g in progetto['tags']}
        self.assertEqual(per_chiave['attivo']['category'], 'stato')
        self.assertEqual(per_chiave['global-grant']['category'], 'localizzazione')

        # Un tipo senza categorie non ne inventa: il frontend lo disegna piatto.
        self.assertEqual(tipi['tradizione']['tagCategories'], [])
        self.assertIsNone(tipi['tradizione']['tags'][0]['category'])


class CategorieAggiunteAMano(TestCase):
    """Quello che fa l'admin dal pannello, senza passare dal seed."""

    def setUp(self):
        self.tipo = ArticleType.objects.create(
            key='prova', name='Prova', name_plural='Prove',
            active_fields=['title', 'tags'], required_fields=[])

    def test_una_categoria_nuova_raggruppa_i_suoi_tag(self):
        ArticleTypeTagCategory.objects.create(
            article_type=self.tipo, sort_order=0, key='durata', label='Durata')
        ArticleTypeTag.objects.create(
            article_type=self.tipo, sort_order=0, key='breve', label='Breve',
            category='durata')
        ArticleTypeTag.objects.create(
            article_type=self.tipo, sort_order=1, key='sciolto', label='Sciolto')

        self.tipo.full_clean()  # non deve lamentare niente
        risposta = APIClient().get('/api/cms/v1/article-types/')
        tipo = next(t for t in risposta.json()['articleTypes'] if t['key'] == 'prova')
        self.assertEqual(tipo['tagCategories'], [{'key': 'durata', 'label': 'Durata'}])
        per_chiave = {g['key']: g['category'] for g in tipo['tags']}
        self.assertEqual(per_chiave, {'breve': 'durata', 'sciolto': None})

    def test_cancellare_il_tipo_porta_via_le_categorie(self):
        ArticleTypeTagCategory.objects.create(
            article_type=self.tipo, sort_order=0, key='durata', label='Durata')
        self.tipo.delete()
        self.assertEqual(ArticleTypeTagCategory.objects.count(), 0)
