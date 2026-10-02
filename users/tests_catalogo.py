"""I cataloghi del profilo in sei lingue, in lettura e in scrittura.

Competenze, competenze trasversali e aree d'intervento erano l'ultimo pezzo
monolingua dell'app, e non per dimenticanza: erano l'unico posto in cui
**l'identita' di una riga era il suo nome**. Finche' il profilo rimandava
indietro i nomi che aveva ricevuto, mostrarli tradotti rompeva il salvataggio —
il server cercava "Project Management" e in tabella c'era "Gestione Progetti".

Il giro di `test_rileggere_e_rimandare_indietro_in_inglese_non_perde_niente` e'
esattamente quello che fa una persona, ed e' l'unico test che qui serviva
davvero: gli altri verificano i pezzi, quello verifica che le due meta' si
parlino.
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from traduzione import lingue
from traduzione.models import Lingua
from traduzione.umane import fissa
from users.models import FocusArea, Skill, SoftSkill, User


class CatalogoTradottoTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        Lingua.objects.all().delete()
        lingue.svuota_cache()
        Lingua.objects.create(codice='it', nome='Italiano', ordine=0)
        Lingua.objects.create(codice='en', nome='English', ordine=1)

        cls.gestione = Skill.objects.create(name='Gestione Progetti')
        fissa(cls.gestione, 'en', {'name': 'Project Management'})
        cls.sigma = Skill.objects.create(name='Six Sigma')
        fissa(cls.sigma, 'en', {'name': 'Six Sigma'})
        cls.empatia = SoftSkill.objects.create(name='Empatia')
        fissa(cls.empatia, 'en', {'name': 'Empathy'})

        cls.macro = FocusArea.objects.create(name='Gestione di Progetti', code='A')
        fissa(cls.macro, 'en', {'name': 'Project Management'})
        cls.voce = FocusArea.objects.create(name='Valutazione e monitoraggio', code='A1')
        cls.altra_macro = FocusArea.objects.create(name='Rotary Grants', code='B')

        cls.socio = User.objects.create_user(
            username='socio', email='socio@example.com', password='x',
            first_name='Anna', last_name='Rossi', profession='Ingegnere')
        cls.socio.skills.add(cls.gestione)
        cls.socio.focus_areas.add(cls.voce)

    def setUp(self):
        self.client = APIClient()

    def inglese(self, url, **extra):
        return self.client.get(url, HTTP_ACCEPT_LANGUAGE='en-GB,en;q=0.9', **extra)

    # --- lettura -----------------------------------------------------------

    def test_il_catalogo_arriva_nella_lingua_del_lettore(self):
        voci = {v['id']: v['name'] for v in self.inglese(reverse('skills-list')).json()}
        self.assertEqual(voci[self.gestione.pk], 'Project Management')
        # E quello che in inglese si dice uguale resta uguale: e' il motivo per
        # cui i nomi inglesi dei seed sono bloccati.
        self.assertEqual(voci[self.sigma.pk], 'Six Sigma')

    def test_in_italiano_il_catalogo_e_quello_scritto_in_tabella(self):
        voci = {v['id']: v['name'] for v in
                self.client.get(reverse('skills-list')).json()}
        self.assertEqual(voci[self.gestione.pk], 'Gestione Progetti')

    def test_le_competenze_di_un_profilo_sono_tradotte(self):
        self.client.force_authenticate(user=self.socio)
        dati = self.inglese(reverse('me')).json()
        self.assertEqual([s['name'] for s in dati['skills']], ['Project Management'])
        # L'id viaggia accanto all'etichetta: e' cio' che rende possibile
        # rimandarla indietro.
        self.assertEqual([s['id'] for s in dati['skills']], [self.gestione.pk])

    def test_un_area_senza_traduzione_resta_nella_lingua_in_cui_e_scritta(self):
        """Non spariscono e non diventano vuote: si leggono in italiano.

        E' la regola di tutto il progetto — una pagina in italiano dentro una
        cornice inglese e' meglio di un buco — e qui capita per davvero: le
        aree d'intervento le traduce il motore, quindi fra il seed e il primo
        ripasso non hanno traduzione.
        """
        voci = {v['id']: v['name'] for v in self.inglese(reverse('focus-areas-list')).json()}
        self.assertEqual(voci[self.voce.pk], 'Valutazione e monitoraggio')

    # --- scrittura ---------------------------------------------------------

    def test_si_scrive_per_id(self):
        self.client.force_authenticate(user=self.socio)
        risposta = self.client.patch(reverse('me'),
                                     {'skills': [self.sigma.pk, self.gestione.pk]},
                                     format='json')
        self.assertEqual(risposta.status_code, 200, risposta.data)
        self.assertEqual(set(self.socio.skills.values_list('pk', flat=True)),
                         {self.sigma.pk, self.gestione.pk})

    def test_rileggere_e_rimandare_indietro_in_inglese_non_perde_niente(self):
        """Il giro che prima si rompeva, fatto come lo fa una persona.

        Apri il profilo con l'app in inglese, aggiungi una competenza, salvi.
        Prima il profilo rimandava indietro le etichette che aveva letto —
        "Project Management" — e il server cercava una riga con quel nome: non
        la trovava, e la competenza spariva dal profilo senza un errore.
        """
        self.client.force_authenticate(user=self.socio)
        letto = self.inglese(reverse('me')).json()

        ids = [s['id'] for s in letto['skills']] + [self.sigma.pk]
        risposta = self.client.patch(reverse('me'), {'skills': ids}, format='json')
        self.assertEqual(risposta.status_code, 200, risposta.data)

        self.assertEqual(
            sorted(s['name'] for s in self.inglese(reverse('me')).json()['skills']),
            ['Project Management', 'Six Sigma'])
        # E in italiano e' lo stesso profilo, non un altro.
        self.assertEqual(
            sorted(s['name'] for s in self.client.get(reverse('me')).json()['skills']),
            ['Gestione Progetti', 'Six Sigma'])

    def test_si_scrive_anche_quando_gli_id_arrivano_come_testo(self):
        """Il profilo si salva con un `multipart`, per via dell'avatar.

        In un `multipart` tutto e' testo: gli id arrivano dentro una stringa
        JSON, ed e' il percorso che il browser usa davvero — non quello JSON
        del test qui sopra.
        """
        import json

        self.client.force_authenticate(user=self.socio)
        risposta = self.client.patch(
            reverse('me'),
            {'skills': json.dumps([self.sigma.pk]),
             'focus_areas': json.dumps([self.macro.pk])},
            format='multipart')
        self.assertEqual(risposta.status_code, 200, risposta.data)
        self.assertEqual(list(self.socio.skills.values_list('pk', flat=True)),
                         [self.sigma.pk])
        self.assertEqual(list(self.socio.focus_areas.values_list('pk', flat=True)),
                         [self.macro.pk])

    # --- i filtri di /skills ----------------------------------------------

    def test_i_filtri_si_vedono_anche_senza_accesso(self):
        """Il guasto segnalato: le macro aree erano vuote da anonimo.

        Non per mancanza di dati — la risposta era 401 intera, e il frontend
        riempiva le tendine con niente.
        """
        risposta = self.client.get(reverse('skills-filter-options'))
        self.assertEqual(risposta.status_code, 200)
        sigle = [a['code'] for a in risposta.json()['macro_focus_areas']]
        self.assertEqual(sigle, ['A', 'B'])

    def test_i_filtri_sono_tradotti(self):
        nomi = {a['code']: a['name'] for a in
                self.inglese(reverse('skills-filter-options')).json()['macro_focus_areas']}
        self.assertEqual(nomi['A'], 'Project Management')

    def test_l_elenco_dei_soci_resta_dietro_l_accesso(self):
        """I cataloghi sono pubblici, le persone no."""
        self.assertEqual(self.client.get(reverse('skills-search')).status_code, 401)

    def test_le_voci_di_una_macro_area_si_scelgono_per_sigla(self):
        risposta = self.client.get(reverse('skills-filter-options'),
                                   {'macro_focus_area_id': self.macro.pk})
        self.assertEqual([a['code'] for a in risposta.json()['focus_areas']], ['A1'])

    def test_le_sigle_si_ordinano_per_numero_non_per_lettera(self):
        """A1, A2, A10 — non A1, A10, A2, che e' l'ordine alfabetico.

        E non per nome: i nomi arrivano tradotti, quindi in sei lingue
        darebbero sei ordini diversi per le stesse voci.
        """
        for n in (10, 2):
            FocusArea.objects.create(name=f'Voce {n}', code=f'A{n}')
        risposta = self.client.get(reverse('skills-filter-options'),
                                   {'macro_focus_area_id': self.macro.pk})
        self.assertEqual([a['code'] for a in risposta.json()['focus_areas']],
                         ['A1', 'A2', 'A10'])

    # --- costo -------------------------------------------------------------

    def test_un_elenco_di_soci_non_fa_una_query_per_etichetta(self):
        """Trenta soci con tre competenze sono novanta etichette da tradurre.

        Senza il prefetch sono novanta query in piu', e la pagina /skills e'
        esattamente il posto dove si vede.
        """
        competenze = [Skill.objects.create(name=f'Competenza {i}') for i in range(3)]
        for c in competenze:
            fissa(c, 'en', {'name': f'Skill {c.pk}'})
        for i in range(30):
            altro = User.objects.create_user(username=f'u{i}', email=f'u{i}@e.com',
                                             password='x', profession='Ingegnere')
            altro.skills.set(competenze)
            altro.focus_areas.add(self.voce)

        self.client.force_authenticate(user=self.socio)
        with self.assertNumQueries(6):
            risposta = self.inglese(reverse('skills-search'))
        self.assertEqual(risposta.status_code, 200)
        corpo = risposta.json()
        righe = corpo['results'] if isinstance(corpo, dict) else corpo
        self.assertEqual(len(righe), 30)
        self.assertTrue(all(s['name'].startswith('Skill ')
                            for r in righe for s in r['skills']),
                        'le etichette non sono arrivate tradotte')


class GlossarioTest(TestCase):
    def test_i_nomi_delle_sezioni_non_si_traducono(self):
        """Un filo teso, non una prova: il modello li rispetta o no, e si vede
        solo guardando il sito.

        Ma la regola nel glossario e' l'unica cosa che glielo dice, e sparisce
        con una riscrittura distratta. "SKILLS" era il nome della sezione, ed
        era arrivato tradotto come se fosse la parola comune.
        """
        from traduzione.glossario import REGOLE
        for nome in ('SKILLS', 'Rota-Space', 'Radici Rotariane'):
            self.assertIn(nome, REGOLE, f'{nome} non e piu nel glossario')


class SeedCatalogoTest(TestCase):
    """I tre comandi che riempiono i cataloghi, provati per davvero.

    Sono la rete di sicurezza della migrazione: se quella non riuscisse a
    rinominare qualcosa, rilanciare il seed lo sistema. Vale la pena sapere che
    la rete tiene.
    """

    def test_il_catalogo_e_in_italiano_con_l_inglese_a_lato(self):
        from django.core.management import call_command
        call_command('seed_skills', verbosity=0)

        gestione = Skill.objects.get(name='Gestione Progetti')
        self.assertEqual(
            gestione.traduzioni.get(target_language='en').texts['name'],
            'Project Management')
        # Bloccata: `translate_pending --forza` non la riscrive.
        self.assertEqual(gestione.traduzioni.get(target_language='en').locked_paths,
                         ['name'])
        self.assertEqual(SoftSkill.objects.get(name='Empatia').traduzioni
                         .get(target_language='en').texts['name'], 'Empathy')
        # Nessun nome inglese e' rimasto in tabella al posto dell'italiano.
        self.assertFalse(Skill.objects.filter(name='Project Management').exists())

    def test_il_ripasso_degli_arretrati_non_tocca_i_nomi_scritti_a_mano(self):
        """Il ripasso gira a ogni avvio del server e passa su tutto.

        Su una riga umana non ha niente da chiedere al motore — i percorsi sono
        bloccati — ma senza l'impronta ci tornava sopra ogni volta e le
        riscriveva `provider`: la riga diceva "anthropic" su un testo scritto
        da una persona.
        """
        from django.core.management import call_command

        from traduzione.arretrati import traduci_arretrati
        from traduzione.tests import MotoreFinto

        Lingua.objects.get_or_create(codice='en', defaults={'nome': 'English'})
        lingue.svuota_cache()
        call_command('seed_skills', verbosity=0)
        gestione = Skill.objects.get(name='Gestione Progetti')

        traduci_arretrati(MotoreFinto(), lingua='en', da_fare=[Skill])

        riga = gestione.traduzioni.get(target_language='en')
        self.assertEqual(riga.texts['name'], 'Project Management',
                         'il motore ha riscritto un nome scritto a mano')
        self.assertEqual(riga.provider, 'umano')

    def test_rilanciare_i_seed_non_duplica_niente(self):
        from django.core.management import call_command
        call_command('seed_skills', verbosity=0)
        call_command('seed_focus_areas', verbosity=0)
        quante = (Skill.objects.count(), SoftSkill.objects.count(),
                  FocusArea.objects.count())
        call_command('seed_skills', verbosity=0)
        call_command('seed_softskills', verbosity=0)
        call_command('seed_focus_areas', verbosity=0)
        self.assertEqual((Skill.objects.count(), SoftSkill.objects.count(),
                          FocusArea.objects.count()), quante)

    def test_ogni_area_ha_la_sua_sigla(self):
        """Senza sigla un'area non compare in nessuna tendina: ne' fra le macro
        aree ne' fra le voci di una macro area."""
        from django.core.management import call_command
        call_command('seed_focus_areas', verbosity=0)
        senza = list(FocusArea.objects.filter(code='').values_list('name', flat=True))
        self.assertEqual(senza, [])
        self.assertEqual(FocusArea.objects.filter(code='A').first().macro_code, 'A')
        self.assertTrue(FocusArea.objects.get(code='A').is_macro)
        self.assertFalse(FocusArea.objects.get(code='A1').is_macro)
