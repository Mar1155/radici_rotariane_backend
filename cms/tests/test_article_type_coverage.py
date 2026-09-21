"""Il tipo di articolo copre tutto cio' che la vecchia configurazione esprimeva?

Non e' un test di migrazione dati — il database sara' azzerato. E' un test di
**copertura della specifica**: per ogni tab della configurazione congelata deve
esistere un tipo di articolo che ne riproduce struttura e comportamento.

Un tab che non si riesce a rappresentare e' un buco nel modello, e va scoperto
qui invece che a meta' della fase successiva.
"""

from django.core.exceptions import ValidationError
from django.test import TestCase
from wagtail.models import Locale

from cms import vocabularies as vocab
from cms.models import ArticleType
from cms.management.commands.seed_article_types import NOMI
from section.legacy import legacy_config


class ArticleTypeCoverageTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        from django.core.management import call_command
        call_command('seed_geo', verbosity=0)
        call_command('seed_article_types', verbosity=0)
        cls.cfg = legacy_config()

    def _tipo(self, sezione, tab):
        return ArticleType.objects.get(key=NOMI[(sezione, tab)][0])

    def _tab(self, sezione, tab):
        return self.cfg['structureConfig'][sezione]['tabs'][tab]

    def test_esiste_un_tipo_per_ogni_tab(self):
        attesi = sum(len(s['tabs']) for s in self.cfg['structureConfig'].values())
        self.assertEqual(attesi, 12)
        self.assertEqual(ArticleType.objects.count(), attesi)

    def test_campi_attivi_e_obbligatori(self):
        for (sezione, tab) in NOMI:
            with self.subTest(f'{sezione}/{tab}'):
                t, cfg = self._tipo(sezione, tab), self._tab(sezione, tab)
                nascosti = set(cfg['fields'].get('hidden') or [])
                attesi = [f for f in vocab.FIELD_KEYS if f not in nascosti]
                # Se i tag di quel tab erano TUTTI luoghi, il concetto e'
                # passato alla tassonomia geografica e il campo non esiste piu'
                # per questo tipo. Tenerlo obbligatorio rendeva `itinerario`
                # impossibile da pubblicare: si chiedeva un tag e non ce n'era
                # nessuno da scegliere.
                if not t.allowed_tags.exists() and (cfg.get('tags') or []):
                    attesi = [f for f in attesi if f != 'tags']
                self.assertEqual(sorted(t.active_fields), sorted(attesi))
                # nessun campo nascosto e' rimasto attivo
                self.assertFalse(set(t.active_fields) & nascosti)
                # gli obbligatori della vecchia config restano obbligatori,
                # tranne `gallery`: la' era fra i required solo per renderla
                # visibile, e la validazione la saltava esplicitamente.
                for f in cfg['fields'].get('required') or []:
                    if f == 'gallery':
                        self.assertTrue(t.field_is_active(f))
                        self.assertFalse(t.field_is_required(f))
                    elif f == 'tags' and not t.allowed_tags.exists():
                        # Vedi sopra: i tag erano luoghi, e sono diventati geografia.
                        self.assertFalse(t.field_is_active(f))
                        self.assertTrue(t.uses_geo)
                    else:
                        self.assertTrue(t.field_is_required(f))

    def test_obbligatorio_implica_attivo(self):
        """Il vincolo che rende impossibile ricreare il vecchio bug."""
        for t in ArticleType.objects.all():
            with self.subTest(t.key):
                self.assertTrue(set(t.required_fields) <= set(t.active_fields))

    def test_elementi_informativi_con_chiave_stabile(self):
        for (sezione, tab) in NOMI:
            with self.subTest(f'{sezione}/{tab}'):
                t, cfg = self._tipo(sezione, tab), self._tab(sezione, tab)
                attesi = cfg.get('infoElements') or []
                effettivi = list(t.info_elements.all())
                self.assertEqual(len(effettivi), len(attesi))
                for atteso, effettivo in zip(attesi, effettivi):
                    self.assertEqual(effettivo.key, atteso['title'])
                    self.assertEqual(effettivo.icon, atteso['icon'])
                    self.assertTrue(effettivo.label)

    def test_tag_bottoni_colonne_e_permessi(self):
        for (sezione, tab) in NOMI:
            with self.subTest(f'{sezione}/{tab}'):
                t, cfg = self._tipo(sezione, tab), self._tab(sezione, tab)
                # I tag geografici sono passati alla tassonomia: restano nel
                # tipo solo quelli tematici.
                from cms.models import GeoArea
                attesi = cfg.get('tags') or []
                geo = set(GeoArea.objects.filter(key__in=attesi)
                          .values_list('key', flat=True))
                self.assertEqual(
                    sorted(x.key for x in t.allowed_tags.all()),
                    sorted(x for x in attesi if x not in geo))
                if geo:
                    self.assertTrue(t.uses_geo,
                                    'un tipo che aveva tag geografici deve usare la geografia')
                self.assertEqual(sorted(t.buttons), sorted(cfg.get('buttons') or []))
                self.assertEqual(t.default_columns, cfg.get('colonne') or 3)
                self.assertEqual(sorted(t.can_publish),
                                 sorted(cfg.get('canAddArticle') or []))

    def test_contatti_esterni(self):
        t = self._tipo('scopri-la-calabria', 'consigli')
        cfg = self._tab('scopri-la-calabria', 'consigli')
        self.assertEqual(t.external_url, cfg['externalUrl'])
        self.assertEqual(t.external_email, cfg['externalEmail'])
        self.assertEqual(t.external_phone, cfg['externalPhone'])
        self.assertEqual(t.can_publish, [], 'nessuno deve poter pubblicare consigli')

    def test_tipi_identici_restano_distinti(self):
        """offri e cerca sono strutturalmente identici ma devono restare due tipi.

        Se condividessero un tipo non si distinguerebbero piu' i loro articoli:
        e' il tipo a dire in quale elenco sta un articolo.
        """
        a = ArticleType.objects.get(key='scambio-offerta')
        b = ArticleType.objects.get(key='scambio-richiesta')
        self.assertEqual(sorted(a.active_fields), sorted(b.active_fields))
        self.assertNotEqual(a.pk, b.pk)
        self.assertNotEqual(a.name, b.name)

    def test_vocabolari_coprono_la_config(self):
        """Nessun valore della vecchia config resta fuori dai vocabolari."""
        campi, bottoni, ruoli, icone = set(), set(), set(), set()
        for s in self.cfg['structureConfig'].values():
            for cfg in s['tabs'].values():
                campi |= set(cfg['fields']['required']) | set(cfg['fields']['hidden'])
                bottoni |= set(cfg.get('buttons') or [])
                ruoli |= set(cfg.get('canAddArticle') or [])
                icone |= {ie['icon'] for ie in cfg.get('infoElements') or []}
        self.assertFalse(campi - set(vocab.FIELD_KEYS))
        self.assertFalse(bottoni - set(vocab.BUTTON_KEYS))
        self.assertFalse(ruoli - set(vocab.ROLE_KEYS))
        self.assertFalse(icone - set(vocab.ICON_KEYS))

    def test_obbligatorio_non_attivo_e_rifiutato(self):
        t = ArticleType(key='prova', name='Prova', name_plural='Prove',
                        active_fields=['title'], required_fields=['title', 'subtitle'])
        with self.assertRaises(ValidationError) as ctx:
            t.full_clean()
        self.assertIn('required_fields', ctx.exception.message_dict)
