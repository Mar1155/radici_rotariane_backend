"""L'italiano che l'utente legge deve essere italiano scritto bene.

Nel codice scrivo i commenti in ASCII di proposito — `perche'`, `piu'`, `e'` —
perche' un commento lo legge chi lavora al progetto e l'ASCII non si rompe mai.
In una pagina pubblica la stessa abitudine e' un errore di ortografia, ed e'
arrivata in produzione due volte: nei titoli del Rota-Space e nei dati di prova
del forum, dove si leggeva "Soci under 40: perche entrano".

Questo test guarda le **stringhe** dei comandi che creano contenuto, non i
commenti: la distinzione e' esattamente il punto.
"""

import ast
import re
from pathlib import Path

from django.test import SimpleTestCase

RADICE = Path(__file__).resolve().parent.parent.parent

#: Parole che in italiano non esistono senza accento. Niente `meta` o `eta`, che
#: senza accento sono parole buone, e niente `e`, che e' anche congiunzione.
SENZA_ACCENTO = [
    'piu', 'puo', 'perche', 'cosi', 'gia', 'pero', 'cio', 'funzionalita',
    'attivita', 'citta', 'qualita', 'comunita', 'universita', 'identita',
    'novita', 'societa', 'verita', 'possibilita', 'opportunita', 'realta',
    'priorita', 'disponibilita',
]
ATTESO = re.compile(r"\b(" + "|".join(SENZA_ACCENTO) + r")'?\b", re.IGNORECASE)

#: Dove l'ASCII e' voluto: messaggi che si leggono in un terminale, dove un
#: accento puo' non arrivare a destinazione.
AMMESSI = {'translate_pending.py', 'build_site.py', 'check_s3.py'}


def stringhe(percorso: Path):
    """Ogni stringa del file, esclusi i docstring. Letta dall'albero sintattico
    e non con una regex, perche' un docstring e' una stringa come le altre e si
    distingue solo da dove sta."""
    albero = ast.parse(percorso.read_text(encoding='utf-8'))
    docstring = set()
    for nodo in ast.walk(albero):
        if isinstance(nodo, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            primo = nodo.body[0] if nodo.body else None
            if (isinstance(primo, ast.Expr) and isinstance(primo.value, ast.Constant)
                    and isinstance(primo.value.value, str)):
                docstring.add(id(primo.value))
    for nodo in ast.walk(albero):
        if (isinstance(nodo, ast.Constant) and isinstance(nodo.value, str)
                and id(nodo) not in docstring):
            yield nodo.lineno, nodo.value


#: I troncamenti veri, dove l'apostrofo non sostituisce un accento.
TRONCAMENTI = {"po'", "mo'", "de'", "be'", "ca'", "fa'", "da'", "di'", "va'", "sta'",
               "un'", "l'", "d'", "all'", "dell'", "nell'", "sull'", "quell'",
               "bell'", "sant'", "anch'", "dov'", "cos'", "qualcos'", "tutt'"}

#: Una parola che finisce con una vocale e un apostrofo ASCII e' un accento
#: scritto male: `sostenibilita'`, `perche'`, `piu'`. E' la regola generale che
#: l'elenco di parole qui sopra non copriva — l'ha dimostrato `sostenibilita'`,
#: arrivato in produzione proprio mentre correggevo gli altri.
APOSTROFO = re.compile(r"\b([A-Za-z]{2,}[aeiou]')(?=[\s,.;:!?\"]|$)")


class ItalianoScrittoBeneTest(SimpleTestCase):
    def test_i_comandi_che_creano_contenuto_scrivono_con_gli_accenti(self):
        problemi = []
        for percorso in sorted(RADICE.glob('*/management/commands/*.py')):
            if percorso.name in AMMESSI:
                continue
            for riga, testo in stringhe(percorso):
                if len(testo) < 8:
                    continue
                trovato = ATTESO.search(testo)
                if trovato:
                    problemi.append(
                        f'{percorso.relative_to(RADICE)}:{riga} '
                        f'"{trovato.group(0)}" in {testo[:60]!r}')
        self.assertEqual(problemi, [], 'Italiano senza accenti:\n' + '\n'.join(problemi))

    def test_nessun_apostrofo_al_posto_di_un_accento(self):
        """La stessa cosa detta come regola invece che come elenco.

        L'elenco di parole sopra ne lasciava fuori una per ogni parola che non
        avevo pensato: `sostenibilita'`, `legalita'`, `mobilita'` sono arrivate
        in produzione mentre correggevo `perche'` e `piu'`.
        """
        problemi = []
        for percorso in sorted(RADICE.glob('*/management/commands/*.py')):
            if percorso.name in AMMESSI:
                continue
            for riga, testo in stringhe(percorso):
                for trovato in APOSTROFO.finditer(testo):
                    if trovato.group(1).lower() in TRONCAMENTI:
                        continue
                    problemi.append(f'{percorso.relative_to(RADICE)}:{riga} '
                                    f'{trovato.group(1)!r} in {testo[:60]!r}')
        self.assertEqual(problemi, [],
                         "Apostrofo al posto di un accento:\n" + '\n'.join(problemi))
