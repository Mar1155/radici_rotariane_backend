import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from users.models import User, Skill, SoftSkill
from forum.models import Post, Comment
from chat.models import Chat, Message
from section.models import Card


class Command(BaseCommand):
    help = "Seed demo data for presentation."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing demo-related data before seeding.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self._reset_data()

        self._ensure_skills()
        clubs = self._create_clubs()
        members = self._create_members(clubs)
        self._create_cards(clubs, members)
        posts = self._create_forum_posts(members)
        self._create_forum_comments(posts, members)
        self._create_chats(clubs, members)

        self.stdout.write(self.style.SUCCESS("Demo data created successfully."))

    def _reset_data(self):
        Message.objects.all().delete()
        Chat.objects.all().delete()
        Comment.objects.all().delete()
        Post.objects.all().delete()
        Card.objects.all().delete()
        User.objects.exclude(is_superuser=True).delete()

    def _ensure_skills(self):
        if Skill.objects.exists() and SoftSkill.objects.exists():
            return

        hard_skills = [
            ("Project Management", {"it": "Gestione Progetti"}),
            ("Software Development", {"it": "Sviluppo Software"}),
            ("Data Analysis", {"it": "Analisi Dati"}),
            ("Digital Marketing", {"it": "Marketing Digitale"}),
            ("Financial Planning", {"it": "Pianificazione Finanziaria"}),
            ("Legal Consulting", {"it": "Consulenza Legale"}),
            ("Medical Research", {"it": "Ricerca Medica"}),
            ("Graphic Design", {"it": "Design Grafico"}),
            ("Public Relations", {"it": "Pubbliche Relazioni"}),
            ("Business Strategy", {"it": "Strategia Aziendale"}),
            ("Engineering", {"it": "Ingegneria"}),
            ("Architecture", {"it": "Architettura"}),
            ("Event Planning", {"it": "Pianificazione Eventi"}),
            ("Social Media Management", {"it": "Gestione Social Media"}),
            ("Cybersecurity", {"it": "Sicurezza Informatica"}),
        ]

        soft_skills = [
            ("Leadership", {"it": "Leadership"}),
            ("Teamwork", {"it": "Lavoro di Squadra"}),
            ("Communication", {"it": "Comunicazione"}),
            ("Problem Solving", {"it": "Risoluzione Problemi"}),
            ("Time Management", {"it": "Gestione del Tempo"}),
            ("Adaptability", {"it": "Adattabilità"}),
            ("Critical Thinking", {"it": "Pensiero Critico"}),
            ("Conflict Resolution", {"it": "Risoluzione Conflitti"}),
            ("Emotional Intelligence", {"it": "Intelligenza Emotiva"}),
            ("Public Speaking", {"it": "Parlare in Pubblico"}),
            ("Negotiation", {"it": "Negoziazione"}),
            ("Creativity", {"it": "Creatività"}),
            ("Mentoring", {"it": "Mentoring"}),
            ("Decision Making", {"it": "Presa di Decisioni"}),
            ("Empathy", {"it": "Empatia"}),
        ]

        for name, translations in hard_skills:
            skill, _ = Skill.objects.get_or_create(name=name)
            skill.translations = translations
            skill.save()

        for name, translations in soft_skills:
            skill, _ = SoftSkill.objects.get_or_create(name=name)
            skill.translations = translations
            skill.save()

    def _create_clubs(self):
        clubs_data = [
            {
                "club_name": "Rotary Club Milano Duomo",
                "club_city": "Milano",
                "club_country": "Italia",
                "club_district": "2042",
                "club_latitude": 45.4642,
                "club_longitude": 9.1900,
                "bio": "<p>Club attivo su progetti di inclusione lavorativa e innovazione urbana.</p>",
            },
            {
                "club_name": "Rotary Club Torino Valentino",
                "club_city": "Torino",
                "club_country": "Italia",
                "club_district": "2032",
                "club_latitude": 45.0703,
                "club_longitude": 7.6869,
                "bio": "<p>Promuove programmi STEM per scuole superiori e mentoring professionale.</p>",
            },
            {
                "club_name": "Rotary Club Genova Porto Antico",
                "club_city": "Genova",
                "club_country": "Italia",
                "club_district": "2032",
                "club_latitude": 44.4056,
                "club_longitude": 8.9463,
                "bio": "<p>Focus su rigenerazione urbana e cultura marittima.</p>",
            },
            {
                "club_name": "Rotary Club Bologna Galvani",
                "club_city": "Bologna",
                "club_country": "Italia",
                "club_district": "2072",
                "club_latitude": 44.4949,
                "club_longitude": 11.3426,
                "bio": "<p>Attivo in progetti di formazione universitaria e ricerca applicata.</p>",
            },
            {
                "club_name": "Rotary Club Verona Arena",
                "club_city": "Verona",
                "club_country": "Italia",
                "club_district": "2060",
                "club_latitude": 45.4384,
                "club_longitude": 10.9916,
                "bio": "<p>Iniziative culturali e sostegno a imprese creative.</p>",
            },
            {
                "club_name": "Rotary Club Venezia Laguna",
                "club_city": "Venezia",
                "club_country": "Italia",
                "club_district": "2060",
                "club_latitude": 45.4408,
                "club_longitude": 12.3155,
                "bio": "<p>Progetti ambientali e tutela del patrimonio storico.</p>",
            },
            {
                "club_name": "Rotary Club Firenze Brunelleschi",
                "club_city": "Firenze",
                "club_country": "Italia",
                "club_district": "2071",
                "club_latitude": 43.7696,
                "club_longitude": 11.2558,
                "bio": "<p>Laboratori su turismo sostenibile e valorizzazione culturale.</p>",
            },
            {
                "club_name": "Rotary Club Pisa Galilei",
                "club_city": "Pisa",
                "club_country": "Italia",
                "club_district": "2071",
                "club_latitude": 43.7228,
                "club_longitude": 10.4017,
                "bio": "<p>Collaborazioni con universita' e centri di ricerca.</p>",
            },
            {
                "club_name": "Rotary Club Perugia Etrusca",
                "club_city": "Perugia",
                "club_country": "Italia",
                "club_district": "2090",
                "club_latitude": 43.1107,
                "club_longitude": 12.3908,
                "bio": "<p>Progetti di educazione civica e cittadinanza attiva.</p>",
            },
            {
                "club_name": "Rotary Club Roma Foro",
                "club_city": "Roma",
                "club_country": "Italia",
                "club_district": "2080",
                "club_latitude": 41.9028,
                "club_longitude": 12.4964,
                "bio": "<p>Programmi di sostegno a start-up sociali e progetti intergenerazionali.</p>",
            },
            {
                "club_name": "Rotary Club Pescara Adriatica",
                "club_city": "Pescara",
                "club_country": "Italia",
                "club_district": "2090",
                "club_latitude": 42.4618,
                "club_longitude": 14.2161,
                "bio": "<p>Iniziative sulla blue economy e formazione professionale.</p>",
            },
            {
                "club_name": "Rotary Club Napoli Partenope",
                "club_city": "Napoli",
                "club_country": "Italia",
                "club_district": "2101",
                "club_latitude": 40.8518,
                "club_longitude": 14.2681,
                "bio": "<p>Progetti su inclusione sociale e rigenerazione di quartieri storici.</p>",
            },
            {
                "club_name": "Rotary Club Bari Levante",
                "club_city": "Bari",
                "club_country": "Italia",
                "club_district": "2120",
                "club_latitude": 41.1171,
                "club_longitude": 16.8719,
                "bio": "<p>Network per l'imprenditoria giovanile e scambi professionali.</p>",
            },
            {
                "club_name": "Rotary Club Lecce Barocco",
                "club_city": "Lecce",
                "club_country": "Italia",
                "club_district": "2120",
                "club_latitude": 40.3529,
                "club_longitude": 18.1743,
                "bio": "<p>Progetti culturali con focus su artigianato e innovazione.</p>",
            },
            {
                "club_name": "Rotary Club Cagliari Castello",
                "club_city": "Cagliari",
                "club_country": "Italia",
                "club_district": "2080",
                "club_latitude": 39.2238,
                "club_longitude": 9.1217,
                "bio": "<p>Programmi di welfare territoriale e sostegno alle famiglie.</p>",
            },
            {
                "club_name": "Rotary Club Palermo Normanna",
                "club_city": "Palermo",
                "club_country": "Italia",
                "club_district": "2110",
                "club_latitude": 38.1157,
                "club_longitude": 13.3615,
                "bio": "<p>Progetti su legalita' e promozione della cultura civica.</p>",
            },
            {
                "club_name": "Rotary Club Messina Peloro",
                "club_city": "Messina",
                "club_country": "Italia",
                "club_district": "2110",
                "club_latitude": 38.1938,
                "club_longitude": 15.5540,
                "bio": "<p>Attivo su mobilita' sostenibile e azioni di protezione civile.</p>",
            },
            {
                "club_name": "Rotary Club Cosenza",
                "club_city": "Cosenza",
                "club_country": "Italia",
                "club_district": "2102",
                "club_latitude": 39.2983,
                "club_longitude": 16.2536,
                "bio": "<p>Club storico con focus su innovazione sociale e mentoring giovanile.</p>",
            },
            {
                "club_name": "Rotary Club Reggio Calabria",
                "club_city": "Reggio Calabria",
                "club_country": "Italia",
                "club_district": "2102",
                "club_latitude": 38.1112,
                "club_longitude": 15.6473,
                "bio": "<p>Impegnato in progetti di cooperazione internazionale e gemellaggi.</p>",
            },
            {
                "club_name": "Rotary Club Catanzaro",
                "club_city": "Catanzaro",
                "club_country": "Italia",
                "club_district": "2102",
                "club_latitude": 38.9097,
                "club_longitude": 16.5877,
                "bio": "<p>Promuove iniziative culturali e scambi professionali.</p>",
            },
            {
                "club_name": "Rotary Club Lamezia Terme",
                "club_city": "Lamezia Terme",
                "club_country": "Italia",
                "club_district": "2102",
                "club_latitude": 38.9667,
                "club_longitude": 16.3167,
                "bio": "<p>Specializzato in progetti di formazione e sviluppo locale.</p>",
            },
            {
                "club_name": "Rotary Club Toronto Calabria",
                "club_city": "Toronto",
                "club_country": "Canada",
                "club_district": "7070",
                "club_latitude": 43.6532,
                "club_longitude": -79.3832,
                "bio": "<p>Rotariani calabresi nel mondo con rete internazionale.</p>",
            },
            {
                "club_name": "Rotary Club New York Calabria",
                "club_city": "New York",
                "club_country": "USA",
                "club_district": "7230",
                "club_latitude": 40.7128,
                "club_longitude": -74.0060,
                "bio": "<p>Club dedicato alla valorizzazione delle eccellenze calabresi.</p>",
            },
        ]

        clubs = []
        for idx, data in enumerate(clubs_data, start=1):
            username = slugify(data["club_name"]).replace("-", "_")
            email = f"{username}@demo.rotary"
            club, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "user_type": User.Types.CLUB,
                    "club_name": data["club_name"],
                    "club_city": data["club_city"],
                    "club_country": data["club_country"],
                    "club_district": data["club_district"],
                    "club_latitude": data["club_latitude"],
                    "club_longitude": data["club_longitude"],
                    "bio": data["bio"],
                },
            )
            club.set_password("demo12345")
            club.save()
            clubs.append(club)

        return clubs

    def _create_members(self, clubs):
        first_names = [
            "Marco", "Giulia", "Alessandro", "Francesca", "Luca", "Sara",
            "Davide", "Chiara", "Stefano", "Elena", "Paolo", "Marta",
            "Antonio", "Valentina", "Simone", "Federica", "Riccardo", "Ilaria",
            "Giorgio", "Lucia", "Matteo", "Beatrice", "Giovanni", "Serena",
            "Nicolo", "Alessia", "Emanuele", "Silvia", "Daniele", "Arianna",
            "Andrea", "Ginevra",
        ]
        last_names = [
            "Rossi", "Bianchi", "Greco", "Russo", "Gallo", "Ferraro",
            "Vitale", "Colombo", "Costa", "Fontana", "Marino", "Giordano",
            "Serra", "Monti", "De Luca", "Rinaldi", "Caruso", "Ricci",
        ]
        professions = [
            "Ingegnere Gestionale",
            "Data Analyst",
            "Consulente Legale",
            "Medico Specialista",
            "Project Manager",
            "Responsabile Marketing",
            "Architetto",
            "Consulente Finanziario",
            "Imprenditore Sociale",
            "Ricercatore Biomedico",
            "Esperto di Sostenibilita'",
            "Docente Universitario",
            "HR Manager",
            "Esperto di Comunicazione",
            "Designer di Servizi",
            "Consulente ESG",
            "Responsabile Supply Chain",
            "Innovation Manager",
            "Psicologo del Lavoro",
            "Ingegnere Civile",
        ]
        sectors = [
            "Tecnologia", "Sanità", "Finanza", "Legale", "Marketing",
            "Formazione", "Infrastrutture", "Ricerca", "Sviluppo locale",
            "Energia", "Turismo", "Industria creativa", "Agroalimentare",
            "Logistica", "Pubblica amministrazione",
        ]
        locations = [
            "Milano, Italia",
            "Torino, Italia",
            "Genova, Italia",
            "Bologna, Italia",
            "Verona, Italia",
            "Venezia, Italia",
            "Firenze, Italia",
            "Pisa, Italia",
            "Perugia, Italia",
            "Roma, Italia",
            "Pescara, Italia",
            "Napoli, Italia",
            "Bari, Italia",
            "Lecce, Italia",
            "Cagliari, Italia",
            "Palermo, Italia",
            "Messina, Italia",
            "Cosenza, Italia",
            "Catanzaro, Italia",
            "Reggio Calabria, Italia",
            "Toronto, Canada",
            "New York, USA",
            "Berlino, Germania",
            "Londra, Regno Unito",
            "Zurigo, Svizzera",
        ]
        bios = [
            "<p>Professionista con esperienza internazionale e forte orientamento alla collaborazione.</p>",
            "<p>Mi occupo di progettazione e innovazione con focus su impatto sociale.</p>",
            "<p>Mentore per giovani talenti, appassionato di networking e scambi culturali.</p>",
            "<p>Specializzato in strategie data-driven e sviluppo di progetti complessi.</p>",
            "<p>Credo nel valore delle relazioni e nella crescita attraverso il dialogo.</p>",
            "<p>Coordino programmi di formazione e sviluppo di comunita' locali.</p>",
            "<p>Esperienza in project finance e modelli di governance sostenibile.</p>",
            "<p>Appassionato di tecnologia civica e collaborazione pubblico-privato.</p>",
            "<p>Promotore di iniziative culturali con ricaduta sui territori.</p>",
            "<p>Ho lavorato in startup e PMI, con focus su innovazione di processo.</p>",
            "<p>Consulente per strategie di comunicazione e public speaking.</p>",
            "<p>Supporto organizzazioni non profit nella definizione di KPI d'impatto.</p>",
        ]

        skills = list(Skill.objects.all())
        soft_skills = list(SoftSkill.objects.all())
        random.shuffle(skills)
        random.shuffle(soft_skills)

        members = []
        for idx in range(60):
            first_name = first_names[idx % len(first_names)]
            last_name = last_names[idx % len(last_names)]
            username = f"{slugify(first_name)}_{slugify(last_name)}_{idx + 1}"
            email = f"{username}@demo.rotary"
            club = random.choice(clubs)

            user = User.objects.create_user(
                username=username,
                email=email,
                password="demo12345",
                first_name=first_name,
                last_name=last_name,
                user_type=User.Types.NORMAL,
                profession=random.choice(professions),
                sector=random.choice(sectors),
                location=random.choice(locations),
                club=club,
                club_name=club.club_name,
                offers_mentoring=random.choice([True, False]),
                bio=random.choice(bios),
                languages=[
                    {"name": "Italiano", "proficiency": "Native"},
                    {"name": "Inglese", "proficiency": "Fluent"},
                ],
            )

            user.skills.set(random.sample(skills, k=random.randint(2, 4)))
            user.soft_skills.set(random.sample(soft_skills, k=random.randint(2, 4)))
            members.append(user)

        return members

    def _create_cards(self, clubs, members):
        sections = [
            ("storie-e-radici", "Racconti di ritorno alle origini"),
            ("scopri-la-calabria", "Itinerari autentici in Calabria"),
            ("scambi-e-mobilita", "Programmi di scambio e mobilità"),
            ("adotta-un-progetto", "Progetti da sostenere"),
            ("eccellenze-calabresi", "Eccellenze imprenditoriali"),
            ("calendario-delle-radici", "Eventi e calendario"),
        ]

        for idx, (section, title_seed) in enumerate(sections, start=1):
            author = random.choice(members)
            title = f"{title_seed} #{idx}"
            Card.objects.create(
                section=section,
                tab="presentazione",
                title=title,
                subtitle="Sintesi per presentazione con focus sui valori Rotary.",
                location=random.choice(["Cosenza", "Catanzaro", "Reggio Calabria", "Crotone"]),
                tags=["rotary", "calabria", "community"],
                content="<p>Contenuto demo con dettagli sull'iniziativa e invito alla partecipazione.</p>",
                date_type="single",
                date=timezone.now().date() + timedelta(days=idx * 3),
                author=author,
                is_published=True,
                infoElementValues=["Demo", "Presentazione", "Networking"],
            )

    def _create_forum_posts(self, members):
        topics = [
            {
                "title": "Innovazione nei club internazionali",
                "summary": "Esperienze e strumenti digitali per coordinare i service tra distretti.",
                "content": (
                    "<p>Negli ultimi mesi abbiamo sperimentato un modello di coordinamento tra club "
                    "basato su check-in mensili e dashboard condivise.</p>"
                    "<p>Il metodo ha ridotto i tempi di avvio dei service e migliorato la raccolta di volontari.</p>"
                ),
            },
            {
                "title": "Mentoring per giovani professionisti",
                "summary": "Programma pilota di mentorship con alumni e imprese locali.",
                "content": (
                    "<p>Abbiamo coinvolto 18 mentor e 32 mentee in un percorso di sei mesi con incontri tematici.</p>"
                    "<p>Le sessioni hanno coperto orientamento, networking e competenze trasversali.</p>"
                ),
            },
            {
                "title": "Collaborazioni tra club gemellati",
                "summary": "Best practice per attivare sinergie concrete in tempi brevi.",
                "content": (
                    "<p>Il gemellaggio ha portato alla co-progettazione di un evento formativo itinerante.</p>"
                    "<p>Stiamo raccogliendo proposte per il calendario 2025 con un format condiviso.</p>"
                ),
            },
            {
                "title": "Progetti di sostenibilita' locale",
                "summary": "Misurare l'impatto dei service sul territorio.",
                "content": (
                    "<p>Abbiamo definito KPI semplici (partecipazione, formazione, partnership) per monitorare i risultati.</p>"
                    "<p>I primi dati evidenziano un miglior coinvolgimento delle scuole superiori.</p>"
                ),
            },
            {
                "title": "Eventi culturali per la diaspora calabrese",
                "summary": "Connessioni tra community all'estero e club italiani.",
                "content": (
                    "<p>Le serate di networking hanno favorito il dialogo tra professionisti residenti in Italia e all'estero.</p>"
                    "<p>Stiamo valutando una piattaforma di matchmaking per progetti condivisi.</p>"
                ),
            },
            {
                "title": "Formazione digitale per i club",
                "summary": "Ciclo di workshop su strumenti collaborativi.",
                "content": (
                    "<p>Abbiamo organizzato tre sessioni su gestione documentale, meeting ibridi e community online.</p>"
                    "<p>Il feedback indica una maggiore efficacia nella comunicazione interna.</p>"
                ),
            },
            {
                "title": "Service su inclusione lavorativa",
                "summary": "Partnership con enti locali e aziende del territorio.",
                "content": (
                    "<p>Il progetto ha attivato percorsi di tirocinio per giovani NEET in tre province.</p>"
                    "<p>Stiamo estendendo il modello con nuovi tutor aziendali.</p>"
                ),
            },
            {
                "title": "Rigenerazione urbana e cultura",
                "summary": "Laboratori per riattivare spazi pubblici.",
                "content": (
                    "<p>Un percorso partecipativo ha coinvolto associazioni, studenti e artigiani.</p>"
                    "<p>Il risultato e' un calendario di eventi con sponsor locali.</p>"
                ),
            },
            {
                "title": "Progetto salute e prevenzione",
                "summary": "Iniziative territoriali con medici volontari.",
                "content": (
                    "<p>Abbiamo offerto screening gratuiti con un focus su prevenzione cardiovascolare.</p>"
                    "<p>Le adesioni sono state superiori alle aspettative, con 420 partecipanti.</p>"
                ),
            },
            {
                "title": "Rete di imprese sociali",
                "summary": "Condivisione di opportunita' e competenze manageriali.",
                "content": (
                    "<p>Le imprese coinvolte hanno definito un piano comune di formazione e procurement.</p>"
                    "<p>Prossimo passo: creare un fondo di micro-grant per progetti locali.</p>"
                ),
            },
            {
                "title": "Turismo delle radici e accoglienza",
                "summary": "Proposte per valorizzare le comunita' di origine.",
                "content": (
                    "<p>Stiamo mappando itinerari e servizi dedicati a chi rientra in Italia per motivi familiari.</p>"
                    "<p>Si lavora a un kit informativo multilingue per i club ospitanti.</p>"
                ),
            },
            {
                "title": "Scambi professionali tra distretti",
                "summary": "Format di scambio breve tra giovani professionisti.",
                "content": (
                    "<p>Il primo scambio ha coinvolto 12 partecipanti con visite aziendali e mentoring.</p>"
                    "<p>Il format prevede ora una piattaforma per candidature e report finale.</p>"
                ),
            },
        ]

        posts = []
        for idx, topic in enumerate(topics, start=1):
            author = random.choice(members)
            post = Post.objects.create(
                title=topic["title"],
                description=topic["summary"],
                content_html=(
                    f"{topic['content']}"
                    "<p>Nel prossimo incontro raccoglieremo nuove proposte e definiremo le priorita'.</p>"
                ),
                author=author,
            )
            posts.append(post)

        return posts

    def _create_forum_comments(self, posts, members):
        comment_texts = [
            "Ottima iniziativa, sarebbe utile coinvolgere anche i club gemellati.",
            "Condivido pienamente, possiamo replicare il modello in altri distretti.",
            "Mi interessa partecipare al prossimo incontro, resto disponibile.",
            "Suggerisco di aggiungere un momento formativo per i giovani rotariani.",
            "Possiamo integrare una survey per misurare l'impatto a sei mesi.",
            "Abbiamo una rete di volontari che potrebbe supportare la logistica.",
            "Propongo di coinvolgere universita' e incubatori locali.",
            "Disponibile a condividere materiali e template per la pianificazione.",
            "Serve un coordinamento con le amministrazioni locali, posso aiutare.",
            "Molto utile, potremmo allargare il target anche alle scuole tecniche.",
        ]

        for post in posts:
            top_level = []
            for _ in range(5):
                comment = Comment.objects.create(
                    post=post,
                    author=random.choice(members),
                    text=random.choice(comment_texts),
                )
                top_level.append(comment)

            for parent in top_level:
                Comment.objects.create(
                    post=post,
                    parent=parent,
                    author=random.choice(members),
                    text=(
                        "Grazie per il feedback, possiamo coordinarci nel gruppo dedicato "
                        "e definire una timeline condivisa."
                    ),
                )

    def _create_chats(self, clubs, members):
        random.shuffle(clubs)
        gemellaggi = [
            (clubs[0], clubs[1]),
            (clubs[2], clubs[3]),
        ]

        for club_a, club_b in gemellaggi:
            chat = Chat.create_group(
                name=f"Gemellaggio {club_a.club_name} - {club_b.club_name}",
                creator=club_a,
                description="Spazio di coordinamento per il gemellaggio.",
                chat_type="gemellaggio",
                club_ids=[club_a.id, club_b.id],
            )
            self._seed_messages(chat, [club_a, club_b], members)

        # Direct chats between members
        for member in members[:5]:
            peer = random.choice([m for m in members if m != member])
            chat = Chat.get_or_create_direct_chat(member, peer)
            self._seed_messages(chat, [member, peer], members)

        # General group chat
        group = Chat.create_group(
            name="Community Rota-Space",
            creator=random.choice(members),
            description="Canale generale per aggiornamenti e annunci.",
            chat_type="general_group",
            participant_ids=[m.id for m in random.sample(members, k=6)],
        )
        self._seed_messages(group, members, members)

    def _seed_messages(self, chat, participants, members):
        messages = [
            "Ciao a tutti, condividiamo lo stato del progetto?",
            "Abbiamo già raccolto le adesioni principali.",
            "Propongo un meeting la prossima settimana per definire le attività.",
            "Ottimo, prepariamo una timeline condivisa.",
        ]
        for idx in range(4):
            sender = random.choice(participants)
            Message.objects.create(
                chat=chat,
                sender=sender,
                body=messages[idx],
                created_at=timezone.now() - timedelta(days=4 - idx),
            )
