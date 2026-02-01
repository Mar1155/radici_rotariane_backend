"""
Comprehensive Card Seeding Script

Creates 3-4 cards for each tab in each section with coherent, realistic data.
Respects the structure configuration and generates appropriate info element values.
"""

import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from section.models import Card
from section.structure import get_all_sections, get_tab_keys_for_section, get_tags_for_tab, get_info_elements_config
from users.models import User


class RichContentGenerator:
    """Generate rich HTML content with various formatting features"""
    
    @staticmethod
    def generate_content(title, content_text, include_list=False, include_link=True):
        """
        Generate rich HTML content with formatting.
        
        Args:
            title: Main heading for the content
            content_text: Body text for paragraphs
            include_list: Whether to include an ordered list
            include_link: Whether to include a link
        """
        html_parts = [
            f'<h1>{title}</h1>',
            '<h2>Dettagli Importanti</h2>',
            f'<p>{content_text}</p>',
            '<p><strong>Punto principale:</strong> Leggi attentamente le informazioni.</p>',
            '<p><em>Questo è un elemento importante</em></p>',
            '<p><u>Sottolineato per enfasi</u></p>',
            f'<p><span style="color: rgb(230, 0, 0);">Informazione critica</span></p>',
            '<p>Questo è <span style="background-color: rgb(255, 255, 0);">evidenziato</span> per importanza</p>',
        ]
        
        if include_list:
            html_parts.append(
                '<ol>'
                '<li data-list="ordered"><span class="ql-ui" contenteditable="false"></span>Prima considerazione</li>'
                '<li data-list="ordered"><span class="ql-ui" contenteditable="false"></span>Seconda considerazione</li>'
                '</ol>'
            )
        
        html_parts.append('<p class="ql-align-center">Informazioni Aggiuntive</p>')
        html_parts.append('<p class="ql-align-center"><br></p>')
        
        if include_link:
            html_parts.append(
                '<p><a href="https://www.rotary.org" rel="noopener noreferrer" target="_blank">'
                'Per saperne di più visita il sito ufficiale</a></p>'
            )
        
        return ''.join(html_parts)


class Command(BaseCommand):
    help = "Seed comprehensive card data for all sections and tabs."
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.image_counter = random.randint(1, 10000)

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing cards before seeding.",
        )

    def _get_random_image_url(self):
        """Generate a random image URL using picsum.photos"""
        self.image_counter += random.randint(1, 100)
        return f"https://picsum.photos/300/200?random={self.image_counter}"

    def _generate_rich_content(self, title, content_text, include_list=False, include_link=True):
        """Generate rich HTML content with formatting"""
        generator = RichContentGenerator()
        return generator.generate_content(title, content_text, include_list, include_link)

    def handle(self, *args, **options):
        if options["reset"]:
            Card.objects.all().delete()
            self.stdout.write(self.style.WARNING("All existing cards deleted."))

        # Get all available authors
        authors = list(User.objects.filter(user_type='NORMAL').all()[:30])
        if not authors:
            self.stdout.write(self.style.ERROR("No users found. Please seed users first with: python manage.py seed_demo"))
            return

        sections = get_all_sections()
        cards_created = 0

        for section in sections:
            tabs = get_tab_keys_for_section(section)
            self.stdout.write(self.style.SUCCESS(f"\n📚 Section: {section}"))
            
            for tab in tabs:
                cards_data = self._get_cards_for_tab(section, tab)
                
                for card_data in cards_data:
                    card_data['author'] = random.choice(authors)
                    card_data['section'] = section
                    card_data['tab'] = tab
                    
                    try:
                        card = Card.objects.create(**card_data)
                        cards_created += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"  ✓ {tab}: {card.title}")
                        )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"  ✗ {tab}: {card_data.get('title', 'Unknown')} - {str(e)}")
                        )

        self.stdout.write(
            self.style.SUCCESS(f"\n✅ Successfully created {cards_created} cards!")
        )

    def _get_cards_for_tab(self, section, tab):
        """
        Get card data for a specific section/tab combination.
        Returns a list of 3-4 card dictionaries ready to create.
        """
        
        # Get configuration
        allowed_tags = get_tags_for_tab(section, tab)
        info_elements_count = get_info_elements_config(section, tab)
        
        # Route to section-specific method
        if section == "adotta-un-progetto":
            return self._cards_adotta_un_progetto(tab, allowed_tags, info_elements_count)
        elif section == "storie-e-radici":
            return self._cards_storie_e_radici(tab, allowed_tags, info_elements_count)
        elif section == "eccellenze-calabresi":
            return self._cards_eccellenze_calabresi(tab, allowed_tags, info_elements_count)
        elif section == "calendario-delle-radici":
            return self._cards_calendario_delle_radici(tab, allowed_tags, info_elements_count)
        elif section == "scopri-la-calabria":
            return self._cards_scopri_la_calabria(tab, allowed_tags, info_elements_count)
        elif section == "scambi-e-mobilita":
            return self._cards_scambi_e_mobilita(tab, allowed_tags, info_elements_count)
        elif section == "archivio":
            return self._cards_archivio(tab, allowed_tags, info_elements_count)
        
        return []

    # ========================================================================
    # ADOTTA UN PROGETTO
    # ========================================================================
    
    def _cards_adotta_un_progetto(self, tab, allowed_tags, info_elements_count):
        """
        Projects to adopt - 3-4 cards per tab
        Info elements: importo, impatto, scadenza
        """
        return [
            {
                'title': 'Centro Digitale per l\'Inclusione Sociale a Cosenza',
                'subtitle': 'Laboratorio tecnologico per corsi di coding e digital skills destinati a giovani a rischio di esclusione',
                'location': 'Cosenza, Italia',
                'tags': self._select_tags(allowed_tags, ['educazione', 'comunità']),
                'content': self._generate_rich_content(
                    'Trasformare vite attraverso la tecnologia',
                    'Progetto innovativo che mira a ridurre il divario digitale nelle aree interne della Calabria. '
                    'Formerai 150 giovani in linguaggi di programmazione, creerai una community di sviluppatori locali, '
                    'e faciliterai l\'accesso al mercato del lavoro tech. In partnership con Università della Calabria, Comune di Cosenza e Associazioni locali.',
                    include_list=True,
                    include_link=True
                ),
                'cover_image': None,
                'date_type': 'range',
                'date_start': timezone.now().date() + timedelta(days=30),
                'date_end': timezone.now().date() + timedelta(days=365),
                'infoElementValues': ['€150.000', 'Alto - Formazione 150 giovani', '31 Marzo 2026'],
                'is_published': True,
            },
            {
                'title': 'Rigenerazione dell\'Orto Botanico Storico di Reggio Calabria',
                'subtitle': 'Restauro e valorizzazione di uno spazio verde pubblico come polo educativo e culturale',
                'location': 'Reggio Calabria, Italia',
                'tags': self._select_tags(allowed_tags, ['ambiente', 'comunità']),
                'content': self._generate_rich_content(
                    'Restaurare un gioiello della natura calabrese',
                    'Recupero di una struttura abbandonata con valore storico e paesaggistico significativo. '
                    'Pulizia, bonifica e piantumazione di specie autoctone della flora calabrese. '
                    'Creazione di percorsi accessibili e aree didattiche. Organizzazione di workshop e visite scolastiche per 40 scuole e 2000+ studenti.',
                    include_list=True,
                    include_link=True
                ),
                'cover_image': None,
                'date_type': 'range',
                'date_start': timezone.now().date() + timedelta(days=45),
                'date_end': timezone.now().date() + timedelta(days=180),
                'infoElementValues': ['€80.000', 'Medio - Impatto ambientale e educativo', '30 Giugno 2026'],
                'is_published': True,
            },
            {
                'title': 'Piattaforma per l\'Agricoltura Sostenibile in Calabria',
                'subtitle': 'Tecnologia blockchain per tracciabilità e commercio diretto dei prodotti agricoli locali',
                'location': 'Catanzaro, Italia',
                'tags': self._select_tags(allowed_tags, ['sviluppo', 'internazionale']),
                'content': self._generate_rich_content(
                    'Innovazione digitale per l\'agricoltura calabrese',
                    'Progetto di innovazione digitale applicata all\'agroindustria calabrese. Creazione di una piattaforma digitale con 150+ produttori locali, '
                    'sistema di certificazione blockchain per l\'autenticità, e mercato virtuale con spedizioni in tutta Italia e Europa. '
                    'Risultati attesi: aumento del 300% delle vendite dirette e creazione di 20 nuovi posti di lavoro.',
                    include_list=True,
                    include_link=True
                ),
                'cover_image': None,
                'date_type': 'range',
                'date_start': timezone.now().date() + timedelta(days=60),
                'date_end': timezone.now().date() + timedelta(days=540),
                'infoElementValues': ['€250.000', 'Alto - Innovazione e occupazione', '31 Dicembre 2025'],
                'is_published': True,
            },
            {
                'title': 'Programma di Welfare Territoriale per Famiglie Fragili a Crotone',
                'subtitle': 'Rete integrata di servizi sociali e supporto economico per nuclei familiari in difficoltà',
                'location': 'Crotone, Italia',
                'tags': self._select_tags(allowed_tags, ['comunità', 'sanità']),
                'content': self._generate_rich_content(
                    'Supporto concreto alle famiglie in difficoltà',
                    'Intervento strutturato di inclusione sociale con approccio multidimensionale. Consulenza legale e tributaria per PMI, '
                    'sostegno psicologico gratuito, corsi di formazione professionale, microcredito agevolato e mentoring imprenditoriale. '
                    'Nel primo anno l\'impatto diretto raggiungerà 200 famiglie della comunità crotoniese.',
                    include_list=True,
                    include_link=True
                ),
                'cover_image': None,
                'date_type': 'range',
                'date_start': timezone.now().date() + timedelta(days=20),
                'date_end': timezone.now().date() + timedelta(days=365),
                'infoElementValues': ['€120.000', 'Alto - 200 famiglie supportate', '31 Dicembre 2026'],
                'is_published': True,
            },
        ]

    # ========================================================================
    # STORIE E RADICI
    # ========================================================================
    
    def _cards_storie_e_radici(self, tab, allowed_tags, info_elements_count):
        """
        Stories and roots section - different content per tab
        """
        if tab == 'storie':
            return [
                {
                    'title': 'Da Cosenza a Milano: La storia di una famiglia di imprenditori',
                    'subtitle': 'Come i valori calabresi hanno ispirato tre generazioni di successo',
                    'cover_image': self._get_random_image_url(),
                    'content': self._generate_rich_content(
                        'Dalla bottega di artigiani al design moderno',
                        'La storia di Salvatore inizia nel 1952 a Cosenza, in una bottega di artigiani. Suo nonno Vincenzo '
                        'creava mobili in legno con tecniche tramandate da generazioni. Nel 1985 fondò la sua prima azienda '
                        'a Milano, unendo l\'artigianalità calabrese con le innovazioni del design moderno.',
                        include_list=True,
                        include_link=True
                    ),
                    'tags': [],
                    'date_type': 'none',
                    'is_published': True,
                    'infoElementValues': [],
                },
                {
                    'title': 'Quando le radici nutrono le ali: Dalla Calabria al mondo',
                    'subtitle': 'Ricordi di un medico che ha portato l\'orgoglio calabrese nell\'eccellenza globale',
                    'cover_image': self._get_random_image_url(),
                    'content': self._generate_rich_content(
                        'Una carriera internazionale costruita sui valori calabresi',
                        'Dottor Francesco Arcuri, cardiologo di fama internazionale, racconta il suo viaggio. '
                        'Mio padre era un semplice contadino nella provincia di Reggio Calabria. Nonostante le difficoltà '
                        'economiche, insistette affinché studiassi. La sua determinazione mi ha insegnato il valore della '
                        'crescita personale e della dedizione.',
                        include_list=True,
                        include_link=True
                    ),
                    'tags': [],
                    'date_type': 'none',
                    'is_published': True,
                    'infoElementValues': [],
                },
                {
                    'title': 'Imprenditoria femminile: Le donne calabresi che cambiano il mercato',
                    'subtitle': 'Tre racconto di coraggio, innovazione e radici',
                    'cover_image': self._get_random_image_url(),
                    'content': self._generate_rich_content(
                        'Donne che trasformano la Calabria dall\'interno',
                        'Tre donne, tre storie diverse ma accomunate da una visione condivisa: trasformare la Calabria '
                        'in un polo di innovazione. Marisa Russo ha trasformato la ricetta della nonna in un brand '
                        'internazionale. Elena De Luca ha fondato una startup che crea app per l\'inclusione digitale. '
                        'Giada Toretta fonde tessitura tradizionale e design contemporaneo.',
                        include_list=True,
                        include_link=True
                    ),
                    'tags': [],
                    'date_type': 'none',
                    'is_published': True,
                    'infoElementValues': [],
                },
            ]
        
        elif tab == 'tradizioni':
            return [
                {
                    'title': 'La Festa di San Cosmo e San Damiano: Tradizione e Comunità',
                    'subtitle': 'Una celebrazione che nutre corpo e anima in provincia di Cosenza',
                    'cover_image': self._get_random_image_url(),
                    'content': self._generate_rich_content(
                        'Una festa che dura tre giorni',
                        'Il primo settembre, nella piccola cittadina di San Cosmo Albanese, inizia una festa che dura '
                        'tre giorni e mobilita l\'intera comunità di 3000 abitanti. Risale al XVII secolo quando una grande '
                        'siccità minacciò i raccolti. La comunità si affidò ai Santi protettori e da allora ogni anno si '
                        'rinnova la promessa di gratitudine.',
                        include_list=True,
                        include_link=True
                    ),
                    'tags': self._select_tags(allowed_tags, ['festa', 'tradizione']),
                    'date_type': 'none',
                    'is_published': True,
                    'infoElementValues': [],
                },
                {
                    'title': 'L\'Artigianato della Ceramica Calabrese: Arte Tramandato da Secoli',
                    'subtitle': 'Quando le mani sagge trasformano l\'argilla in bellezza',
                    'cover_image': self._get_random_image_url(),
                    'content': self._generate_rich_content(
                        'L\'arte della ceramica a Seminara',
                        'A Seminara, nel reggino, l\'arte della ceramica ha radici che si perdono nel Medioevo. '
                        'Ogni pezzo è creato a mano utilizzando una ruota di tornio in legno, esattamente come facevano '
                        'i maestri artigiani sei secoli fa. L\'argilla viene estratta dalle colline circostanti, le forme '
                        'rappresentano spesso geometrie e simboli della tradizione calabrese.',
                        include_list=True,
                        include_link=True
                    ),
                    'tags': self._select_tags(allowed_tags, ['artigianato', 'tradizione']),
                    'date_type': 'none',
                    'is_published': True,
                    'infoElementValues': [],
                },
                {
                    'title': 'I Suoni della Tarantella: La Danza che Parla l\'Anima Calabrese',
                    'subtitle': 'Ritmi antichi, passi che raccontano la storia di un popolo',
                    'cover_image': self._get_random_image_url(),
                    'content': self._generate_rich_content(
                        'La tarantella: linguaggio ancestrale',
                        'La tarantella calabrese non è solo una danza, è un linguaggio ancestrale che esprime gioie, '
                        'dolori, speranze di generazioni. Secondo la leggenda, il nome deriva dal morso della tarantola '
                        'che causava compulsioni al movimento. Storicamente, è nata come forma di catarsi collettiva: '
                        'attraverso il ballo ritmico e la musica vivace, le comunità scacciavano la negatività e celebravano la vita.',
                        include_list=True,
                        include_link=True
                    ),
                    'tags': self._select_tags(allowed_tags, ['tradizione', 'folklore']),
                    'date_type': 'none',
                    'is_published': True,
                    'infoElementValues': [],
                },
            ]
        
        elif tab == 'testimonianze':
            return [
                {
                    'title': '',
                    'subtitle': 'Mi sono trasferito a New York come ingegnere, ma ogni successo l\'ho regalato ai miei genitori.',
                    'location': 'New York, USA',
                    'content': (
                        '<p>"Mio padre era muratore e mia madre casalinga. Sono stato il primo della famiglia a conseguire una laurea. '
                        'Oggi, a 52 anni, sono direttore tecnico in una multinazionale energetica.</p>'
                        '<p>Non mi è mai dimenticato da dove vengo. La Calabria mi ha insegnato il valore del lavoro, dell\'onestà e della '
                        'responsabilità verso la propria famiglia. Ogni anno torno e investo nel mio paese: una scuola di formazione tecnica, '
                        'due borse di studio per giovani talenti, e supporto a un laboratorio artigianale locale.</p>'
                        '<p>La distanza geografica non cambia l\'appartenenza. Sono un calabrese che fortunatamente ha potuto realizzarsi, '
                        'e questa fortuna mi impone il dovere di restituire".</p>'
                    ),
                    'cover_image': None,
                    'tags': [],
                    'date_type': 'none',
                    'is_published': True,
                    'infoElementValues': [],
                },
                {
                    'title': '',
                    'subtitle': 'Sono rimasta in Calabria e ho creato un\'azienda con visione globale. Lo stile di vita conta più dei soldi.',
                    'location': 'Cosenza, Italia',
                    'content': (
                        '<p>"All\'università mi offrirono stage a Milano e Roma. Molti dei miei compagni se ne andarono. Io scelsi di restare.'
                        '<p>La ragione? Mia nonna ha una azienda di trasformazione dei prodotti agricoli, piccolina ma genuina. L\'ho ripresa '
                        'una decina di anni fa e l\'ho trasformata. Oggi esportiamo in 8 paesi, abbiamo 45 dipendenti, e i margini sono solidi.</p>'
                        '<p>La qualità della vita qui è incomparabile. Lavoro 8 ore, gioco a pallone 2 volte a settimana, ho una famiglia serena, '
                        'conosco personalmente i miei clienti, supporto 3 associazioni locali.</p>'
                        '<p>Se fossi a Milano, guadagnerei il 40% in più ma vivrei il 40% in meno. Ho scelto di vivere".</p>'
                    ),
                    'cover_image': None,
                    'tags': [],
                    'date_type': 'none',
                    'is_published': True,
                    'infoElementValues': [],
                },
                {
                    'title': '',
                    'subtitle': 'Ho insegnato per 35 anni in Calabria e ho visto generazioni sbocciare. Questo è il vero potere del Rotary.',
                    'location': 'Catanzaro, Italia',
                    'content': (
                        '<p>"Sono una maestra di scuola primaria. Negli ultimi 12 anni, il Club Rotary locale ha donato 15 computer alla mia scuola, '
                        'finanziato 8 progetti educativi, creato borse di studio per 32 alunni meritevoli e talentosi.</p>'
                        '<p>Ho visto bambini che non sapevano leggere diventare ingegneri. Ho visto bambine date per perse dai loro genitori '
                        'diventare medichesse e avvocate.</p>'
                        '<p>Il Rotary non regala soldi. Regala possibilità. E la possibilità è il dono più grande che puoi fare a un bambino '
                        'della periferia calabrese. Quando i miei ex alunni di vent\'anni fa passano a salutarmi e mi dicono "signora maestra, '
                        'ce l\'abbiamo fatta", capisco che ogni progetto del Rotary è una vittoria per la comunità".</p>'
                    ),
                    'cover_image': None,
                    'tags': [],
                    'date_type': 'none',
                    'is_published': True,
                    'infoElementValues': [],
                },
            ]
        
        return []

    # ========================================================================
    # ECCELLENZE CALABRESI
    # ========================================================================
    
    def _cards_eccellenze_calabresi(self, tab, allowed_tags, info_elements_count):
        """
        Calabrian excellences - business conveniences
        Info elements: sconto
        """
        return [
            {
                'title': 'Ristorante "Nduja & Tradizione" - Cosenza',
                'subtitle': 'Specialità calabresi autentiche con atmosfera storica e convivialità',
                'location': 'Cosenza, Italia',
                'tags': self._select_tags(allowed_tags, ['sconto', 'cosenza']),
                'content': self._generate_rich_content(
                    'La vera Calabria a tavola',
                    'Ristorante specializzato in piatti tradizionali calabresi. La \'nduja, il caciocavallo, le lagane, lo stocco alla messinese. '
                    'Atmosfera autentica con arredi storici e una wine list di vini calabresi di qualità. Perfetto per cene di affari e riunioni Rotary. '
                    'Chef con esperienza internazionale che reinterpreta le ricette nonne calabresi.',
                    include_list=False,
                    include_link=False
                ),
                'cover_image': self._get_random_image_url(),
                'date_type': 'none',
                'infoElementValues': ['20% sconto per i Rotariani'],
                'is_published': True,
            },
            {
                'title': 'Azienda Agricola "Terre di Reggio" - Reggio Calabria',
                'subtitle': 'Produttore biologico certificato di agrumi e bergamotto calabrese',
                'location': 'Reggio Calabria, Italia',
                'tags': self._select_tags(allowed_tags, ['sconto', 'reggio-calabria']),
                'content': self._generate_rich_content(
                    'Eccellenza biologica calabrese',
                    'Azienda agricola che produce agrumi e bergamotto secondo i più rigidi standard biologici. '
                    'Coltivazioni tradizionali sulle colline di Reggio. I loro succhi e oli essenziali sono esportati in tutta Europa. '
                    'Visita ai campi con spiegazione del processo di coltivazione e trasformazione. Disponibili per fornimenti all\'ingrosso.',
                    include_list=False,
                    include_link=False
                ),
                'cover_image': self._get_random_image_url(),
                'date_type': 'none',
                'infoElementValues': ['Degustazione gratuita e sconto 15% su acquisti'],
                'is_published': True,
            },
            {
                'title': 'Biblioteca Storica "Codex Calabricus" - Crotone',
                'subtitle': 'Centro di ricerca con collezione unica di manoscritti calabresi medievali',
                'location': 'Crotone, Italia',
                'tags': self._select_tags(allowed_tags, ['gratis', 'crotone']),
                'content': self._generate_rich_content(
                    'Un tesoro di storia calabrese',
                    'Centro di ricerca con collezione unica di manoscritti calabresi dal medioevo all\'era moderna. '
                    'Documenti originali sulla storia dei Rotary Club calabresi, studi sulla cultura arbëreshë, testi rari sulla filosofia calabrese. '
                    'Biblioteca specializzata in studi sud-italiani con oltre 5000 volumi. Sala lettura con accesso a database digitali internazionali.',
                    include_list=False,
                    include_link=False
                ),
                'cover_image': self._get_random_image_url(),
                'date_type': 'none',
                'infoElementValues': ['Visita libera gratuita per i soci Rotary'],
                'is_published': True,
            },
            {
                'title': 'Laboratorio di Artigianato "Ceramiche Seminara" - Reggio Calabria',
                'subtitle': 'Produzione artigianale di ceramiche secondo i metodi tradizionali del XVI secolo',
                'location': 'Reggio Calabria, Italia',
                'tags': self._select_tags(allowed_tags, ['sconto', 'reggio-calabria']),
                'content': self._generate_rich_content(
                    'L\'arte della ceramica vive ancora',
                    'Laboratorio dove maestri ceramisti produce opere secondo le tecniche del XVI secolo. '
                    'Le ceramiche di Seminara sono riconosciute come patrimonio intangibile dell\'UNESCO. Ogni pezzo è unico e creato a mano. '
                    'Possibilità di custom orders per regali aziendali e commissioni speciali. Visita del laboratorio con dimostrazione pratica.',
                    include_list=False,
                    include_link=False
                ),
                'cover_image': self._get_random_image_url(),
                'date_type': 'none',
                'infoElementValues': ['25% di sconto su tutti i prodotti artigianali'],
                'is_published': True,
            },
        ]

    # ========================================================================
    # CALENDARIO DELLE RADICI
    # ========================================================================
    
    def _cards_calendario_delle_radici(self, tab, allowed_tags, info_elements_count):
        """
        Calendar of events
        """
        return [
            {
                'title': 'Festival della Biodiversità Calabrese',
                'subtitle': 'Tre giorni dedicati alla scoperta della flora e fauna endemica della Calabria',
                'location': 'Sila, Cosenza',
                'cover_image': self._get_random_image_url(),
                'content': self._generate_rich_content(
                    'Un evento unico celebra la straordinaria biodiversità',
                    'Un evento unico che celebra la straordinaria biodiversità del Parco Nazionale della Sila. '
                    'Escursioni guidate con esperti botanici, workshop su conservazione ambientale, mostra fotografica '
                    'della natura calabrese e cena a km0 con produttori locali.',
                    include_list=True,
                    include_link=True
                ),
                'tags': ['in-presenza'],
                'date_type': 'range',
                'date_start': timezone.now().date() + timedelta(days=90),
                'date_end': timezone.now().date() + timedelta(days=92),
                'is_published': True,
                'infoElementValues': [],
            },
            {
                'title': 'Radici in Festa: Cena Galeotta Calabrese',
                'subtitle': 'Serata conviviale con piatti tipici della tradizione rurale calabrese',
                'location': 'Catanzaro, Italia',
                'cover_image': self._get_random_image_url(),
                'content': self._generate_rich_content(
                    'Una celebrazione della tavola calabrese',
                    'Una celebrazione della tavola calabrese in cui ogni portata racconta una storia. Menu tradizionale '
                    'con antipasti, primi, secondi e dolci tipici. Con musica tradizionale e tarantelle dal vivo.',
                    include_list=True,
                    include_link=True
                ),
                'tags': ['in-presenza'],
                'date_type': 'single',
                'date': timezone.now().date() + timedelta(days=120),
                'is_published': True,
                'infoElementValues': [],
            },
            {
                'title': 'Convegno Internazionale "Rotary e Territorialità"',
                'subtitle': 'Condivisione di best practices su come il Rotary impatta lo sviluppo locale',
                'location': 'Reggio Calabria, Italia',
                'cover_image': self._get_random_image_url(),
                'content': self._generate_rich_content(
                    'Appuntamento che riunisce rotariani e studiosi',
                    'Un appuntamento che riunisce rotariani e studiosi da tutta Italia e dall\'estero. '
                    'Tematiche: Innovazione sociale nei club locali, progetti di inclusione economica, '
                    'gemellaggi internazionali e scambi culturali, sostenibilità e responsabilità ambientale.',
                    include_list=True,
                    include_link=True
                ),
                'tags': ['online', 'in-presenza'],
                'date_type': 'range',
                'date_start': timezone.now().date() + timedelta(days=150),
                'date_end': timezone.now().date() + timedelta(days=152),
                'is_published': True,
                'infoElementValues': [],
            },
            {
                'title': 'Mostra Itinerante "Maestri Calabresi"',
                'subtitle': 'Esposizione di opere di 20 artigiani contemporanei che preservano i mestieri tradizionali',
                'location': 'Cosenza, Italia',
                'cover_image': self._get_random_image_url(),
                'content': self._generate_rich_content(
                    'Una celebrazione dell\'artigianato calabrese contemporaneo',
                    'Una celebrazione dell\'artigianato calabrese contemporaneo con maestri ceramisti di Seminara, '
                    'tessitori tradizionali di San Cosmo Albanese, liutai di Reggio Calabria, artigiani della '
                    'lavorazione del legno e maestri della lavorazione del ferro.',
                    include_list=True,
                    include_link=True
                ),
                'tags': ['in-presenza'],
                'date_type': 'range',
                'date_start': timezone.now().date() + timedelta(days=60),
                'date_end': timezone.now().date() + timedelta(days=90),
                'is_published': True,
                'infoElementValues': [],
            },
        ]

    # ========================================================================
    # SCOPRI LA CALABRIA
    # ========================================================================
    
    def _cards_scopri_la_calabria(self, tab, allowed_tags, info_elements_count):
        """
        Discover Calabria section - split by itinerari, esperienze, consigli
        """
        if tab == 'itinerari':
            return [
                {
                    'title': 'Sila Grande: Il Polmone Verde della Calabria',
                    'subtitle': 'Trekking tra foreste millenarie, laghi alpini e borghi medievali',
                    'location': 'Sila, Cosenza',
                    'cover_image': self._get_random_image_url(),
                    'tags': self._select_tags(allowed_tags, ['cosenza']),
                    'content': self._generate_rich_content(
                        'Un itinerario di 3 giorni nel cuore del Parco Nazionale',
                        'Escursione mattutina al Lago Cecita, uno dei laghi più suggestivi d\'Italia. Trekking tra '
                        'il bosco di Carlomagno e foreste di pini silani. Visita al borgo di San Giovanni in Fiore '
                        'con i suoi telosai. Salita al Botte Donato, punto più alto della Sila con panorami incredibili.',
                        include_list=True,
                        include_link=True
                    ),
                    'date_type': 'none',
                    'infoElementValues': ['3 giorni'],
                    'is_published': True,
                },
                {
                    'title': 'Costa dei Gelsomini: Spiagge Incontaminate e Grotte Marine',
                    'subtitle': 'Navigazione lungo la costa ionica con snorkeling e storia millenaria',
                    'location': 'Crotone, Italia',
                    'cover_image': self._get_random_image_url(),
                    'tags': self._select_tags(allowed_tags, ['crotone']),
                    'content': self._generate_rich_content(
                        'Un itinerario marittimo di 2 giorni',
                        'Navigazione verso l\'Area Marina Protetta di Capo Rizzuto. Snorkeling tra fondali ricchi '
                        'di biodiversità. Visita al Castello Aragonese. Esplorazione di spiagge raggiunte solo dal mare '
                        'e grotte geologicamente interessanti. Cena di pesce fresco.',
                        include_list=True,
                        include_link=True
                    ),
                    'date_type': 'none',
                    'infoElementValues': ['2 giorni'],
                    'is_published': True,
                },
                {
                    'title': 'Itinerario delle Radici: 5 Borghi Storici della Calabria Centrale',
                    'subtitle': 'Viaggio tra storia, architettura e tradizioni dialettali diverse',
                    'location': 'Catanzaro, Italia',
                    'cover_image': self._get_random_image_url(),
                    'tags': self._select_tags(allowed_tags, ['catanzaro']),
                    'content': self._generate_rich_content(
                        'Un itinerario di 3 giorni attraverso borghi storici',
                        'Visita a Taverna (patria di Mattia Preti), Soriano Calabro (ex convento-fortezza), '
                        'San Floro (la Betlemme calabrese), Frascineto (borgata arbëreshë con tradizioni bizantine) '
                        'e Papanice (il paese degli artisti). Scopri il DNA della Calabria attraverso storia e architettura.',
                        include_list=True,
                        include_link=True
                    ),
                    'date_type': 'none',
                    'infoElementValues': ['3 giorni'],
                    'is_published': True,
                },
                {
                    'title': 'Straits of Messina Crossing: Reggio Calabria al Confine d\'Italia',
                    'subtitle': 'Escursione storica e paesaggistica tra il mito e la realtà dello Stretto',
                    'location': 'Reggio Calabria, Italia',
                    'cover_image': self._get_random_image_url(),
                    'tags': self._select_tags(allowed_tags, ['reggio-calabria']),
                    'content': self._generate_rich_content(
                        'Un itinerario di 2 giorni in uno dei luoghi più mitologici',
                        'Visita al Museo Archeologico Nazionale con i Bronzi di Riace. Passeggiata sul lungomare '
                        'più bello d\'Italia e cena di pesce spada. Salita verso i piccoli villaggi dell\'Aspromonte '
                        'con viste sulla Sicilia, sul vulcano Etna e sullo Stretto.',
                        include_list=True,
                        include_link=True
                    ),
                    'date_type': 'none',
                    'infoElementValues': ['2 giorni'],
                    'is_published': True,
                },
            ]
        
        elif tab == 'esperienze':
            return [
                {
                    'title': 'Immersioni nella Calabria Subacquea: Il Paradiso Sommerso',
                    'subtitle': 'Esperienze di snorkeling e immersioni nella riviera più bella del Mediterraneo',
                    'location': 'Scilla, Reggio Calabria',
                    'cover_image': self._get_random_image_url(),
                    'tags': self._select_tags(allowed_tags, ['reggio-calabria']),
                    'content': self._generate_rich_content(
                        'Un\'esperienza unica nel mare della Calabria',
                        'Immersioni guidate nei siti di Scilla e Capo Vaticano. Scopri una biodiversità marina eccezionale: '
                        'barracuda, tonni, e specie endemiche del Mediterraneo. Lezioni di snorkeling per principianti. '
                        'Colazioni di pesce sulla spiaggia con i pescatori locali.',
                        include_list=True,
                        include_link=True
                    ),
                    'date_type': 'none',
                    'infoElementValues': ['Attività acquatiche'],
                    'is_published': True,
                },
                {
                    'title': 'Cammini Mistici della Calabria: Trekking Spirituali tra Santuari e Monasteri',
                    'subtitle': 'Percorsi a piedi che collegano i luoghi sacri della tradizione calabrese',
                    'location': 'Calabria Centrale',
                    'cover_image': self._get_random_image_url(),
                    'tags': self._select_tags(allowed_tags, ['catanzaro']),
                    'content': self._generate_rich_content(
                        'Un\'esperienza di connessione spirituale e culturale',
                        'Cammino di 5 giorni che collega il Santuario di San Francesco di Paola a Cosenza, monasteri bizantini '
                        'tra i monti dell\'Aspromonte, e basiliche paleocristiane nascoste tra i boschi. Meditazioni guidate nei '
                        'luoghi di culto più antichi. Cene in conventi con ricette tradizionali monacali.',
                        include_list=True,
                        include_link=True
                    ),
                    'date_type': 'none',
                    'infoElementValues': ['5 giorni'],
                    'is_published': True,
                },
                {
                    'title': 'Laboratori Artigianali: Impara i Mestieri della Tradizione Calabrese',
                    'subtitle': 'Workshop hands-on con maestri artigiani di ceramica, tessuti e intagli',
                    'location': 'Vari borghi calabresi',
                    'cover_image': self._get_random_image_url(),
                    'tags': self._select_tags(allowed_tags, ['tradizioni']),
                    'content': self._generate_rich_content(
                        'Un\'esperienza autentica con i maestri calabresi',
                        'Scegli tra laboratori di ceramica a Santo Stefano in Aspromonte, tessiture a telaio a Longobardi, '
                        'intagli di legno ad Aprigliano, o lavorazione del corallo a Scilla. Ogni laboratorio dura 3 giorni e '
                        'produce un\'opera finale che potrai portare a casa. Alloggio in case di artigiani.',
                        include_list=True,
                        include_link=True
                    ),
                    'date_type': 'none',
                    'infoElementValues': ['3 giorni per laboratorio'],
                    'is_published': True,
                },
                {
                    'title': 'Food Tours Enogastronomici: Dalla Tavola alla Vite nei Terroir Calabresi',
                    'subtitle': 'Degustazioni guidate di vini DOP, formaggi, e specialità tipiche regionali',
                    'location': 'Valli del Crati e Ionian Coast',
                    'cover_image': self._get_random_image_url(),
                    'tags': self._select_tags(allowed_tags, ['enogastronomia']),
                    'content': self._generate_rich_content(
                        'Un tour enogastronomico indimenticabile',
                        'Visita a cantine storiche nel Cirò e Melissa per degustazione di vini rossi prestigiosi. Fattorie di produzione di '
                        'pecorino e caciocavallo in Sila. Caseifici artigianali a Cotronei. Tour nei borghi gastronomici di Praia a Mare e Scilla '
                        'per pesce fresco. Cena con chef stellato che utilizza ingredienti calabresi.',
                        include_list=True,
                        include_link=True
                    ),
                    'date_type': 'none',
                    'infoElementValues': ['4 giorni'],
                    'is_published': True,
                },
            ]
        
        elif tab == 'consigli':
            return [
                {
                    'title': 'Visita la Sila nei mesi di giugno e settembre per il clima ideale',
                    'subtitle': 'Evita luglio e agosto quando è affollata di turisti',
                    'location': None,
                    'content': self._generate_rich_content(
                        'Il momento migliore per la Sila',
                        'Giugno e settembre offrono temperature moderate (18-24°C), meno pioggia e pienamente godibili per escursioni. '
                        'Luglio e agosto sono affollati di turisti lombardi e romani. Maggio è fresco ma bellissimo per i fiori alpini. '
                        'Novembre-marzo le strade si ghiacciano e molti rifugi chiudono.',
                        include_list=False,
                        include_link=False
                    ),
                    'cover_image': None,
                    'tags': [],
                    'date_type': 'none',
                    'is_published': True,
                    'infoElementValues': [],
                },
                {
                    'title': 'I borghi arbëreshë della provincia di Cosenza meritano 2-3 giorni di visita dedicata',
                    'subtitle': 'Cultura albanese, chiese bizantine e tradizioni uniche nel panorama italiano',
                    'location': None,
                    'content': self._generate_rich_content(
                        'Borghi con storia mille anni di profondità',
                        'Frascineto, San Demetrio Corone, Civita, Acri e Lungro conservano una cultura albanese (arbëreshë) arrivata nel 1600. '
                        'Le chiese seguono il rito bizantino, la cucina è affascinante (fave e cicoria, çka e prasa), le tradizioni tessili sono uniche. '
                        'Perfetto per chi vuole scoprire un "Italia nascosta".',
                        include_list=False,
                        include_link=False
                    ),
                    'cover_image': None,
                    'tags': [],
                    'date_type': 'none',
                    'is_published': True,
                    'infoElementValues': [],
                },
                {
                    'title': 'Non perdere l\'Aspromonte: il "balcone della Sicilia"',
                    'subtitle': 'Specialmente al tramonto, le viste sulla Sicilia e lo Stretto di Messina sono spettacolari',
                    'location': None,
                    'content': self._generate_rich_content(
                        'Il punto di osservazione più sublime della Calabria',
                        'Dall\'Aspromonte, a 1956 metri, puoi vedere il vulcano Etna in Sicilia e lo Stretto di Messina perfettamente disegnato. '
                        'Il tramonto ricopre tutto di oro. Le strade verso la vetta sono panoramiche (SP502). Consigliati: Madonna di Polsi, '
                        'Fiumara di Amendolea. Tempo meteo stabile: ottobre-aprile.',
                        include_list=False,
                        include_link=False
                    ),
                    'cover_image': None,
                    'tags': [],
                    'date_type': 'none',
                    'is_published': True,
                    'infoElementValues': [],
                },
            ]
        
        return []

    # ========================================================================
    # SCAMBI E MOBILITA
    # ========================================================================
    
    def _cards_scambi_e_mobilita(self, tab, allowed_tags, info_elements_count):
        """
        Exchanges and mobility - split by offri (offer) and cerca (search)
        Info elements: posti_disponibili, periodo_anno
        """
        if tab == 'offri':
            return [
                {
                    'title': 'Tirocinio in Azienda Tecnologica a Milano - IT Development',
                    'subtitle': 'Offriamo opportunità di stage per giovani sviluppatori e data analyst interessati all\'industria tech',
                    'location': 'Milano, Italia',
                    'content': self._generate_rich_content(
                        'Esperienza tech in una realtà internazionale',
                        'La nostra azienda partner a Milano, leader nel cloud computing e AI, cerca 5 giovani talenti per un programma di 6 mesi. '
                        'Lavorerai su progetti reali di machine learning, sviluppo backend, e data engineering. Mentorship di esperti, stipendio competitivo, '
                        'possibilità di inserimento a fine stage. Perfetto per chi vuole una carriera tech di qualità.',
                        include_list=True,
                        include_link=True
                    ),
                    'cover_image': None,
                    'tags': [],
                    'date_type': 'none',
                    'infoElementValues': ['5 posti disponibili', 'Da giugno a settembre'],
                    'is_published': True,
                },
                {
                    'title': 'Scambio Culturale: Toronto - Programma 6 Mesi',
                    'subtitle': 'Il nostro Club Rotary di Toronto ospita giovani professionisti calabresi interessati a esperienze internazionali',
                    'location': 'Toronto, Canada',
                    'content': self._generate_rich_content(
                        'Crescita professionale e personale in Canada',
                        'Il Rotary Club di Toronto ti offre alloggio, mentorship, e rete professionale. Ideale per giovani professionisti (25-35 anni) '
                        'in accounting, marketing, sales, o management. Conoscerai il sistema business canadese, amplierai la tua rete internazionale, '
                        'e potrai esplorare il Nord America. Include visa sponsorship e health insurance.',
                        include_list=True,
                        include_link=True
                    ),
                    'cover_image': None,
                    'tags': [],
                    'date_type': 'none',
                    'infoElementValues': ['3 posti disponibili', 'Gennaio - Giugno'],
                    'is_published': True,
                },
                {
                    'title': 'Mentoring Professionale: Programma 1-a-1 Online',
                    'subtitle': 'Rotariani esperti disponibili per sessioni di mentoring in business strategy, leadership, finanza',
                    'location': 'Online, Worldwide',
                    'content': self._generate_rich_content(
                        'Sviluppa le tue competenze con mentor internazionali',
                        'Abbiamo 10 mentor Rotariani esperti (CEO, CFO, imprenditori) disponibili per sessioni settimanali. Svilupperai competenze in leadership, '
                        'strategia, fundraising, innovazione, o finanza. Flessibilità totale con incontri online. Impegno: 3-6 mesi, 1-2 ore settimanali. '
                        'Gratuito per giovani talenti della rete Rotary calabrese.',
                        include_list=True,
                        include_link=True
                    ),
                    'cover_image': None,
                    'tags': [],
                    'date_type': 'none',
                    'infoElementValues': ['10 posti disponibili', 'Anno intero'],
                    'is_published': True,
                },
                {
                    'title': 'Visiting Scholar: Università di Bologna - Ricerca e Didattica',
                    'subtitle': 'Posizioni aperte per ricercatori e docenti interessati a collaborare su progetti di sostenibilità territoriale',
                    'location': 'Bologna, Italia',
                    'content': self._generate_rich_content(
                        'Collaborazione accademica ad alto livello',
                        'L\'Università di Bologna, in partnership con il nostro network Rotary, cerca 2 ricercatori/docenti per un anno accademico di collaborazione. '
                        'Focus: sostenibilità ambientale, economia circolare, sviluppo rurale, e innovazione territoriale. Sala office dedicata, accesso a '
                        'laboratori, stipendio, e possibilità di pubblicazioni internazionali. Ottimo per consolidare carriera accademica.',
                        include_list=True,
                        include_link=True
                    ),
                    'cover_image': None,
                    'tags': [],
                    'date_type': 'none',
                    'infoElementValues': ['2 posti disponibili', 'Settembre - Agosto'],
                    'is_published': True,
                },
            ]
        
        elif tab == 'cerca':
            return [
                {
                    'title': 'Cerchiamo Mentor in Digital Marketing per Startup Calabrese',
                    'subtitle': 'Ricerchiamo professionista esperto disposto a seguire team di 4 giovani imprenditori',
                    'location': 'Cosenza, Italia',
                    'content': self._generate_rich_content(
                        'Aiuta una startup calabrese a crescere online',
                        'Startup giovane e energica che vende cosmetici biologici calabresi cerca mentor esperto. Il mentor guiderà il team in strategie '
                        'di social media, email marketing, SEO, e brand positioning. Impegno: 4-6 ore mensili per 9-12 mesi. Possibilità di equity stake. '
                        'Ambiente dinamico, prodotti di qualità, mercato con grande potenziale.',
                        include_list=True,
                        include_link=True
                    ),
                    'cover_image': None,
                    'tags': [],
                    'date_type': 'none',
                    'infoElementValues': ['1 mentor cercato', 'Febbraio - Dicembre'],
                    'is_published': True,
                },
                {
                    'title': 'Cercasi Docente di Ingegneria Civile per Master\'s Equivalence',
                    'subtitle': 'Università Calabrese in cerca di professionista con esperienza per insegnamento part-time',
                    'location': 'Catanzaro, Italia',
                    'content': self._generate_rich_content(
                        'Insegna e trasmetti esperienza ai giovani professionisti',
                        'Università di Catanzaro cerca docente di Ingegneria Civile con master internazionale e 5+ anni di esperienza pratica. '
                        'Insegnerai 2 corsi di 48 ore ciascuno (fondamenti e progettazione). Retribuzione competitiva, flessibilità negli orari, possibilità '
                        'di ricerca collaborativa. Perfetto per mantenere contatti accademici',
                        include_list=True,
                        include_link=True
                    ),
                    'cover_image': None,
                    'tags': [],
                    'date_type': 'none',
                    'infoElementValues': ['1 docente cercato', 'Anno accademico 2025-26'],
                    'is_published': True,
                },
                {
                    'title': 'Scambio Aziendale: Azienda Calabrese Cerca Partner Europeo',
                    'subtitle': 'Azienda di processing agricolo in Calabria cerca joint-venture con partner europeo per export',
                    'location': 'Reggio Calabria, Italia',
                    'content': self._generate_rich_content(
                        'Espandi la tua azienda nei mercati calabresi',
                        'Azienda leader nel processing di bergamotto, limone e arancia cerca partner europeo per esportazione e distribuzione. '
                        'Prodotti biologici certificati, filiera controllata. Cerchiamo azienda con rete in Francia, Germania, o paesi del Nord Europa. '
                        'Opportunità di crescita reciproca, marchio forte, prodotti premium.',
                        include_list=True,
                        include_link=True
                    ),
                    'cover_image': None,
                    'tags': [],
                    'date_type': 'none',
                    'infoElementValues': ['2 partner cercati', 'Da subito'],
                    'is_published': True,
                },
                {
                    'title': 'Ricerca Volontari: Progetto di Ricerca Medica nel Sud Italia',
                    'subtitle': 'Centro di ricerca biomedica cerca volontari per partecipare a studio clinico di 8 settimane',
                    'location': 'Napoli, Italia',
                    'content': self._generate_rich_content(
                        'Contribuisci alla ricerca medica',
                        'Centro di ricerca accreditato presso università napoletana cerca 15 volontari sani (18-60 anni) per studio clinico su '
                        'nutraceutici derivati da piante calabresi. 8 settimane, visite settimanali, compenso €300. Studi preliminari mostrano benefici '
                        'per metabolismo e antiossidanti. Studio etico approvato.',
                        include_list=True,
                        include_link=True
                    ),
                    'cover_image': None,
                    'tags': [],
                    'date_type': 'none',
                    'infoElementValues': ['15 volontari cercati', 'Marzo - Novembre'],
                    'is_published': True,
                },
            ]
        
        return []

    # ========================================================================
    # ARCHIVIO
    # ========================================================================
    
    def _cards_archivio(self, tab, allowed_tags, info_elements_count):
        """
        Archive section with historical and archival content
        """
        return [
            {
                'title': 'Documento Storico: Statuto del Rotary Club Reggio Calabria (1952)',
                'subtitle': 'Fondazione e primi anni di attività del club più antico della Calabria',
                'location': None,
                'tags': self._select_tags(allowed_tags, ['testo']),
                'content': self._generate_rich_content(
                    'Le origini del Rotary in Calabria',
                    'Il Rotary Club Reggio Calabria è stato fondato nel 1952, durante gli anni di ricostruzione post-bellica, da 32 soci fondatori, '
                    'figure prominenti della borghesia locale e del mondo professionale. Lo statuto originale, conservato nell\'archivio del Club, '
                    'documenta i valori e gli obiettivi del club. Nel documento si riflette l\'impegno verso l\'assistenza sociale e lo sviluppo della comunità, '
                    'temi ancora oggi centrali nell\'azione del Club.',
                    include_list=False,
                    include_link=False
                ),
                'cover_image': None,
                'date_type': 'none',
                'is_published': True,
                'infoElementValues': [],
            },
            {
                'title': 'Foto Storica: Cena Galeotta 1985 - Reunion Generazionale',
                'subtitle': 'Archivio fotografico della celebre cena che riunì 200+ Rotariani da tutta Italia',
                'location': None,
                'tags': self._select_tags(allowed_tags, ['foto']),
                'content': self._generate_rich_content(
                    'Un momento storico del Rotary calabrese',
                    'Una raccolta di 45 fotografie a colori della cena galeotta del 1985, evento che marcò i 33 anni di fondazione del Club. '
                    'Tra i presenti, figure storiche del Rotary internazionale e regionale. Le foto documentano l\'evoluzione della comunità rotariana calabrese '
                    'e le reti di amicizia che si sono costruite nel tempo. Uno sguardo affascinante sui volti e gli istanti che hanno fatto storia.',
                    include_list=False,
                    include_link=False
                ),
                'cover_image': None,
                'date_type': 'none',
                'is_published': True,
                'infoElementValues': [],
            },
            {
                'title': 'Video Documentario: Il Rotary a Servizio della Calabria (1990-2020)',
                'subtitle': 'Documentario 45 minuti sui progetti e l\'impatto del Rotary nel territorio calabrese',
                'location': None,
                'tags': self._select_tags(allowed_tags, ['video']),
                'content': self._generate_rich_content(
                    'Tre decadi di service rotariano',
                    'Un viaggio affascinante attraverso tre decadi di service rotariano in Calabria. Il documentario, realizzato nel 2020, presenta '
                    'testimonianze di beneficiari, club member, amministratori pubblici e racconta come i progetti Rotary hanno trasformato comunità, '
                    'creato opportunità e rafforzato le connessioni umane. Una testimonianza del cambiamento positivo generato dal volontariato organizzato.',
                    include_list=False,
                    include_link=False
                ),
                'cover_image': None,
                'date_type': 'none',
                'is_published': True,
                'infoElementValues': [],
            },
            {
                'title': 'Archivio Testuale: Articoli da "Rotary Calabria" (1960-1980)',
                'subtitle': 'Collezione digitalizzata della rivista periodica ufficiale con 120 articoli e resoconti',
                'location': None,
                'tags': self._select_tags(allowed_tags, ['testo']),
                'content': self._generate_rich_content(
                    'Scritti che raccontano la storia',
                    'Testi storici che documentano l\'evoluzione culturale, sociale ed economica della Calabria attraverso lo sguardo della comunità Rotary. '
                    'La raccolta include resoconti di assemblee, interviste a personalità calabresi, articoli su progetti di service e riflessioni sulla mission Rotary '
                    'applicata al contesto locale. Una risorsa preziosa per comprendere come il Rotary ha accompagnato la trasformazione della regione.',
                    include_list=False,
                    include_link=False
                ),
                'cover_image': None,
                'date_type': 'none',
                'is_published': True,
                'infoElementValues': [],
            },
        ]

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def _select_tags(self, allowed_tags, preferred_tags):
        """
        Select 1-3 tags from the allowed list, preferring from the preferred list
        """
        if not allowed_tags:
            return []
        
        # Filter preferred tags to only those in allowed list
        available_preferred = [tag for tag in preferred_tags if tag in allowed_tags]
        
        # If we have preferred tags, use them; otherwise use random allowed tags
        if available_preferred:
            return random.sample(available_preferred, k=min(random.randint(1, 2), len(available_preferred)))
        else:
            return random.sample(allowed_tags, k=min(random.randint(1, 2), len(allowed_tags)))
