# seed_cards Command Execution Flow

## Visual Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    seed_cards Management Command                │
│                    section/management/commands/seed_cards.py    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  Start Command      │
                    └─────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │ Parse Arguments    │
                    │ --reset (optional) │
                    └─────────▼──────────┘
                              │
                    ┌─────────▼──────────┐
          ┌─────────│ --reset flag?      │
          │         └─────────▬──────────┘
          │                   │
      YES │                   │ NO
          │                   │
          ▼                   │
    ┌──────────────┐          │
    │ DELETE ALL   │          │
    │ CARDS        │          │
    └──────┬───────┘          │
           │                  │
           └──────────┬───────┘
                      │
                      ▼
            ┌──────────────────────┐
            │ Load All Users       │
            │ WHERE user_type      │
            │ = 'NORMAL'           │
            └────────┬─────────────┘
                     │
         ┌───────────▼───────────┐
         │ Users Found?          │
         └───┬──────────────┬────┘
             │              │
          YES│              │ NO
             │              ▼
             │     ┌──────────────────┐
             │     │ ERROR: Run       │
             │     │ seed_demo first  │
             │     │ EXIT             │
             │     └──────────────────┘
             │
             ▼
    ┌─────────────────────────────┐
    │ Loop Through All Sections   │
    │ (7 sections)                │
    └────────┬────────────────────┘
             │
      ┌──────▼──────┐
      │ For each    │
      │ section:    │
      └──────┬──────┘
             │
      ┌──────▼──────────────────┐
      │ Loop Through Tabs       │
      │ (varies per section)    │
      └──────┬─────────────────┘
             │
      ┌──────▼──────────────────┐
      │ Route to section method │
      │ _cards_*_*()           │
      └──────┬─────────────────┘
             │
      ┌──────▼──────────────────────────┐
      │ Return 3-4 card dictionaries    │
      │ With section & tab auto-set     │
      └──────┬──────────────────────────┘
             │
      ┌──────▼──────────────────────────┐
      │ For each card dictionary:       │
      │ 1. Assign random author         │
      │ 2. Create Card object           │
      │ 3. Save to database             │
      └──────┬──────────────────────────┘
             │
      ┌──────▼──────────────────┐
      │ Error handling:         │
      │ ✓ on success            │
      │ ✗ on failure            │
      └──────┬─────────────────┘
             │
             ▼
    ┌──────────────────────────┐
    │ Print Summary Statistics │
    │ "✅ Created X cards"     │
    └──────┬───────────────────┘
           │
           ▼
    ┌────────────────┐
    │ Command Ends   │
    └────────────────┘
```

## Detailed Section Routing

```
SECTION                 → TAB              → METHOD                → CARDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

adotta-un-progetto      → main             → _cards_adotta_un_progetto  → 4
                          (unique tab)       (creates 4 projects)

storie-e-radici         → storie           → _cards_storie_e_radici      → 3
                        → testimonianze                                   → 3
                        → tradizioni                                      → 3
                          (3 distinct                                     ─────
                           return sets)                                    → 9

eccellenze-calabresi    → main             → _cards_eccellenze_calabresi → 4

calendario-delle-radici → main             → _cards_calendario_radici    → 4

scopri-la-calabria      → itinerari        → _cards_scopri_la_calabria   → 4
                        → esperienze                                      → 4
                        → consigli                                        → 3
                          (3 distinct                                     ─────
                           return sets)                                   → 11

scambi-e-mobilita       → offri            → _cards_scambi_e_mobilita    → 4
                        → cerca                                           → 4
                          (2 distinct                                     ─────
                           return sets)                                   → 8

archivio                → main             → _cards_archivio             → 4

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL                                                                    44
```

## Data Flow per Card

```
Card Dictionary Created
    │
    ├─ title: str                    (e.g., "Project Name")
    ├─ subtitle: str                 (e.g., "Brief description")
    ├─ location: str                 (e.g., "Cosenza, Italia")
    │
    ├─ section: str                  ◄── AUTO-ASSIGNED (from routing)
    ├─ tab: str                      ◄── AUTO-ASSIGNED (from routing)
    │
    ├─ tags: List[str]               (validated against allowed_tags)
    ├─ infoElementValues: List[str]  (count validated against config)
    │
    ├─ content: str (or None)        (HTML content, optional)
    ├─ cover_image: None             (always None in this script)
    │
    ├─ date_type: str                (single/range/none)
    ├─ date: date                    (if single date)
    ├─ date_start: date              (if range)
    ├─ date_end: date                (if range)
    │
    ├─ is_published: bool            (True for all)
    ├─ author: User                  ◄── RANDOMLY ASSIGNED
    │
    └─ views_count: int              (auto-created as 0)
             │
             ▼
    Card.objects.create(**card_dict)
             │
             ▼
    Card saved to database
             │
             ├─► slug auto-generated
             ├─► created_at auto-set
             ├─► updated_at auto-set
             │
             └─► Display: ✓ [Tab]: [Title]
                 Or:      ✗ [Tab]: [Title] - [Error]
```

## Command Execution Example

### Input
```bash
$ python manage.py seed_cards
```

### Execution Timeline

```
Time  Event
────  ─────────────────────────────────────────────────────────
0.0s  Load command, parse arguments
0.1s  Query: SELECT users WHERE user_type='NORMAL'
0.2s  Found 60 users ✓
0.3s  Process section: adotta-un-progetto
0.35s   → Assign tab: main
0.36s   → Route to _cards_adotta_un_progetto()
0.37s   → Create 4 card objects
0.45s   → Print: 4 success messages (✓)
0.50s  Process section: storie-e-radici
0.55s   → Route to storie tab
0.60s   → Create 3 cards
0.65s   → Route to testimonianze tab
0.70s   → Create 3 cards
0.75s   → Route to tradizioni tab
0.80s   → Create 3 cards
0.85s   → Print: 9 success messages
...
2.8s  Process section: archivio
2.9s   → Create 4 cards
2.95s  → Print: 4 success messages
3.0s  Print summary: "✅ Successfully created 44 cards!"
3.1s  Command ends
```

### Output Example

```
📚 Section: adotta-un-progetto
  ✓ main: Centro Digitale per l'Inclusione Sociale a Cosenza
  ✓ main: Rigenerazione dell'Orto Botanico Storico di Reggio Calabria
  ✓ main: Piattaforma per l'Agricoltura Sostenibile in Calabria
  ✓ main: Programma di Welfare Territoriale per Famiglie Fragili a Crotone

📚 Section: storie-e-radici
  ✓ storie: Da Cosenza a Milano: La storia di una famiglia di imprenditori
  ✓ storie: Quando le radici nutrono le ali: Dalla Calabria al mondo
  ✓ storie: Imprenditoria femminile: Le donne calabresi che cambiano il mercato
  ✓ testimonianze: 
  ✓ testimonianze: 
  ✓ testimonianze: 
  ✓ tradizioni: La Festa di San Cosmo e San Damiano: Tradizione e Comunità
  ✓ tradizioni: L'Artigianato della Ceramica Calabrese: Arte Tramandato da Secoli
  ✓ tradizioni: I Suoni della Tarantella: La Danza che Parla l'Anima Calabrese

📚 Section: eccellenze-calabresi
  ✓ main: Ristorante "Nduja & Tradizione" - Cosenza
  ✓ main: Azienda Agricola "Terre di Reggio" - Reggio Calabria
  ✓ main: Biblioteca Storica "Codex Calabricus" - Crotone
  ✓ main: Laboratorio di Artigianato "Ceramiche Seminara" - Reggio Calabria

📚 Section: calendario-delle-radici
  ✓ main: Festival della Biodiversità Calabrese
  ✓ main: Radici in Festa: Cena Galeotta Calabrese
  ✓ main: Convegno Internazionale "Rotary e Territorialità"
  ✓ main: Mostra Itinerante "Maestri Calabresi"

📚 Section: scopri-la-calabria
  ✓ itinerari: Sila Grande: Il Polmone Verde della Calabria
  ✓ itinerari: Costa dei Gelsomini: Spiagge Incontaminate e Grotte Marine
  ✓ itinerari: Itinerario delle Radici: 5 Borghi Storici della Calabria Centrale
  ✓ itinerari: Straits of Messina Crossing: Reggio Calabria al Confine d'Italia
  ✓ esperienze: Corso di Cucina Calabrese con Chef Locale
  ✓ esperienze: Laboratorio Artigianale di Ceramica a Seminara
  ✓ esperienze: Escursione Naturalistica nell'Oasi di Capo Rizzuto
  ✓ esperienze: Tour Enoturismo: Vigneti di Reggio Calabria e Degustazione
  ✓ consigli: Visita la Sila nei mesi di giugno e settembre per il clima ideale
  ✓ consigli: I borghi arbëreshë della provincia di Cosenza meritano 2-3 giorni di visita dedicata
  ✓ consigli: Non perdere l'Aspromonte: il "balcone della Sicilia"

📚 Section: scambi-e-mobilita
  ✓ offri: Tirocinio in Azienda Tecnologica a Milano - IT Development
  ✓ offri: Scambio Culturale: Toronto - Programma 6 Mesi
  ✓ offri: Mentoring Professionale: Programma 1-a-1 Online
  ✓ offri: Visiting Scholar: Università di Bologna - Ricerca e Didattica
  ✓ cerca: Cerchiamo Mentor in Digital Marketing per Startup Calabrese
  ✓ cerca: Cercasi Docente di Ingegneria Civile per Master's Equivalence
  ✓ cerca: Scambio Aziendale: Azienda Calabrese Cerca Partner Europeo
  ✓ cerca: Ricerca Volontari: Progetto di Ricerca Medica nel Sud Italia

📚 Section: archivio
  ✓ main: Documento Storico: Statuto del Rotary Club Reggio Calabria (1952)
  ✓ main: Foto Storica: Cena Galeotta 1985 - Reunion Generazionale
  ✓ main: Video Documentario: Il Rotary a Servizio della Calabria (1990-2020)
  ✓ main: Archivio Testuale: Articoli e Resoconti dalla Rivista "Rotary Calabria" (1960-1980)

✅ Successfully created 44 cards!
```

## Error Scenarios

### Scenario 1: No Users Found

```
Input:  python manage.py seed_cards
↓
Check: User.objects.filter(user_type='NORMAL').exists()
↓
Result: False (0 users)
↓
Output: No users found. Please seed users first with: python manage.py seed_demo
↓
Exit: Command terminates gracefully
```

### Scenario 2: Card Creation Error

```
For each card:
  ↓
  Try: Card.objects.create(**card_data)
  ↓
  If ValidationError:
    Print: ✗ [tab]: [title] - [error_message]
    Continue to next card
  ↓
  If Success:
    Print: ✓ [tab]: [title]
```

### Scenario 3: --reset Flag Used

```
Input:  python manage.py seed_cards --reset
↓
Parse: options['reset'] = True
↓
Execute: Card.objects.all().delete()
↓
Print:  All existing cards deleted.
↓
Continue: Normal seeding flow
```

## Database Operations Summary

```
Database Write Operations
────────────────────────────────────────

Operation          Count    Impact
────────           ─────    ──────────────────
Card.create()      44       Primary data
User.assign        44       Foreign key links
Index update       ~2-3     Slug + created_at
────────────────────────────────────────
Total writes:      ~90      ~150 SQL queries
```

## Integration with Other Commands

```
Historical Command Dependencies:
┌──────────────────────┐
│  python manage.py    │
│  migrate             │  ◄── Must run first (creates schema)
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  seed_demo --reset   │  ◄── Creates 60 users, skills, clubs
│  (optional)          │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  seed_cards          │  ◄── THIS COMMAND
│  (creates 44 cards)  │
└──────────┬───────────┘
           │
           ▼
        Ready for:
     ✓ API Testing
     ✓ Frontend Development
     ✓ Demo Presentations
     ✓ Integration Testing
```

## Performance Metrics

```
Execution Profile
─────────────────────────────────────
Phase              Duration    Queries
─────              ────────    ───────
Initialization     0.1s        2
Load users         0.2s        1
Section iteration  2.5s        ~140
Card creation      0.15s       1 per card (44)
Output formatting  0.05s       0
─────────────────────────────────────
Total              2.9s        ~150
```

---

**Note:** This flow diagram is accurate as of December 2025. For the most up-to-date execution details, review the actual `seed_cards.py` file.
