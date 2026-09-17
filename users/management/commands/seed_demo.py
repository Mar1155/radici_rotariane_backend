import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from users.models import User, Skill, SoftSkill

# Password unica per tutti gli account di prova, stampata a fine esecuzione.
PASSWORD_DEMO = "demo12345"
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
        admin = self._crea_admin()
        redattore = self._crea_redattore()
        clubs = self._create_clubs()
        members = self._create_members(clubs)
        self._verifica_email(clubs + members + [admin, redattore])
        self._create_cards(clubs, members)
        posts = self._create_forum_posts(members)
        self._create_forum_comments(posts, members)
        self._create_chats(clubs, members)

        self._stampa_accessi(clubs, members)

    def _crea_admin(self):
        """Un amministratore di prova, distinto dal superuser gia' presente.

        Serve perche' alcuni tipi di articolo si pubblicano solo da admin, e
        perche' senza email verificata il login del frontend rifiuta anche un
        superuser: il pannello Wagtail funziona, il sito no.
        """
        admin, _ = User.objects.get_or_create(
            email="admin@demo.rotary",
            defaults={"username": "admin_demo", "first_name": "Admin",
                      "last_name": "Demo"},
        )
        admin.is_staff = True
        admin.is_superuser = True
        admin.is_active = True
        admin.set_password(PASSWORD_DEMO)
        admin.save()
        return admin

    def _crea_redattore(self):
        """L'account con cui il cliente compone le pagine.

        Sta nel gruppo Redazione e **non** e' superuser: e' cio' che rende
        verificabile la separazione. Vede pagine e immagini, non i tipi di
        articolo, che restano a chi sviluppa.
        """
        from django.contrib.auth.models import Group

        redattore, _ = User.objects.get_or_create(
            email="redazione@demo.rotary",
            defaults={"username": "redazione_demo", "first_name": "Redazione",
                      "last_name": "Demo"},
        )
        redattore.is_staff = True        # serve per entrare in /cms/
        redattore.is_superuser = False
        redattore.is_active = True
        redattore.set_password(PASSWORD_DEMO)
        redattore.save()

        gruppo = Group.objects.filter(name="Redazione").first()
        if gruppo:
            redattore.groups.add(gruppo)
        else:
            self.stdout.write(self.style.WARNING(
                "  gruppo Redazione assente: esegui `build_site`"))
        return redattore

    def _verifica_email(self, utenti):
        """Segna verificate le email di prova.

        Senza questo il login rifiuta: i dati esistono ma nessuno puo' entrare,
        e per provare la webapp bisognerebbe passare dalla registrazione vera.
        """
        adesso = timezone.now()
        User.objects.filter(pk__in=[u.pk for u in utenti],
                            email_verified_at__isnull=True).update(email_verified_at=adesso)

    def _stampa_accessi(self, clubs, members):
        socio = members[0] if members else None
        club = clubs[0] if clubs else None
        righe = [
            "",
            f"Dati di prova pronti: {len(clubs)} club, {len(members)} soci, "
            f"{Card.objects.count()} articoli.",
            "",
            f"Accessi (password: {PASSWORD_DEMO})",
        ]
        if socio:
            righe.append(f"  socio  {socio.email}  ({socio.get_full_name()})")
        if club:
            righe.append(f"  club   {club.email}  ({club.club_name})")
        righe.append("  admin  admin@demo.rotary")
        righe.append("  cms    redazione@demo.rotary  (compone le pagine su /cms/)")
        righe.append("")
        righe.append("Tutti gli altri account di prova usano la stessa password.")
        righe.append("Gli stessi dati sono in ACCESSI-DEMO.md.")
        self.stdout.write(self.style.SUCCESS("\n".join(righe)))

    def _reset_data(self):
        Message.objects.all().delete()
        Chat.objects.all().delete()
        Comment.objects.all().delete()
        Post.objects.all().delete()
        Card.objects.all().delete()
        User.objects.exclude(is_superuser=True).delete()

    def _unique_rotary_id(self, prefix: str, start: int = 1) -> str:
        """Generate a unique rotary_id with the given prefix and numeric suffix."""
        counter = start
        while True:
            candidate = f"{prefix}-{counter:04d}"
            if not User.objects.filter(rotary_id=candidate).exists():
                return candidate
            counter += 1

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
                "club_president": "Lorenzo Bernardi",
                "club_city": "Milano",
                "club_country": "Italia",
                "club_district": "2042",
                "club_latitude": 45.4642,
                "club_longitude": 9.1900,
                "bio": "<p>Club attivo su progetti di inclusione lavorativa e innovazione urbana.</p>",
            },
            {
                "club_name": "Rotary Club Torino Valentino",
                "club_president": "Gianni Ferri",
                "club_city": "Torino",
                "club_country": "Italia",
                "club_district": "2032",
                "club_latitude": 45.0703,
                "club_longitude": 7.6869,
                "bio": "<p>Promuove programmi STEM per scuole superiori e mentoring professionale.</p>",
            },
            {
                "club_name": "Rotary Club Genova Porto Antico",
                "club_president": "Marco De Santis",
                "club_city": "Genova",
                "club_country": "Italia",
                "club_district": "2032",
                "club_latitude": 44.4056,
                "club_longitude": 8.9463,
                "bio": "<p>Focus su rigenerazione urbana e cultura marittima.</p>",
            },
            {
                "club_name": "Rotary Club Bologna Galvani",
                "club_president": "Paola Rinaldi",
                "club_city": "Bologna",
                "club_country": "Italia",
                "club_district": "2072",
                "club_latitude": 44.4949,
                "club_longitude": 11.3426,
                "bio": "<p>Attivo in progetti di formazione universitaria e ricerca applicata.</p>",
            },
            {
                "club_name": "Rotary Club Verona Arena",
                "club_president": "Luca Monti",
                "club_city": "Verona",
                "club_country": "Italia",
                "club_district": "2060",
                "club_latitude": 45.4384,
                "club_longitude": 10.9916,
                "bio": "<p>Iniziative culturali e sostegno a imprese creative.</p>",
            },
            {
                "club_name": "Rotary Club Venezia Laguna",
                "club_president": "Chiara Bellini",
                "club_city": "Venezia",
                "club_country": "Italia",
                "club_district": "2060",
                "club_latitude": 45.4408,
                "club_longitude": 12.3155,
                "bio": "<p>Progetti ambientali e tutela del patrimonio storico.</p>",
            },
            {
                "club_name": "Rotary Club Firenze Brunelleschi",
                "club_president": "Alessandro Moretti",
                "club_city": "Firenze",
                "club_country": "Italia",
                "club_district": "2071",
                "club_latitude": 43.7696,
                "club_longitude": 11.2558,
                "bio": "<p>Laboratori su turismo sostenibile e valorizzazione culturale.</p>",
            },
            {
                "club_name": "Rotary Club Pisa Galilei",
                "club_president": "Federica Conti",
                "club_city": "Pisa",
                "club_country": "Italia",
                "club_district": "2071",
                "club_latitude": 43.7228,
                "club_longitude": 10.4017,
                "bio": "<p>Collaborazioni con universita' e centri di ricerca.</p>",
            },
            {
                "club_name": "Rotary Club Perugia Etrusca",
                "club_president": "Matteo Guidi",
                "club_city": "Perugia",
                "club_country": "Italia",
                "club_district": "2090",
                "club_latitude": 43.1107,
                "club_longitude": 12.3908,
                "bio": "<p>Progetti di educazione civica e cittadinanza attiva.</p>",
            },
            {
                "club_name": "Rotary Club Roma Foro",
                "club_president": "Francesca Gatti",
                "club_city": "Roma",
                "club_country": "Italia",
                "club_district": "2080",
                "club_latitude": 41.9028,
                "club_longitude": 12.4964,
                "bio": "<p>Programmi di sostegno a start-up sociali e progetti intergenerazionali.</p>",
            },
            {
                "club_name": "Rotary Club Pescara Adriatica",
                "club_president": "Riccardo Bassi",
                "club_city": "Pescara",
                "club_country": "Italia",
                "club_district": "2090",
                "club_latitude": 42.4618,
                "club_longitude": 14.2161,
                "bio": "<p>Iniziative sulla blue economy e formazione professionale.</p>",
            },
            {
                "club_name": "Rotary Club Napoli Partenope",
                "club_president": "Giulia Romano",
                "club_city": "Napoli",
                "club_country": "Italia",
                "club_district": "2101",
                "club_latitude": 40.8518,
                "club_longitude": 14.2681,
                "bio": "<p>Progetti su inclusione sociale e rigenerazione di quartieri storici.</p>",
            },
            {
                "club_name": "Rotary Club Bari Levante",
                "club_president": "Andrea Leone",
                "club_city": "Bari",
                "club_country": "Italia",
                "club_district": "2120",
                "club_latitude": 41.1171,
                "club_longitude": 16.8719,
                "bio": "<p>Network per l'imprenditoria giovanile e scambi professionali.</p>",
            },
            {
                "club_name": "Rotary Club Lecce Barocco",
                "club_president": "Serena Caruso",
                "club_city": "Lecce",
                "club_country": "Italia",
                "club_district": "2120",
                "club_latitude": 40.3529,
                "club_longitude": 18.1743,
                "bio": "<p>Progetti culturali con focus su artigianato e innovazione.</p>",
            },
            {
                "club_name": "Rotary Club Cagliari Castello",
                "club_president": "Paolo Serra",
                "club_city": "Cagliari",
                "club_country": "Italia",
                "club_district": "2080",
                "club_latitude": 39.2238,
                "club_longitude": 9.1217,
                "bio": "<p>Programmi di welfare territoriale e sostegno alle famiglie.</p>",
            },
            {
                "club_name": "Rotary Club Palermo Normanna",
                "club_president": "Giorgio Vitale",
                "club_city": "Palermo",
                "club_country": "Italia",
                "club_district": "2110",
                "club_latitude": 38.1157,
                "club_longitude": 13.3615,
                "bio": "<p>Progetti su legalita' e promozione della cultura civica.</p>",
            },
            {
                "club_name": "Rotary Club Messina Peloro",
                "club_president": "Elena Greco",
                "club_city": "Messina",
                "club_country": "Italia",
                "club_district": "2110",
                "club_latitude": 38.1938,
                "club_longitude": 15.5540,
                "bio": "<p>Attivo su mobilita' sostenibile e azioni di protezione civile.</p>",
            },
            {
                "club_name": "Rotary Club Cosenza",
                "club_president": "Antonio Russo",
                "club_city": "Cosenza",
                "club_country": "Italia",
                "club_district": "2102",
                "club_latitude": 39.2983,
                "club_longitude": 16.2536,
                "bio": "<p>Club storico con focus su innovazione sociale e mentoring giovanile.</p>",
            },
            {
                "club_name": "Rotary Club Reggio Calabria",
                "club_president": "Valentina Costa",
                "club_city": "Reggio Calabria",
                "club_country": "Italia",
                "club_district": "2102",
                "club_latitude": 38.1112,
                "club_longitude": 15.6473,
                "bio": "<p>Impegnato in progetti di cooperazione internazionale e gemellaggi.</p>",
            },
            {
                "club_name": "Rotary Club Catanzaro",
                "club_president": "Simone Gallo",
                "club_city": "Catanzaro",
                "club_country": "Italia",
                "club_district": "2102",
                "club_latitude": 38.9097,
                "club_longitude": 16.5877,
                "bio": "<p>Promuove iniziative culturali e scambi professionali.</p>",
            },
            {
                "club_name": "Rotary Club Lamezia Terme",
                "club_president": "Marta Ferraro",
                "club_city": "Lamezia Terme",
                "club_country": "Italia",
                "club_district": "2102",
                "club_latitude": 38.9667,
                "club_longitude": 16.3167,
                "bio": "<p>Specializzato in progetti di formazione e sviluppo locale.</p>",
            },
            {
                "club_name": "Rotary Club Toronto Calabria",
                "club_president": "Giovanni Marino",
                "club_city": "Toronto",
                "club_country": "Canada",
                "club_district": "7070",
                "club_latitude": 43.6532,
                "club_longitude": -79.3832,
                "bio": "<p>Rotariani calabresi nel mondo con rete internazionale.</p>",
            },
            {
                "club_name": "Rotary Club New York Calabria",
                "club_president": "Sara Lombardi",
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
            rotary_id = self._unique_rotary_id("RID-CLUB", idx)
            president_name = data["club_president"].strip()
            pres_first, pres_last = (president_name.split(" ", 1) + [data["club_name"]])[:2]
            club, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "user_type": User.Types.CLUB,
                    "first_name": pres_first,
                    "last_name": pres_last,
                    "club_name": data["club_name"],
                    "club_president": data["club_president"],
                    "club_city": data["club_city"],
                    "club_country": data["club_country"],
                    "club_district": data["club_district"],
                    "club_latitude": data["club_latitude"],
                    "club_longitude": data["club_longitude"],
                    "bio": data["bio"],
                    "rotary_id": rotary_id,
                },
            )
            if not created:
                # Ensure rotary_id and name fields are populated for existing records
                if not club.rotary_id:
                    club.rotary_id = rotary_id
                if not club.first_name:
                    club.first_name = pres_first
                if not club.last_name:
                    club.last_name = pres_last
                club.email = club.email or email
            club.set_password(PASSWORD_DEMO)
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
            rotary_id = self._unique_rotary_id("RID-MEM", idx + 1)

            if User.objects.filter(username=username).exists():
                user = User.objects.get(username=username)
                if not user.rotary_id:
                    user.rotary_id = rotary_id
                    user.save(update_fields=["rotary_id"])
                members.append(user)
                continue

            user = User.objects.create_user(
                username=username,
                email=email,
                password=PASSWORD_DEMO,
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
                rotary_id=rotary_id,
            )

            user.skills.set(random.sample(skills, k=random.randint(2, 4)))
            user.soft_skills.set(random.sample(soft_skills, k=random.randint(2, 4)))
            members.append(user)

        return members

    # (titolo, sottotitolo, provincia) per ciascun tipo di articolo.
    # Il titolo vuoto e' voluto: `testimonianza` non ha il campo titolo.
    ARTICOLI = {
        "progetto": [
            ("Una biblioteca per il quartiere Sanita", "Un locale confiscato rimesso a nuovo e 4.000 volumi per i ragazzi del rione", "napoli"),
            ("Acqua potabile a Tambacounda", "Due pozzi e la formazione di sei manutentori locali, con il RC Dakar", "torino"),
            ("Borse di studio per giovani artigiani", "Dieci percorsi di bottega nella lavorazione del vetro", "venezia"),
            ("Ambulatorio mobile nelle aree interne", "Un mezzo attrezzato per sei comuni rimasti senza medico di base", "potenza"),
        ],
        "evento": [
            ("Assemblea distrettuale 2026", "Una giornata di lavori su azione internazionale e nuove generazioni", "bologna"),
            ("Serata di gala per il service idrico", "Cena di raccolta fondi con asta benefica", "milano"),
            ("Incontro con i club gemellati di Baviera", "Tre giorni di visite e tavoli di lavoro congiunti", "bolzano"),
            ("Forum sui giovani e il lavoro", "Imprenditori e studenti a confronto", "firenze"),
        ],
        "itinerario": [
            ("La Via Francigena da Lucca a Siena", "Sei tappe fra pievi, crete senesi e ospitalita rotariana", "siena"),
            ("I borghi del Pollino", "Anello di quattro giorni fra Basilicata e Calabria", "cosenza"),
            ("Barocco leccese in tre giorni", "Un percorso a piedi fra chiese, cortili e cave di tufo", "lecce"),
            ("Le Dolomiti di Brenta", "Cinque giorni di rifugi e ferrate storiche", "trento"),
        ],
        "esperienza": [
            ("Vendemmia nelle Langhe", "Una giornata in vigna e in cantina con un produttore socio del club", "cuneo"),
            ("Laboratorio di ceramica a Grottaglie", "Mezza giornata al tornio nel quartiere delle ceramiche", "taranto"),
            ("Pesca turismo a Cetara", "In mare all alba con i pescatori di alici", "salerno"),
            ("Cammino notturno sull Etna", "Salita guidata fino ai crateri sommitali", "catania"),
        ],
        "eccellenza": [
            ("Pasticceria Serafini", "Lievitati e dolci della tradizione, dal 1954", "perugia"),
            ("Hotel Torre del Parco", "Dimora storica del 1419 nel centro di Lecce", "lecce"),
            ("Cantine Vallebruna", "Vini biologici e visite guidate in cantina", "verona"),
            ("Sartoria Lo Verso", "Su misura e riparazioni sartoriali", "palermo"),
        ],
        "storia": [
            ("Mio nonno parti da Ellis Island", "La storia di una famiglia molisana fra due continenti", None),
            ("Ritorno a Castelmezzano dopo sessant anni", "Il viaggio di un socio australiano nel paese dei suoi genitori", None),
            ("La lettera trovata in soffitta", "Come un foglio del 1948 ha riunito due rami della stessa famiglia", None),
        ],
        "tradizione": [
            ("La Infiorata di Spello", "Come si preparano i tappeti di petali, quartiere per quartiere", None),
            ("Il pane di Altamura", "Impasto, lievito madre e forno a legna: una filiera che non e cambiata", None),
            ("La Sartiglia di Oristano", "La giostra equestre che apre il carnevale sardo", None),
        ],
        "testimonianza": [
            ("", "Sono tornata nel paese di mio padre dopo quarant anni e ho trovato la casa ancora in piedi", "campobasso"),
            ("", "Il gemellaggio con il club di Lione ci ha cambiato il modo di pensare i progetti", "genova"),
            ("", "Da studente ospite a socio: vent anni dopo ospito io i ragazzi", "padova"),
        ],
        "documento-archivio": [
            ("Verbale del gemellaggio con il RC Nizza, 1987", "Il documento originale firmato dai due presidenti", None),
            ("Fotografie del service alluvione 1994", "Quarantadue scatti dai giorni dell emergenza in Piemonte", None),
            ("Registro dei soci fondatori", "Riproduzione digitale del registro del 1949", None),
        ],
        "scambio-offerta": [
            ("Ospitalita a Trieste per l estate", "Appartamento con due camere a dieci minuti dal centro", "trieste"),
            ("Casa in campagna vicino ad Assisi", "Disponibile per famiglie rotariane in primavera", "perugia"),
            ("Posto barca e alloggio alla Maddalena", "Per chi arriva in Sardegna via mare", "sassari"),
        ],
        "scambio-richiesta": [
            ("Cerchiamo ospitalita in Baviera", "Due settimane per una famiglia di quattro persone", "brescia"),
            ("Studente in cerca di alloggio a Porto", "Semestre Erasmus, cerco famiglia ospitante", "bari"),
            ("Ospitalita a Buenos Aires", "Per un viaggio sulle tracce dei nonni emigrati", "roma"),
        ],
        "consiglio": [
            ("Casa Calabria International", "Il portale dei calabresi nel mondo", None),
            ("Portale del Turismo delle Radici", "Il sito del Ministero degli Esteri dedicato al turismo di ritorno", None),
        ],
    }

    CORPO = (
        "<p>{sottotitolo}</p>"
        "<p>Questo e un contenuto di prova, inserito per poter esplorare la "
        "piattaforma con le pagine gia popolate: mostra come si presenta un "
        "articolo completo, con la copertina, le informazioni laterali e i tag.</p>"
        "<p>I contenuti veri li inserisce chi amministra il sito, direttamente "
        "dalla piattaforma e senza passare da uno sviluppatore.</p>"
    )

    # Valori plausibili per gli elementi informativi, per chiave.
    VALORI_INFO = {
        "importo": ["12.000 euro", "4.500 euro", "30.000 euro", "8.200 euro"],
        "impatto": ["400 persone", "2 comuni", "60 studenti", "1 quartiere"],
        "scadenza": ["31/03/2026", "30/06/2026", "15/12/2026", "01/09/2026"],
        "giorni": ["6", "4", "3", "5"],
        "prezzo": ["45 euro", "Gratuito", "120 euro", "25 euro"],
        "sconto": ["-15%", "-20%", "-10%", "Omaggio"],
        "contattaci": ["info@esempio.it", "prenota@esempio.it", "ciao@esempio.it", "shop@esempio.it"],
        "posti_disponibili": ["4", "2", "6", "3"],
        "periodo_anno": ["Giugno - Agosto", "Primavera", "Tutto l anno", "Settembre"],
    }

    COLORI_COPERTINA = ["#17458f", "#009739", "#00a2e0", "#00adbb", "#ff7600",
                        "#d41367", "#7a6e66", "#657f99", "#f7a81b"]

    def _copertina(self, titolo, colore):
        """Una copertina generata: tinta piena con il titolo in basso."""
        from io import BytesIO
        from django.core.files.base import ContentFile
        from PIL import Image, ImageDraw

        larghezza, altezza = 1200, 675
        img = Image.new("RGB", (larghezza, altezza), colore)
        d = ImageDraw.Draw(img)
        d.rectangle([0, int(altezza * 0.72), larghezza, altezza], fill="#ffffff22")
        testo = (titolo or "Radici Rotariane")[:46]
        d.text((60, int(altezza * 0.80)), testo, fill="#ffffff")
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=82)
        return ContentFile(buf.getvalue(), name=f"{slugify(testo) or 'copertina'}.jpg")

    def _create_cards(self, clubs, members):
        """Articoli di prova, piu d uno per tipo.

        Il tipo dice quali campi esistono, quali tag sono ammessi e quali
        elementi informativi vanno compilati: il seed li legge da li invece di
        ripetere la stessa configurazione, cosi non puo produrre un articolo
        che il modello rifiuta.
        """
        from cms.models import ArticleType, GeoArea

        tipi = {t.key: t for t in
                ArticleType.objects.prefetch_related("allowed_tags", "info_elements")}
        if not tipi:
            self.stdout.write("  (nessun tipo di articolo: esegui prima seed_article_types)")
            return

        province = {g.key: g for g in GeoArea.objects.filter(level="province")}
        autori = (members or []) + (clubs or [])
        if not autori:
            return

        for chiave, righe in self.ARTICOLI.items():
            tipo = tipi.get(chiave)
            if tipo is None:
                continue

            attivi = set(tipo.active_fields or [])
            ammessi = [t.key for t in tipo.allowed_tags.all()]
            chiavi_info = [e.key for e in tipo.info_elements.all()]

            for i, (titolo, sottotitolo, prov) in enumerate(righe):
                slug = slugify(titolo or sottotitolo)[:60]
                if Card.objects.filter(slug=slug).exists():
                    continue

                area = province.get(prov) if (prov and tipo.uses_geo) else None
                card = Card(
                    slug=slug,
                    article_type=tipo,
                    author=autori[(hash(slug) % len(autori))],
                    is_published=True,
                    geo_area=area,
                    title=titolo if "title" in attivi else None,
                    subtitle=sottotitolo if "subtitle" in attivi else None,
                    content=(self.CORPO.format(sottotitolo=sottotitolo)
                             if "content" in attivi else None),
                    # `location` e il testo che si legge sulla card; `geo_area`
                    # e cio su cui filtra la ricerca. Servono entrambi.
                    location=(area.name if area else "Italia") if "location" in attivi else None,
                    tags=(random.sample(ammessi, k=min(len(ammessi), 2))
                          if ammessi and "tags" in attivi else []),
                    info_values={k: self._valore_info(k, i) for k in chiavi_info},
                    date_type="single" if "date" in attivi else "none",
                    date=(timezone.now().date() + timedelta(days=random.randint(-40, 90)))
                         if "date" in attivi else None,
                )
                if "coverImage" in attivi:
                    card.cover_image = self._copertina(
                        titolo or sottotitolo,
                        self.COLORI_COPERTINA[i % len(self.COLORI_COPERTINA)])

                card.validate_consistency()
                card.save()

    def _valore_info(self, chiave, i):
        scelte = self.VALORI_INFO.get(chiave)
        return scelte[i % len(scelte)] if scelte else "Da definire"

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
        # Su una copia: `shuffle` riordina sul posto, e la lista e' la stessa
        # che il chiamante usa dopo per stampare le credenziali. Mescolarla qui
        # faceva cambiare l'account documentato a ogni esecuzione.
        sorteggiati = list(clubs)
        random.shuffle(sorteggiati)
        gemellaggi = [
            (sorteggiati[0], sorteggiati[1]),
            (sorteggiati[2], sorteggiati[3]),
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
