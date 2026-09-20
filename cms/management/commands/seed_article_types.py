"""Crea i 12 tipi di articolo a partire dallo snapshot della vecchia config.

Non e' una migrazione dati: il database sara' azzerato. E' la traduzione della
**specifica** — cosa la vecchia configurazione sapeva esprimere — nel nuovo
modello. Se un tipo non riesce a rappresentare un tab, il modello ha un buco, ed
e' qui che si scopre.

Idempotente: si puo' rilanciare, aggiorna i tipi esistenti per chiave.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.models import Locale

from cms import vocabularies as vocab
from cms.models import ArticleType, ArticleTypeInfoElement, ArticleTypeTag, GeoArea
from section.legacy import legacy_config

# (sezione, tab) -> (chiave, nome singolare, nome plurale, descrizione)
# I nomi sono deliberatamente generici: il progetto e' passato dalla Calabria a
# tutta l'Italia, quindi "Eccellenza" e non "Eccellenza calabrese".
#
# ATTENZIONE alle chiavi a sinistra: non sono slug di pagina, sono le coppie
# (sezione, tab) con cui la vecchia configurazione e' registrata dentro
# `section/legacy/config_snapshot.json`, che e' congelato. Le pagine oggi si
# chiamano /eccellenze-italiane e /scopri-l-italia, ma qui si continua a
# cercare con i nomi di allora: rinominarle spezza il test di copertura.
NOMI = {
    ('adotta-un-progetto', 'main'): (
        'progetto', 'Progetto', 'Progetti',
        'Un progetto che cerca sostegno: importo, impatto e scadenza.'),
    ('storie-e-radici', 'storie'): (
        'storia', 'Storia', 'Storie',
        'Un racconto lungo, con copertina e corpo dell articolo.'),
    ('storie-e-radici', 'tradizioni'): (
        'tradizione', 'Tradizione', 'Tradizioni',
        'Usanze, feste, proverbi e leggende del territorio.'),
    ('storie-e-radici', 'testimonianze'): (
        'testimonianza', 'Testimonianza', 'Testimonianze',
        'Una voce diretta, senza titolo ne copertina: conta il testo.'),
    ('eccellenze-calabresi', 'main'): (
        'eccellenza', 'Eccellenza', 'Eccellenze',
        'Una realta di eccellenza segnalata dalla redazione. '
        'Non ha corpo dell articolo: la scheda e tutto.'),
    ('calendario-delle-radici', 'main'): (
        'evento', 'Evento', 'Eventi',
        'Un appuntamento con una data, mostrabile su calendario.'),
    ('scopri-la-calabria', 'itinerari'): (
        'itinerario', 'Itinerario', 'Itinerari',
        'Un percorso da fare, con la durata in giorni.'),
    ('scopri-la-calabria', 'esperienze'): (
        'esperienza', 'Esperienza', 'Esperienze',
        'Un attivita da vivere, con il prezzo.'),
    ('scopri-la-calabria', 'consigli'): (
        'consiglio', 'Consiglio', 'Consigli',
        'Una scheda che rimanda a un referente esterno. '
        'Nessuno pubblica articoli di questo tipo dall app.'),
    ('scambi-e-mobilita', 'offri'): (
        'scambio-offerta', 'Offerta di scambio', 'Offerte di scambio',
        'Chi mette a disposizione posti per uno scambio.'),
    ('scambi-e-mobilita', 'cerca'): (
        'scambio-richiesta', 'Richiesta di scambio', 'Richieste di scambio',
        'Chi cerca posti per uno scambio. Stessa struttura dell offerta, '
        'ma tipo distinto: e il tipo a dire in quale elenco sta un articolo.'),
    ('archivio', 'main'): (
        'documento-archivio', 'Documento d archivio', 'Documenti d archivio',
        'Materiale storico con galleria di allegati.'),
}


class Command(BaseCommand):
    help = 'Crea i tipi di articolo dallo snapshot della configurazione legacy.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Mostra cosa farebbe senza scrivere.')

    @transaction.atomic
    def handle(self, *args, **options):
        dry = options['dry_run']
        cfg = legacy_config()
        struttura = cfg['structureConfig']
        etichette_tag = cfg['tagTranslations']
        etichette_info = cfg['infoElementTranslations']
        locale = Locale.get_default()

        creati = aggiornati = 0
        for sezione, sdata in struttura.items():
            for tab, tdata in sdata['tabs'].items():
                chiave_nomi = NOMI.get((sezione, tab))
                if not chiave_nomi:
                    self.stderr.write(f'  ! nessun nome per {sezione}/{tab} — saltato')
                    continue
                key, nome, plurale, descrizione = chiave_nomi

                nascosti = set(tdata['fields'].get('hidden') or [])
                attivi = [f for f in vocab.FIELD_KEYS if f not in nascosti]
                obbligatori = [f for f in tdata['fields'].get('required') or []
                               if f in attivi]
                # `gallery` stava fra i required solo per renderla visibile: il
                # vecchio modello non sapeva dire "attivo ma facoltativo", e la
                # validazione la saltava con un commento che lo ammetteva. Ora
                # quello stato esiste, quindi la si modella per quello che e'.
                obbligatori = [f for f in obbligatori if f != 'gallery']

                ha_corpo = 'content' in attivi
                blocchi = vocab.BODY_BLOCK_KEYS if ha_corpo else []
                if 'gallery' not in attivi and 'gallery' in blocchi:
                    blocchi = [b for b in blocchi if b != 'gallery']

                valori = dict(
                    name=nome, name_plural=plurale, description=descrizione,
                    active_fields=attivi, required_fields=obbligatori,
                    buttons=list(tdata.get('buttons') or []),
                    can_publish=list(tdata.get('canAddArticle') or []),
                    body_blocks=blocchi,
                    default_columns=tdata.get('colonne') or 3,
                    new_article_label=(tdata.get('newArticleButtonLabel') or {}).get('it', ''),
                    uses_geo='location' in attivi,
                    external_url=tdata.get('externalUrl') or '',
                    external_email=tdata.get('externalEmail') or '',
                    external_phone=tdata.get('externalPhone') or '',
                )

                if dry:
                    self.stdout.write(
                        f'  {key:20} {nome:24} campi={len(attivi):2} '
                        f'obbl={len(obbligatori):2} info={len(tdata.get("infoElements") or [])} '
                        f'tag={len(tdata.get("tags") or [])} pubbl={valori["can_publish"] or "nessuno"}')
                    continue

                tipo, creato = ArticleType.objects.update_or_create(
                    key=key, locale=locale, defaults=valori)
                creati += creato
                aggiornati += (not creato)

                tipo.info_elements.all().delete()
                for i, ie in enumerate(tdata.get('infoElements') or []):
                    k = ie['title']
                    ArticleTypeInfoElement.objects.create(
                        article_type=tipo, sort_order=i, key=k, icon=ie['icon'],
                        label=etichette_info.get(k, {}).get('it', k.replace('_', ' ').title()),
                        locale=locale)

                # I tag che sono in realta' luoghi non diventano tag: li assorbe
                # la tassonomia geografica. Riconosciuti confrontandoli con
                # l'albero invece che con un elenco scritto a mano, cosi' la
                # regola resta vera anche per sezioni future.
                #
                # DIPENDENZA: serve che `seed_geo` sia gia' girato. Senza
                # l'albero, i luoghi restano tag e un tipo puo' finire con i
                # tag obbligatori e nessun tag da scegliere.
                chiavi_geo = set(
                    GeoArea.objects.filter(key__in=tdata.get('tags') or [])
                    .values_list('key', flat=True)
                )
                if chiavi_geo:
                    valori['uses_geo'] = True
                    tipo.uses_geo = True
                    tipo.save(update_fields=['uses_geo'])

                tipo.allowed_tags.all().delete()
                rimasti = [x for x in (tdata.get('tags') or []) if x not in chiavi_geo]
                for i, t in enumerate(rimasti):
                    ArticleTypeTag.objects.create(
                        article_type=tipo, sort_order=i, key=t,
                        label=etichette_tag.get(t, {}).get('it', t.replace('-', ' ').capitalize()),
                        locale=locale)

                # Se i tag erano TUTTI luoghi, il campo non esiste piu' per
                # questo tipo: il concetto e' passato alla geografia. Lasciarlo
                # fra gli obbligatori rendeva `itinerario` impossibile da
                # pubblicare — si chiedeva un tag e non ce n'era nessuno.
                if not rimasti:
                    tipo.active_fields = [f for f in tipo.active_fields if f != 'tags']
                    tipo.required_fields = [f for f in tipo.required_fields if f != 'tags']
                    tipo.save(update_fields=['active_fields', 'required_fields'])

        if dry:
            self.stdout.write(self.style.WARNING('\ndry-run: niente scritto.'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'\n{creati} tipi creati, {aggiornati} aggiornati.'))
