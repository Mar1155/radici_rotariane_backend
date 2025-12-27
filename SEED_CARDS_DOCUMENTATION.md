# Card Seeding Script Documentation

## Overview

`seed_cards.py` is a Django management command that populates the database with comprehensive, realistic card data across all 7 sections and their respective tabs. The script creates **44 cards total** (3-4 per tab) with coherent, semantically relevant content that matches the structure configuration.

## Features

✨ **Comprehensive Coverage**
- All 7 sections fully seeded
- All tabs within each section populated
- 3-4 cards per tab for realistic data volume
- Total: 44 ready-to-use cards

🎯 **Smart Data Generation**
- Coherent, realistic content specific to each section/tab
- Appropriate info element values matching frontend configuration
- Correct tag assignments respecting allowed tags per tab
- Authentic Italian language content focused on Calabria and Rotary values

🔗 **Proper Relationships**
- Automatically assigns random users as authors (from seed_demo users)
- Respects all structure configuration constraints
- Validates data consistency

## Prerequisites

Before running `seed_cards`, you must:

1. **Run the demo seeding script first:**
   ```bash
   python manage.py seed_demo --reset
   ```
   This creates 60 users that will be assigned as card authors.

2. **Ensure the database is migrated:**
   ```bash
   python manage.py migrate
   ```

## Usage

### Basic Command

```bash
python manage.py seed_cards
```

This will create all 44 cards without deleting existing ones (cards will be appended).

### Reset and Reseed

```bash
python manage.py seed_cards --reset
```

This will:
1. Delete all existing cards
2. Create fresh ones with new random author assignments

## Section Breakdown

### 1. **Adotta un Progetto** (Adopt a Project)
- **Tab:** main
- **Cards:** 4
- **Content:** Real community projects needing support
- **Info Elements:** 
  - Importo (€150K-250K)
  - Impatto (Qualitative impact descriptions)
  - Scadenza (Project deadlines)
- **Example Cards:**
  - Digital Inclusion Center in Cosenza
  - Historic Botanical Garden Restoration in Reggio Calabria
  - Sustainable Agriculture Platform
  - Territorial Welfare Program in Crotone

### 2. **Storie e Radici** (Stories and Roots)
Three distinct tabs with 3-4 cards each:

#### 2a. **Storie** (Stories)
- Personal narratives of professional success
- Inter-generational business journeys
- Example: Entrepreneur from Cosenza building international brand

#### 2b. **Testimonianze** (Testimonials)
- First-person accounts from diaspora members
- Local success stories
- Impact of staying vs. leaving
- Example: Engineer in New York giving back to hometown

#### 2c. **Tradizioni** (Traditions)
- Cultural heritage documentation
- Artisanal techniques
- Festival celebrations
- Example: San Cosmo & San Damiano Festival traditions, Ceramic arts, Tarantella music

### 3. **Eccellenze Calabresi** (Calabrian Excellences)
- **Tab:** main
- **Cards:** 4
- **Content:** Business partnerships and discounts for Rotarians
- **Tags:** 'sconto' (20-25% discounts) or 'gratis' (free access)
- **Example Cards:**
  - 'Nduja & Tradizione Restaurant - 20% discount
  - Organic Agriculture Company - Free tasting + 15% discount
  - Historic Library - Free visits for Rotarians
  - Ceramics Workshop - 25% discount on artisanal products

### 4. **Calendario delle Radici** (Calendar of Roots)
- **Tab:** main
- **Cards:** 4
- **Content:** Upcoming events and celebrations
- **Info Elements:** None (0 required)
- **Example Cards:**
  - Biodiversity Festival (3 days in Sila)
  - Traditional Calabrese Dinner Gala
  - International Rotary Conference on Territoriality
  - Itinerant Exhibition of Calabrian Masters

### 5. **Scopri la Calabria** (Discover Calabria)
Three distinct tabs with 3-4 cards each:

#### 5a. **Itinerari** (Itineraries)
- Multi-day travel routes
- **Info Elements:** Duration in days
- **Tags:** Cities (cosenza, crotone, catanzaro, reggio-calabria, etc.)
- **Example Cards:**
  - Sila Grande (3 days) - pristine forests and alpine lakes
  - Ionian Coast (2 days) - marine biodiversity
  - Historic Villages Route (3 days) - medieval heritage
  - Messina Strait (2 days) - mythological and strategic locations

#### 5b. **Esperienze** (Experiences)
- Hands-on activities and workshops
- **Info Elements:** Price point
- **Tags:** Experience type (enogastronomia, artigianato, natura)
- **Example Cards:**
  - Calabrese Cooking Class (€65) - traditional recipes
  - Ceramic Workshop in Seminara (€85) - artisanal pottery
  - Marine Nature Excursion (€45) - snorkeling in Capo Rizzuto
  - Wine Tasting Tour (€75) - DOC Calabrian wines

#### 5c. **Consigli** (Advice/Tips)
- Short, practical travel recommendations
- **Info Elements:** None
- **Content:** Minimal (titles and subtitles only)
- **Example Cards:**
  - Visit Sila in June/September, avoid August crowds
  - Albanian communities (arbëreshë) deserve 2-3 days
  - Aspromonte is the "Sicilian balcony" - stunning sunset views

### 6. **Scambi e Mobilità** (Exchanges and Mobility)
Two distinct tabs with 4 cards each:

#### 6a. **Offri** (Offer - We Offer These Opportunities)
- Internships, exchanges, mentoring programs
- **Info Elements:**
  - Posti disponibili (available spots)
  - Periodo anno (timeframe)
- **Example Cards:**
  - Tech Internship Milan (5 spots, June-September)
  - Toronto Exchange Program (3 spots, January-June)
  - Online Mentoring (10 spots, year-round)
  - University Scholar Position Bologna (2 spots, Sept-Aug)

#### 6b. **Cerca** (Search - We're Looking For)
- Requests for mentors, partners, volunteers
- **Info Elements:**
  - Number of positions sought
  - Timeline
- **Example Cards:**
  - Marketing Mentor for Calabrese Startup (1 mentor, Feb-Dec)
  - Engineering Professor (1 position, 2025-26 academic year)
  - European Business Partner (2 partners, immediate)
  - Medical Research Volunteers (15 positions, March-November)

### 7. **Archivio** (Archive)
- **Tab:** main
- **Cards:** 4
- **Content:** Historical documents and media
- **Tags:** 'testo', 'foto', 'video' (document type)
- **Example Cards:**
  - Historic Statutes from 1952
  - Photographs from 1985 Anniversary Dinner
  - Documentary: 30 Years of Rotary Service (45 mins)
  - Digitized Magazine Archive (1960-1980, 120 articles)

## Data Schema

Each card includes:

```python
{
    'title': str,                    # Main heading
    'subtitle': str,                 # Secondary description
    'section': str,                  # Section key (auto-assigned)
    'tab': str,                      # Tab within section (auto-assigned)
    'location': str or None,         # Geographic location
    'tags': List[str],               # Relevant tags (respects allowed list)
    'content': str or None,          # HTML content
    'cover_image': None,             # Always None in this seeding
    'date_type': str,                # 'single', 'range', or 'none'
    'date': date or None,            # For single date events
    'date_start': date or None,      # For date ranges
    'date_end': date or None,        # For date ranges
    'author': User,                  # Random user from seed_demo
    'is_published': bool,            # Always True
    'infoElementValues': List[str],  # Values matching section/tab config
}
```

## Info Elements Configuration

Info elements are configured in `/section/structure.py`. The `seed_cards` script automatically generates appropriate values for each:

| Section | Tab | Info Elements | Example Values |
|---------|-----|---------------|-----------------|
| Adotta Progetto | main | 3 (importo, impatto, scadenza) | €150.000, Alto, 31 Marzo 2026 |
| Eccellenze | main | 1 (sconto) | 20% sconto |
| Scopri - Itinerari | itinerari | 1 (giorni) | 3 giorni |
| Scopri - Esperienze | esperienze | 1 (prezzo) | €65 per persona |
| Scambi - Offri | offri | 2 (posti, periodo) | 5 posti, Giugno-Settembre |
| Scambi - Cerca | cerca | 2 (posti, periodo) | 1 mentor, Febbraio-Dicembre |
| Calendario | main | 0 | (none) |
| Storie/Archivio | varies | 0 | (none) |

## Verification

After running the command, verify the data:

```bash
# Count cards per section
python manage.py shell
>>> from section.models import Card
>>> Card.objects.values('section', 'tab').annotate(count=Count('id')).order_by('section')

# Check a specific card
>>> card = Card.objects.first()
>>> print(card.title, card.section, card.tab, len(card.infoElementValues))
```

## Customization

To modify the seeding data:

1. **Edit card content:** Modify the return statements in `_cards_*_*` methods
2. **Change card count:** Adjust the number of dictionaries in each method
3. **Modify tags:** Use `self._select_tags()` with different preferred_tags
4. **Adjust dates:** Change the `timedelta(days=X)` values

### Example: Add a card to Adotta un Progetto

```python
def _cards_adotta_un_progetto(self, tab, allowed_tags, info_elements_count):
    return [
        # ... existing cards ...
        {
            'title': 'Your New Project Title',
            'subtitle': 'Brief description',
            'location': 'City, Country',
            'tags': self._select_tags(allowed_tags, ['educazione']),
            'content': '<p>Detailed HTML content here</p>',
            'date_type': 'range',
            'date_start': timezone.now().date() + timedelta(days=30),
            'date_end': timezone.now().date() + timedelta(days=365),
            'infoElementValues': ['€100.000', 'Alto', '31 Dicembre 2025'],
            'is_published': True,
        },
    ]
```

## Error Handling

The script includes:
- ✅ User existence checking
- ✅ Tag validation (only uses allowed tags)
- ✅ Info element count validation
- ✅ Error reporting with visual indicators
- ✅ Graceful error continuation (creates what it can)

## Performance

- **Execution time:** ~2-3 seconds
- **Database queries:** ~150 (44 cards + author lookups)
- **Memory usage:** Minimal (<50MB)

## Best Practices

1. ✅ Always run `seed_demo --reset` before `seed_cards`
2. ✅ Use `--reset` when developing to maintain clean data
3. ✅ Check the visual output for creation confirmation
4. ✅ Verify data in admin interface before production use
5. ✅ Keep consistent with the frontend configuration in `sections.structure.ts`

## Troubleshooting

### "No users found" error
- **Solution:** Run `python manage.py seed_demo --reset` first

### Cards not created
- **Check:** Look for error messages with ✗ symbols
- **Verify:** All imports are correct
- **Test:** Run `python manage.py shell` and manually create a card

### Wrong info element count
- **Check:** The `get_info_elements_config()` function
- **Verify:** The structure configuration file matches
- **Review:** Each card's `infoElementValues` list length

### Tags not valid
- **Check:** The `allowed_tags` list for that section/tab
- **Review:** The preferred tags in `self._select_tags()` calls
- **Verify:** Tags match between frontend (`sections.structure.ts`) and backend (`structure.py`)

## Future Enhancements

Possible improvements:
- [ ] Image generation for `cover_image` field
- [ ] Multi-language content support
- [ ] CSV import for bulk customization
- [ ] Interactive CLI for custom seeding parameters
- [ ] Realistic user assignment based on location/skills
- [ ] Related cards linking (e.g., project → testimonial)

---

**Last Updated:** December 2025  
**Version:** 1.0  
**Author:** Radici Rotariane Backend Team
