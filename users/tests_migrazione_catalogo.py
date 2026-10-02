"""La migrazione che gira una volta sola, provata prima di girare.

`users.0002` sposta due lingue da un JSONField alla tabella delle traduzioni, e
lo fa su dati che esistono gia': i profili dei soci puntano a quelle righe con
una many-to-many, quindi rinominarle e' l'unico modo di non perdere i
collegamenti. Rifarle da zero sarebbe piu' semplice e cancellerebbe le
competenze di tutti.

Si prova facendo marcia indietro e riavanzando: e' il solo modo di avere sotto
mano il mondo di prima, visto che dopo la migrazione il campo non esiste piu'.
"""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class MigrazioneCatalogoTest(TransactionTestCase):
    # Il nome della app e delle due migrazioni fra cui si va avanti e indietro.
    PRIMA = ('users', '0001_initial')
    DOPO = ('users', '0002_catalogo_tradotto')

    def _migra(self, bersaglio):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate([bersaglio])
        return executor

    def tearDown(self):
        # Il database di prova e' condiviso con gli altri test: va riportato
        # in avanti, altrimenti quelli che girano dopo trovano lo schema vecchio.
        self._migra(self.DOPO)

    def test_i_nomi_passano_in_italiano_e_l_inglese_resta_bloccato(self):
        self._migra(self.PRIMA)

        with connection.cursor() as cursore:
            cursore.execute(
                "INSERT INTO users_skill (name, translations) VALUES "
                "(%s, %s), (%s, %s), (%s, %s) RETURNING id",
                ['Project Management', '{"it": "Gestione Progetti"}',
                 'Six Sigma', '{"it": "Six Sigma"}',
                 'Senza Traduzione', '{}'])
            ids = [r[0] for r in cursore.fetchall()]
            cursore.execute(
                "INSERT INTO users_focusarea (name, translations) VALUES (%s, %s) "
                "RETURNING id",
                ['Valutazione e monitoraggio',
                 '{"it": "Valutazione e monitoraggio", "code": "A1"}'])
            area = cursore.fetchone()[0]
            # Un'area la cui sigla sta solo nel nome, come nei database piu' vecchi.
            cursore.execute(
                "INSERT INTO users_focusarea (name, translations) VALUES (%s, %s) "
                "RETURNING id",
                ['B2 Ricerca di Partners', '{}'])
            vecchia = cursore.fetchone()[0]

        self._migra(self.DOPO)

        from traduzione.models import Traduzione
        from users.models import FocusArea, Skill

        gestione, sigma, orfana = (Skill.objects.get(pk=i) for i in ids)
        self.assertEqual(gestione.name, 'Gestione Progetti')
        self.assertEqual(
            Traduzione.objects.get(object_id=str(gestione.pk),
                                   target_language='en').texts, {'name': 'Project Management'})
        self.assertEqual(
            Traduzione.objects.get(object_id=str(gestione.pk),
                                   target_language='en').locked_paths, ['name'])

        # Chi si dice uguale nelle due lingue non si rinomina, e non ha bisogno
        # di una riga: il nome e' gia' quello giusto in entrambe.
        self.assertEqual(sigma.name, 'Six Sigma')
        self.assertFalse(Traduzione.objects.filter(object_id=str(sigma.pk)).exists())

        # Chi non aveva una traduzione resta com'era, invece di diventare vuoto.
        self.assertEqual(orfana.name, 'Senza Traduzione')

        self.assertEqual(FocusArea.objects.get(pk=area).code, 'A1')
        # E la sigla si ripesca dal nome dove non era stata registrata.
        self.assertEqual(FocusArea.objects.get(pk=vecchia).code, 'B2')
