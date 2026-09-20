"""Costruisce nel CMS le 7 pagine che prima erano le sezioni "Scopri".

Erano un unico file da 775 righe che si configurava da `app/scopri/config/`:
sette pagine diverse ottenute per parametri, con hero, spiegazione, tab,
calendario e filtri decisi da codice. Qui diventano sette normali pagine di
blocchi, che il cliente puo' rinominare, riordinare e riscrivere da solo.

Gli indirizzi sono di primo livello (`/storie-e-radici`), non piu' annidati
sotto `/scopri`.

Idempotente: rilanciarlo riscrive il corpo delle pagine senza duplicarle.
"""

import copy

from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.models import Locale

from cms.bootstrap import assicura_homepage
from cms.models import ArticleType, StandardPage


def elenco(tipo, **extra):
    """Un blocco `article_list`, con i valori di base gia' impostati."""
    valori = {
        'heading': '', 'article_type': tipo, 'accent': 'brand-primary',
        'layout': 'grid', 'columns': '3', 'limit': None,
        'show_search': True, 'show_tag_filter': True, 'show_geo_filter': True,
    }
    valori.update(extra)
    return ('article_list', valori)


def tab(etichetta, tipo, colonne='3', layout='grid'):
    return {'label': etichetta, 'article_type': tipo,
            'layout': layout, 'columns': colonne}


SEZIONI = [
    {
        'slug': 'adotta-un-progetto',
        'title': 'Adotta un Progetto',
        'accent': 'emerald',
        'tag': 'fiera digitale',
        'description': 'La vetrina digitale dove i Club possono condividere progetti '
                       'da finanziare o sostenere operativamente.',
        'spiegazione': {
            'title': 'Come funziona',
            'description': 'Scopri e sostieni i progetti degli utenti di Radici Rotariane '
                           'nel mondo. Contribuisci anche tu a fare la differenza',
            'steps': [
                ('Compass', 'Esplora', 'Scopri i progetti che chiedono il tuo aiuto'),
                ('Target', 'Scegli', 'Seleziona il progetto che più ti sta a cuore'),
                ('Heart', 'Sostieni', 'Contribuisci con una donazione o supporto operativo'),
                ('Bookmark', 'Salva', 'Salva il progetto nel tuo profilo per mostrare il tuo interesse'),
            ],
        },
        'corpo': [elenco('progetto', columns='2')],
    },
    {
        'slug': 'storie-e-radici',
        'title': 'Storie e Radici',
        'accent': 'sky',
        'tag': 'Identità e Memoria',
        'description': "L'archivio multimediale dedicato alle culture dei territori "
                       'italiani: racconti autentici che intrecciano memoria, identità '
                       'e appartenenza.',
        'spiegazione': {
            'title': 'Condividi la tua storia',
            'description': 'Condividi foto, video e documenti relativi ad esperienze personali, '
                           'viaggi alle origini, storie di rotariani nel mondo e tradizioni locali.',
            'steps': [
                ('Globe', 'Foto e Video', 'Condividi foto e video di esperienze autentiche'),
                ('Flag', 'Racconti', 'Racconta storie di rotariani di successo nel mondo'),
                ('Award', 'Tradizioni', 'Condividi aneddoti, ricette, tradizioni del tuo territorio'),
            ],
        },
        'corpo': [('tabbed_article_list', {
            'heading': '', 'accent': 'sky',
            'show_search': True, 'show_tag_filter': True, 'show_geo_filter': True,
            'tabs': [
                tab('Storie', 'storia', '2'),
                tab('Tradizioni', 'tradizione', '2'),
                tab('Testimonianze', 'testimonianza', '1'),
            ],
        })],
    },
    {
        'slug': 'eccellenze-italiane',
        'slug_precedenti': ['eccellenze-calabresi'],
        'title': 'Eccellenze Italiane',
        'accent': 'teal',
        'tag': 'Convenzioni e sconti',
        'description': 'Scopri le migliori attività italiane a prezzi agevolati: ristoranti, '
                       'hotel, aziende e professionisti di qualità, con sconti dedicati ai '
                       'Rotariani in visita.',
        'spiegazione': {
            'title': 'Vuoi aderire?',
            'description': "Hai un'attività o conosci un'attività che vorrebbe aderire al "
                           'progetto offrendo sconti esclusivi ai rotariani di passaggio? '
                           'Contattaci',
            'steps': [],
            'contact_email': 'info@rotary2102.org',
        },
        'corpo': [elenco('eccellenza', columns='2')],
    },
    {
        'slug': 'calendario-delle-radici',
        'title': 'Calendario ed Eventi',
        'accent': 'amber',
        'tag': 'eventi',
        'description': 'Lo spazio dove puoi tenerti aggiornato e promuovere gli incontri '
                       'rotariani di Club, Distrettuali ed internazionali (meeting, '
                       'conferenze, service).',
        'spiegazione': None,
        'corpo': [elenco('evento', layout='calendar', columns='1', accent='amber')],
    },
    {
        'slug': 'scopri-l-italia',
        'slug_precedenti': ['scopri-la-calabria'],
        'title': "Scopri l'Italia",
        'accent': 'rose',
        'tag': 'Turismo delle Radici',
        'description': 'La guida alla scoperta dei territori italiani: coste e isole, '
                       'montagne e borghi, storia millenaria e sapori che cambiano '
                       'a ogni provincia.',
        'spiegazione': None,
        'corpo': [('tabbed_article_list', {
            'heading': '', 'accent': 'rose',
            'show_search': True, 'show_tag_filter': True, 'show_geo_filter': True,
            'tabs': [
                tab('Itinerari', 'itinerario', '2'),
                tab('Esperienze', 'esperienza', '3'),
                tab('Consigli', 'consiglio', '1'),
            ],
        })],
    },
    {
        'slug': 'scambi-e-mobilita',
        'title': 'Scambi e Mobilità',
        'accent': 'stone',
        'tag': "Scambio d'Amicizia Rotariana",
        'description': 'La rete di ospitalità rotariana: una bacheca dove offrire o ricercare '
                       "ospitalità, favorendo incontri, soggiorni, e visite tra Club nel segno "
                       "dello Scambio d'amicizia Rotariana",
        'spiegazione': None,
        'corpo': [('tabbed_article_list', {
            'heading': '', 'accent': 'stone',
            'show_search': True, 'show_tag_filter': True, 'show_geo_filter': True,
            'tabs': [
                tab('Offri', 'scambio-offerta', '3'),
                tab('Cerca', 'scambio-richiesta', '3'),
            ],
        })],
    },
    {
        'slug': 'archivio',
        'title': 'Archivio',
        'accent': 'slate',
        'tag': 'Database Rotariano',
        'description': 'Un tuffo nel passato: documenti, testimonianze e immagini di eventi, '
                       "scambi d'amicizia, gemellaggi e progetti già conclusi, per conservare "
                       'e condividere i ricordi dei momenti più significativi.',
        'spiegazione': None,
        'corpo': [elenco('documento-archivio', accent='slate')],
    },
]


class Command(BaseCommand):
    help = 'Crea (o aggiorna) le 7 pagine sezione.'

    @transaction.atomic
    def handle(self, *args, **options):
        locale = Locale.get_default()
        home = assicura_homepage()

        # Il blocco riferisce l'istanza, non la chiave: la chiave la espone poi
        # l'API. Qui si risolve una volta sola.
        tipi = {t.key: t for t in ArticleType.objects.filter(locale=locale)}

        for s in SEZIONI:
            corpo = [('hero', {
                'title': s['title'], 'description': s['description'], 'tag': s['tag'],
                'surface': 'section', 'accent': s['accent'],
                'scroll_to_id': 'contenuto',
            })]

            sp = s['spiegazione']
            if sp:
                corpo.append(('explanation_steps', {
                    'title': sp['title'], 'description': sp['description'],
                    'accent': s['accent'],
                    'contact_email': sp.get('contact_email', ''),
                    'steps': [{'icon': i, 'title': t, 'description': d}
                              for i, t, d in sp['steps']],
                }))

            # Si lavora su una copia: risolvere i tipi sostituisce la chiave
            # con l'istanza, e mutare SEZIONI romperebbe la seconda esecuzione
            # nello stesso processo.
            #
            # L'accento dell'elenco segue quello della sezione, a meno che il
            # blocco non lo dichiari gia'.
            for nome, valori in copy.deepcopy(s['corpo']):
                if nome == 'article_list':
                    if valori['accent'] == 'brand-primary':
                        valori['accent'] = s['accent']
                    valori['article_type'] = self._tipo(valori['article_type'], tipi, s['slug'])
                else:
                    for t in valori['tabs']:
                        t['article_type'] = self._tipo(t['article_type'], tipi, s['slug'])
                corpo.append((nome, valori))

            pagina = StandardPage.objects.filter(slug=s['slug'], locale=locale).first()
            if pagina is None:
                # Se la sezione e' stata rinominata, la pagina c'e' gia' con il
                # nome di prima: va rinominata, non duplicata. Senza questo un
                # database esistente si ritroverebbe la pagina nuova accanto
                # alla vecchia, pubblicata, con i testi di allora.
                pagina = self._con_nome_precedente(s, locale)
                if pagina is not None:
                    self.stdout.write(f'  /{pagina.slug} rinominata in /{s["slug"]}')
                    pagina.slug = s['slug']
            if pagina is None:
                pagina = StandardPage(title=s['title'], slug=s['slug'], locale=locale)
                home.add_child(instance=pagina)
            pagina.title = s['title']
            pagina.body = corpo
            pagina.save()
            pagina.save_revision().publish()
            self.stdout.write(f'  /{s["slug"]:26} {len(corpo)} blocchi')

        self.stdout.write(self.style.SUCCESS(f'{len(SEZIONI)} pagine sezione pubblicate.'))

    def _con_nome_precedente(self, s, locale):
        for precedente in s.get('slug_precedenti', ()):
            pagina = StandardPage.objects.filter(slug=precedente, locale=locale).first()
            if pagina is not None:
                return pagina
        return None

    def _tipo(self, chiave, tipi, slug):
        if chiave not in tipi:
            raise ValueError(
                f'La pagina /{slug} rimanda al tipo di articolo "{chiave}", '
                f'che non esiste. Esegui prima `seed_article_types`.')
        return tipi[chiave]
