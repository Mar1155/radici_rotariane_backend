"""
SECTIONS & TABS STRUCTURE CONFIGURATION

Central file for defining the ARCHITECTURE of sections, tab-sections, and tags.
Contains ONLY structural definitions for backend consistency.

Structure:
- Each section has tabs
- Each tab has allowed tags
- All identifiers are in Italian

CONSISTENCY RULE: Each card belongs to exactly ONE section, and within that section
to exactly ONE tab. Tags must be from the allowed list for that section-tab combination.
"""

from typing import TypedDict, List, Dict, Tuple, Literal

# ============================================================================
# TYPE DEFINITIONS
# ============================================================================

FieldType = Literal[
    'title',
    'subtitle',
    'content',
    'coverImage',
    'tags',
    'date',
    'location',
    'author',
    'infoElements'
]

UserRole = Literal['user', 'club', 'admin']


class TabFieldsConfig(TypedDict):
    """Field visibility and requirement configuration for a tab"""
    required: List[FieldType]
    hidden: List[FieldType]


class TabConfig(TypedDict):
    """Configuration for a single tab within a section"""
    tags: List[str]
    fields: TabFieldsConfig
    infoElements: int  # Number of info elements each card must have
    canAddArticle: List[UserRole]


class SectionConfig(TypedDict):
    """Configuration for a section"""
    tabs: Dict[str, TabConfig]


# ============================================================================
# UNIFIED STRUCTURE CONFIG
# ============================================================================

STRUCTURE_CONFIG: Dict[str, SectionConfig] = {
    # ADOTTA UN PROGETTO
    'adotta-un-progetto': {
        'tabs': {
            'main': {
                'tags': [
                    'attivo', 'completato', 'educazione', 'sanità', 'ambiente',
                    'sviluppo', 'comunità', 'infrastrutture', 'urgente', 'internazionale'
                ],
                'fields': {
                    'required': ['title', 'location', 'subtitle', 'content', 'infoElements', 'tags', 'author'],
                    'hidden': ['coverImage', 'date'],
                },
                'infoElements': 3,
                'canAddArticle': ['user', 'club', 'admin'],
            }
        }
    },

    # STORIE E RADICI
    'storie-e-radici': {
        'tabs': {
            'storie': {
                'tags': [],
                'fields': {
                    'required': ['title', 'subtitle', 'coverImage', 'content', 'author'],
                    'hidden': ['location', 'tags', 'date', 'infoElements'],
                },
                'infoElements': 0,
                'canAddArticle': ['user', 'club', 'admin'],
            },
            'testimonianze': {
                'tags': [],
                'fields': {
                    'required': ['location', 'subtitle', 'content', 'author'],
                    'hidden': ['title', 'tags', 'date', 'coverImage', 'infoElements'],
                },
                'infoElements': 0,
                'canAddArticle': ['user', 'club', 'admin'],
            },
            'tradizioni': {
                'tags': [
                    'tradizione', 'festa', 'artigianato', 'gastronomia', 'leggenda',
                    'folklore', 'saggezza', 'eredità-culturale', 'mito'
                ],
                'fields': {
                    'required': ['title', 'subtitle', 'coverImage', 'content', 'author'],
                    'hidden': ['date', 'location', 'tags', 'infoElements'],
                },
                'infoElements': 0,
                'canAddArticle': ['user', 'club', 'admin'],
            },
        }
    },

    # ECCELLENZE CALABRESI
    'eccellenze-calabresi': {
        'tabs': {
            'main': {
                'tags': ['sconto', 'gratis'],
                'fields': {
                    'required': ['title', 'subtitle', 'tags', 'infoElements', 'location'],
                    'hidden': ['date', 'coverImage', 'content', 'author'],
                },
                'infoElements': 1,
                'canAddArticle': ['user', 'club', 'admin'],
            }
        }
    },

    # CALENDARIO DELLE RADICI
    'calendario-delle-radici': {
        'tabs': {
            'main': {
                'tags': [],
                'fields': {
                    'required': ['title', 'subtitle', 'coverImage', 'content', 'author', 'date', 'location'],
                    'hidden': ['tags', 'infoElements'],
                },
                'infoElements': 0,
                'canAddArticle': ['user', 'club', 'admin'],
            },
        }
    },

    # SCOPRI LA CALABRIA
    'scopri-la-calabria': {
        'tabs': {
            'itinerari': {
                'tags': [
                    'cosenza', 'rende', 'crotone', 'catanzaro', 'vibo-valentia', 'reggio-calabria'
                ],
                'fields': {
                    'required': ['title', 'location', 'tags', 'subtitle', 'coverImage', 'content', 'infoElements', 'author'],
                    'hidden': ['date'],
                },
                'infoElements': 1,
                'canAddArticle': ['user', 'club', 'admin'],
            },
            'esperienze': {
                'tags': ['enogastronomia', 'artigianato', 'natura'],
                'fields': {
                    'required': ['title', 'location', 'tags', 'subtitle', 'coverImage', 'content', 'infoElements', 'author'],
                    'hidden': ['date'],
                },
                'infoElements': 1,
                'canAddArticle': ['user', 'club', 'admin'],
            },
            'consigli': {
                'tags': [],
                'fields': {
                    'required': ['title', 'subtitle'],
                    'hidden': ['date', 'location', 'tags', 'infoElements', 'coverImage', 'content', 'author'],
                },
                'infoElements': 0,
                'canAddArticle': ['admin'],
            },
        }
    },

    # SCAMBI E MOBILITA
    'scambi-e-mobilita': {
        'tabs': {
            'offri': {
                'tags': [],
                'fields': {
                    'required': ['title', 'subtitle', 'location', 'infoElements', 'author'],
                    'hidden': ['tags', 'date', 'coverImage', 'content'],
                },
                'infoElements': 2,
                'canAddArticle': ['user', 'club', 'admin'],
            },
            'cerca': {
                'tags': [],
                'fields': {
                    'required': ['title', 'subtitle', 'location', 'infoElements', 'author'],
                    'hidden': ['tags', 'date', 'coverImage', 'content'],
                },
                'infoElements': 2,
                'canAddArticle': ['user', 'club', 'admin'],
            },
        }
    },

    # ARCHIVIO
    'archivio': {
        'tabs': {
            'main': {
                'tags': ['testo', 'foto', 'video'],
                'fields': {
                    'required': ['title', 'subtitle', 'content', 'tags', 'author'],
                    'hidden': ['date', 'location', 'coverImage', 'infoElements'],
                },
                'infoElements': 0,
                'canAddArticle': ['admin'],
            }
        }
    },
}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_all_sections() -> List[str]:
    """Get all section keys"""
    return list(STRUCTURE_CONFIG.keys())


def get_tabs_for_section(section_key: str) -> Dict[str, TabConfig]:
    """Get tabs for a specific section"""
    return STRUCTURE_CONFIG.get(section_key, {}).get('tabs', {})


def get_tab_keys_for_section(section_key: str) -> List[str]:
    """Get tab keys (names) as a list for a specific section"""
    tabs = STRUCTURE_CONFIG.get(section_key, {}).get('tabs', {})
    return list(tabs.keys())


def get_tags_for_tab(section_key: str, tab_key: str) -> List[str]:
    """Get tags for a specific section/tab combination"""
    tabs = STRUCTURE_CONFIG.get(section_key, {}).get('tabs', {})
    return tabs.get(tab_key, {}).get('tags', [])


def is_section_valid(section_key: str) -> bool:
    """Check if a section exists"""
    return section_key in STRUCTURE_CONFIG


def is_tab_valid(section_key: str, tab_key: str) -> bool:
    """Check if a tab exists for a section"""
    tabs = STRUCTURE_CONFIG.get(section_key, {}).get('tabs', {})
    return tab_key in tabs


def is_tag_valid(section_key: str, tab_key: str, tag_key: str) -> bool:
    """Check if a tag exists for a section/tab combination"""
    tags = get_tags_for_tab(section_key, tab_key)
    return tag_key in tags


def get_tab_fields_config(section: str, tab: str) -> TabFieldsConfig:
    """Get the field configuration for a tab"""
    tab_config = STRUCTURE_CONFIG.get(section, {}).get('tabs', {}).get(tab)

    if not tab_config or 'fields' not in tab_config:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"No field config found for section: {section}, tab: {tab}")
        # Fallback: show basic fields as required
        return {
            'required': ['title', 'subtitle', 'coverImage', 'content'],
            'hidden': ['tags', 'date', 'location', 'infoElements'],
        }

    return tab_config['fields']


def should_show_field(section: str, tab: str, field: FieldType) -> bool:
    """Check if a field should be shown in the form"""
    config = get_tab_fields_config(section, tab)
    return field not in config['hidden']


def is_field_required(section: str, tab: str, field: FieldType) -> bool:
    """Check if a field is required"""
    config = get_tab_fields_config(section, tab)
    return field in config['required']


def get_required_fields(section: str, tab: str) -> List[FieldType]:
    """Get list of all required fields for a tab"""
    config = get_tab_fields_config(section, tab)
    return config['required']


def get_info_elements_config(section: str, tab: str) -> int:
    """Get the expected number of info elements for a section/tab"""
    return STRUCTURE_CONFIG.get(section, {}).get('tabs', {}).get(tab, {}).get('infoElements', 0)


def get_expected_info_elements_count(section: str, tab: str) -> int:
    """Get the expected number of info elements for a section/tab"""
    return get_info_elements_config(section, tab)


def get_can_add_article_roles(section: str, tab: str) -> List[UserRole]:
    """Get the roles that can add articles for a section/tab"""
    return STRUCTURE_CONFIG.get(section, {}).get('tabs', {}).get(tab, {}).get('canAddArticle', ['user', 'club', 'admin'])


def can_user_add_article(section: str, tab: str, user_role: UserRole) -> bool:
    """Check if a user with a specific role can add articles"""
    roles = get_can_add_article_roles(section, tab)
    return user_role in roles


def validate_card_consistency(
    section: str,
    tab: str,
    tags: List[str],
    info_elements_count: int
) -> Tuple[bool, List[str]]:
    """
    Validate card consistency with the structure configuration.

    Args:
        section: The card's section
        tab: The card's tab
        tags: The card's tags
        info_elements_count: The count of info elements in the card

    Returns:
        A tuple (is_valid, errors) where errors is a list of validation error messages
    """
    errors: List[str] = []

    # Check section
    if not is_section_valid(section):
        errors.append(f"Invalid section: {section}")
        return False, errors

    # Check tab
    if not is_tab_valid(section, tab):
        errors.append(f"Invalid tab '{tab}' for section '{section}'")
        return False, errors

    # Check tags
    allowed_tags = get_tags_for_tab(section, tab)
    for tag in tags:
        if tag not in allowed_tags:
            errors.append(f"Invalid tag '{tag}' for section '{section}', tab '{tab}'. Allowed: {allowed_tags}")

    # Check info elements count
    expected_count = get_expected_info_elements_count(section, tab)
    if info_elements_count != expected_count:
        errors.append(
            f"Invalid info elements count. Expected {expected_count}, got {info_elements_count} "
            f"for section '{section}', tab '{tab}'"
        )

    return len(errors) == 0, errors
