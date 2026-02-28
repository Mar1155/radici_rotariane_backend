from django.core.management.base import BaseCommand

from users.models import FocusArea


FOCUS_AREAS = [
    ("A", "Gestione di Progetti in generale"),
    ("A1", "Valutazione e monitoraggio"),
    ("A2", "Valutazione dei bisogni di Comunità"),
    ("A3", "Pianificazione di progetti sostenibili"),
    ("A4", "Pianificazione finanziaria e definizione dei per l'intero del Progetto (Life-cycle costing)"),
    ("A5", "Auditing"),
    ("A6", "Gestione delle Partnerships"),
    ("B", "Rotary Grants"),
    ("B1", "Processi di sviluppo di Rotary Grants e loro compilazione"),
    ("B2", "Ricerca e acquisizione di Partners Internazionali"),
    ("B3", "Fundraising"),
    ("B4", "Progetti Umanitari"),
    ("B5", "Borse di Studio"),
    ("B6", "Vocational Training Team (Teams di Formazione professionale)"),
    ("B7", "Inquadramento nella corretta Area Focus"),
    ("B8", "Qualificazione di Club"),
    ("C", "Alfabetizzazione ed Educazione di Base"),
    ("C1", "Formazione per i Docenti"),
    ("C2", "Allestimento di Centri tecnologici e Formazione relativa (laboratori informatici, lavagne interattive, classi attrezzate, tablets ecc.) associato a un'offerta comprensiva di formazione ai docenti per l'uso degli strumenti tecnologici"),
    ("C3", "Pianificazione e sviluppo del Curriculum"),
    ("C4", "Alfabetizzazione degli Adulti"),
    ("C5", "Alfabetizzazione delle ragazze"),
    ("C6", "Alfabetizzazione dei bambini"),
    ("C7", "Educazione per giovani fuori dal percorso scolastico e/o giovani di scarso rendimento"),
    ("C8", "Educazione dei disabili"),
    ("C9", "Programmi di doposcuola, tutoring e/o mentoring"),
    ("D", "Sviluppo Economico e comunitario"),
    ("D1", "Implementazione e gestione di Progetti in agricoltura, (locali/comunitari) per lo sviluppo di tecniche soprattutto per piccole aziende agricole."),
    ("D2", "Progettazione e implementazione di iniziative di Microcredito"),
    ("D3", "Impostazione e crescita di piccole imprese"),
    ("D4", "Sviluppo di attività economiche gestite da giovani"),
    ("D5", "Formazione professionale per l'impiego"),
    ("D6", "Sostegno e incentivazione all'impiego post scolastico"),
    ("D7", "Organizzazione Comunitaria (\"adotta un villaggio\")"),
    ("D8", "Infrastrutture Economiche e comunitarie di base"),
    ("D9", "Pari opportunità di genere per lo sviluppo economico e sociale"),
    ("E", "Prevenzione e cura delle malattie"),
    ("E1", "Controllo delle malattie trasmissibili ed infettive"),
    ("E2", "Prevenzione, trattamento e gestione di malattie non trasmissibili"),
    ("E3", "Attrezzature e tecnologie sanitarie ambulatoriali/ospedaliere"),
    ("E4", "Attrezzature e tecnologie sanitarie mobili"),
    ("E5", "Cure Primarie"),
    ("E6", "Disabilità fisiche, Riabilitazione e terapia fisica"),
    ("E7", "Salute mentale, Prevenzione del suicidio, Abuso di sostanze, depressione e disturbi affini"),
    ("E8", "Chirurgia d'Urgenza"),
    ("E9", "Chirurgia per malformazioni congenite"),
    ("E10", "Prevenzione e trattamento orale/dentale"),
    ("E11", "Hospice e Cure Palliative"),
    ("E12", "Formazione per operatori sanitari inclusi medici, infermieri, tecnici e operatori sul campo"),
    ("F", "Salute Materno Infantile"),
    ("F1", "Cure materne, pre e post natali"),
    ("F2", "Servizi per il travaglio e il parto"),
    ("F3", "Formazione per infermiere e ostetriche"),
    ("F4", "Cure neonatali"),
    ("F5", "Assistenza sanitaria per bambini inferiori ai 5 anni di età."),
    ("F6", "Nutrizione clinica"),
    ("F7", "Prevenzione e trattamento di malattie non trasmissibili"),
    ("F8", "Salute della sessualità e della riproduzione"),
    ("G", "Acqua e strutture Igienico-sanitarie"),
    ("G1", "Fornitura di acqua (sistemi di alimentazione a gravità, tubazioni, serbatoi, pozzi, raccolta di acqua piovana, dighe e argini ecc.)"),
    ("G2", "Gestione delle acque e dei bacini"),
    ("G3", "Trattamento e analisi della qualità dell'acqua (bio sabbia, ceramica, osmosi inversa, filtri Sawyer, trattamenti per le acque reflue, ecc.)"),
    ("G4", "Irrigazione"),
    ("G5", "Educazione all'igiene a corretti stili di vita"),
    ("G6", "Gestione ed educazione all'igiene mestruale"),
    ("G7", "Gestione dei rifiuti solidi (immondizia)"),
    ("G8", "Costruzione e riparazione di latrine (fosse biologiche, smaltimento ecologico dei rifiuti, deflusso delle toilettes, latrina a fossa ventilata, ecc.)"),
    ("G9", "Gestione di altri rifiuti (non immondizia)"),
    ("G10", "Gestione delle acque di scarico (acque grigie)"),
    ("G11", "WASH nelle scuole"),
    ("G12", "WASH sostegno e patrocinio"),
    ("H", "Pace e prevenzione/risoluzione dei conflitti"),
    ("H1", "Attività di mediazione nella Comunità"),
    ("H2", "Attività con i giovani volta a contrastare la violenza ed incentivare la leadership (specialmente nei gruppi di giovani ad alto rischio)"),
    ("H3", "Iniziative anti-gang"),
    ("H4", "Opera di riconciliazione post conflitto (su base comunitaria)"),
    ("H5", "Rifugiati (si potrebbero richiedere competenze formative)"),
    ("H6", "Attività su problemi transfrontalieri"),
    ("H7", "Interventi di ricostruzione sociale e istituzionale"),
    ("H8", "Educazione e formazione alla non violenza"),
    ("H9", "Contrasto al bullismo."),
]


class Command(BaseCommand):
    help = "Popola le FocusArea DRN senza duplicati."

    def add_arguments(self, parser):
        parser.add_argument(
            "--overwrite-translations",
            action="store_true",
            help="Sovrascrive la traduzione italiana esistente.",
        )

    def handle(self, *args, **options):
        overwrite = options["overwrite_translations"]
        created_count = 0
        updated_count = 0
        renamed_count = 0

        for code, title in FOCUS_AREAS:
            full_label = f"{code} {title}".strip()
            canonical_name = title

            obj = (
                FocusArea.objects.filter(translations__code=code).order_by("id").first()
                or FocusArea.objects.filter(name=canonical_name).order_by("id").first()
                or FocusArea.objects.filter(name=full_label).order_by("id").first()
                or FocusArea.objects.filter(name=code).order_by("id").first()
            )
            created = False

            if not obj:
                obj = FocusArea.objects.create(name=canonical_name)
                created = True
            elif obj.name != canonical_name and not FocusArea.objects.filter(name=canonical_name).exclude(pk=obj.pk).exists():
                obj.name = canonical_name
                obj.save(update_fields=["name"])
                renamed_count += 1

            translations = dict(obj.translations or {})
            if overwrite or not translations.get("it") or not translations.get("code"):
                translations["it"] = title
                translations["code"] = code
                translations["macro_code"] = code[0]
                translations["is_macro"] = len(code) == 1
                obj.translations = translations
                obj.save(update_fields=["translations"])
                if not created:
                    updated_count += 1

            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Seed focus areas completato: "
                f"create={created_count}, rinominate={renamed_count}, "
                f"aggiornate={updated_count}, totale={len(FOCUS_AREAS)}."
            )
        )
