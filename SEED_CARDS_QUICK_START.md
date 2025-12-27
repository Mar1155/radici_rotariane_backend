# Quick Start Guide - seed_cards

## TL;DR

```bash
# Step 1: Create demo users (one time)
python manage.py seed_demo --reset

# Step 2: Seed all cards
python manage.py seed_cards

# Optional: Reset and reseed
python manage.py seed_cards --reset
```

## What Gets Created

✅ **44 cards** across 7 sections:

| Section | Tabs | Cards | Focus |
|---------|------|-------|-------|
| 🎯 Adotta un Progetto | 1 | 4 | Community projects seeking support |
| 📖 Storie e Radici | 3 | 10 | Personal stories, traditions, testimonials |
| 🏆 Eccellenze Calabresi | 1 | 4 | Business partnerships & discounts |
| 📅 Calendario Radici | 1 | 4 | Events & celebrations |
| 🗺️ Scopri la Calabria | 3 | 11 | Itineraries, experiences, travel tips |
| 🔄 Scambi e Mobilità | 2 | 8 | Exchanges, internships, mentoring |
| 📚 Archivio | 1 | 4 | Historical documents & media |

## Key Features

🎨 **Authentic Content**
- All text in Italian
- Focused on Calabrian culture and Rotary values
- Coherent narratives per section

✨ **Smart Data**
- Auto-assigned random authors from demo users
- Correct info element values (pricing, capacity, dates)
- Proper tag assignments respecting configuration

🔗 **Fully Integrated**
- Respects structure configuration
- Validates tags per section/tab
- Matches frontend `sections.structure.ts` exactly

## Testing the Data

```bash
# Enter Django shell
python manage.py shell

# Check created cards
from section.models import Card
Card.objects.count()  # Should be 44

# See cards by section
from django.db.models import Count
Card.objects.values('section').annotate(count=Count('id'))

# Inspect a specific card
card = Card.objects.first()
print(f"{card.title}")
print(f"Section: {card.section}, Tab: {card.tab}")
print(f"Info Elements: {card.infoElementValues}")
print(f"Tags: {card.tags}")
```

## File Locations

```
section/
├── management/
│   ├── __init__.py
│   └── commands/
│       ├── __init__.py
│       └── seed_cards.py          # 👈 Main script
└── models.py

📄 SEED_CARDS_DOCUMENTATION.md     # 👈 Full documentation
```

## Common Tasks

### Add a new card
Edit the relevant `_cards_*_*` method in `seed_cards.py`

### Reset all cards (keep in DB)
```bash
python manage.py shell
>>> from section.models import Card
>>> Card.objects.all().delete()
```

### Reseed with fresh data
```bash
python manage.py seed_cards --reset
```

### Check specific section
```bash
python manage.py shell
>>> from section.models import Card
>>> cards = Card.objects.filter(section='scopri-la-calabria', tab='esperienze')
>>> cards.count()  # Show count
>>> [c.title for c in cards]  # Show titles
```

## Output Example

```
📚 Section: adotta-un-progetto
  ✓ main: Centro Digitale per l'Inclusione Sociale a Cosenza
  ✓ main: Rigenerazione dell'Orto Botanico Storico di Reggio Calabria
  ✓ main: Piattaforma per l'Agricoltura Sostenibile in Calabria
  ✓ main: Programma di Welfare Territoriale per Famiglie Fragili a Crotone

📚 Section: storie-e-radici
  ✓ storie: Da Cosenza a Milano: La storia di una famiglia di imprenditori
  ✓ storie: Quando le radici nutrono le ali: Dalla Calabria al mondo
  ...

✅ Successfully created 44 cards!
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No users found" | Run `python manage.py seed_demo --reset` first |
| No output when running | Check Django settings are configured |
| Cards not in database | Verify migrations: `python manage.py migrate` |
| Wrong info elements | Check `structure.py` configuration matches |

---

For detailed documentation, see: **SEED_CARDS_DOCUMENTATION.md**
