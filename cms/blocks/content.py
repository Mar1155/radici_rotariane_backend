"""I blocchi veri e propri, uno per componente React esistente."""

from wagtail import blocks


from cms import vocabularies as vocab
from .common import (ACCENT_CHOICES, SURFACE_CHOICES, ImmagineBlock,
                     LinkBlock, TipoArticoloBlock)

RICH_TEXT_FEATURES = [
    'h2', 'h3', 'h4', 'bold', 'italic', 'link', 'document-link',
    'ol', 'ul', 'hr', 'blockquote',
]


class HeroBlock(blocks.StructBlock):
    """Intestazione di pagina — app/components/CardHero.tsx"""

    title = blocks.CharBlock(label='titolo')
    description = blocks.TextBlock(label='descrizione')
    tag = blocks.CharBlock(required=False, label='etichetta',
                           help_text='La pillola sopra il titolo.')
    surface = blocks.ChoiceBlock(choices=SURFACE_CHOICES, default='brand-gradient',
                                 label='sfondo')
    accent = blocks.ChoiceBlock(choices=ACCENT_CHOICES, default='brand-primary',
                                label='colore della sezione',
                                help_text="Usato solo se lo sfondo e' "
                                          "'Colore della sezione'.")
    scroll_to_id = blocks.CharBlock(
        required=False, label='scorri fino a',
        help_text="Identificativo del blocco a cui portare l'utente. Lascia vuoto "
                  'per non mostrare la freccia.')

    class Meta:
        icon = 'title'
        label = 'intestazione'


class CtaBannerBlock(blocks.StructBlock):
    """Fascia di invito all'azione — finalCta della home, cta di /partner."""

    title = blocks.CharBlock(label='titolo')
    description = blocks.TextBlock(required=False, label='descrizione')
    surface = blocks.ChoiceBlock(choices=SURFACE_CHOICES, default='brand-gradient',
                                 label='sfondo')
    primary_cta = LinkBlock(label='pulsante principale')
    secondary_cta = LinkBlock(required=False, label='pulsante secondario')

    class Meta:
        icon = 'plus-inverse'
        label = 'invito all azione'


class PartnerItemBlock(blocks.StructBlock):
    name = blocks.CharBlock(label='nome')
    description = blocks.TextBlock(required=False, label='descrizione')
    logo = ImmagineBlock(required=False, label='logo')
    emoji = blocks.CharBlock(
        required=False, max_length=8, label='emoji',
        help_text="Alternativa al logo per chi non ne ha uno.")
    link = blocks.URLBlock(required=False, label='sito')
    logo_scale = blocks.IntegerBlock(
        default=100, min_value=60, max_value=160, label='dimensione del logo (%)',
        help_text='Alcuni loghi hanno molto spazio bianco intorno e vanno '
                  'ingranditi per pesare come gli altri.')

    class Meta:
        icon = 'image'
        label = 'partner'


class PartnerGridBlock(blocks.StructBlock):
    """Griglia di loghi — app/partner/components/PartnerCard.tsx"""

    title = blocks.CharBlock(label='titolo')
    description = blocks.TextBlock(required=False, label='descrizione')
    columns = blocks.ChoiceBlock(choices=[(str(n), str(n)) for n in (2, 3, 4)],
                                 default='4', label='colonne')
    surface = blocks.ChoiceBlock(choices=SURFACE_CHOICES, default='white', label='sfondo')
    items = blocks.ListBlock(PartnerItemBlock(), label='partner')

    class Meta:
        icon = 'group'
        label = 'griglia partner'


class IconCardBlock(blocks.StructBlock):
    icon = blocks.ChoiceBlock(choices=vocab.ICON_CHOICES, label='icona')
    title = blocks.CharBlock(label='titolo')
    description = blocks.TextBlock(label='descrizione')
    accent = blocks.ChoiceBlock(choices=ACCENT_CHOICES, default='brand-primary',
                                label='accento')
    cta = LinkBlock(required=False, label='collegamento')

    class Meta:
        icon = 'pick'
        label = 'scheda'


class IconCardGridBlock(blocks.StructBlock):
    """Griglia di schede con icona — quickAccess della home, pillars di /progetto."""

    title = blocks.CharBlock(required=False, label='titolo')
    subtitle = blocks.TextBlock(required=False, label='sottotitolo')
    columns = blocks.ChoiceBlock(choices=[(str(n), str(n)) for n in (1, 2, 3, 4)],
                                 default='3', label='colonne')
    surface = blocks.ChoiceBlock(choices=SURFACE_CHOICES, default='white', label='sfondo')
    items = blocks.ListBlock(IconCardBlock(), label='schede')

    class Meta:
        icon = 'form'
        label = 'griglia di schede'


class QuoteBlock(blocks.StructBlock):
    """Citazione — il blocco oggi scritto a mano in app/cip/page.tsx."""

    quote = blocks.TextBlock(label='citazione')
    author = blocks.CharBlock(required=False, label='autore')
    role = blocks.CharBlock(required=False, label='ruolo')
    place_and_date = blocks.CharBlock(required=False, label='luogo e data')

    class Meta:
        icon = 'openquote'
        label = 'citazione'


class ExplanationStepBlock(blocks.StructBlock):
    icon = blocks.ChoiceBlock(choices=vocab.ICON_CHOICES, label='icona')
    title = blocks.CharBlock(label='titolo')
    description = blocks.TextBlock(label='descrizione')

    class Meta:
        icon = 'tick'
        label = 'passo'


class ExplanationStepsBlock(blocks.StructBlock):
    """Passi numerati che spiegano una sezione — SectionExplanation.tsx.

    Distinto da `icon_card_grid` perche' i passi sono numerati e ordinati: sono
    una procedura, non un elenco di caratteristiche.
    """

    title = blocks.CharBlock(label='titolo')
    description = blocks.TextBlock(required=False, label='descrizione')
    accent = blocks.ChoiceBlock(choices=ACCENT_CHOICES, default='brand-primary',
                                label='colore')
    contact_email = blocks.EmailBlock(required=False, label='email di contatto')
    steps = blocks.ListBlock(ExplanationStepBlock(), label='passi')

    class Meta:
        icon = 'list-ol'
        label = 'passi esplicativi'


class ArticleListBlock(blocks.StructBlock):
    """Elenco di articoli di un tipo — la griglia di CardItem.

    Il calendario non e' un blocco a se': e' una **modalita di
    visualizzazione** di questo, perche' filtra gli stessi articoli per data.
    Modellarlo come blocco separato avrebbe reso possibile configurarli scollegati.
    """

    heading = blocks.CharBlock(required=False, label='titolo')
    article_type = TipoArticoloBlock(label='tipo di articolo')
    accent = blocks.ChoiceBlock(choices=ACCENT_CHOICES, default='brand-primary',
                                label='colore')
    layout = blocks.ChoiceBlock(choices=vocab.LAYOUT_CHOICES, default='grid',
                                label='visualizzazione')
    columns = blocks.ChoiceBlock(choices=[(str(n), str(n)) for n in (1, 2, 3, 4)],
                                 default='3', label='colonne')
    limit = blocks.IntegerBlock(required=False, min_value=1, max_value=100,
                                label='quanti al massimo',
                                help_text='Vuoto per mostrarli tutti.')
    show_search = blocks.BooleanBlock(required=False, default=True, label='campo di ricerca')
    show_tag_filter = blocks.BooleanBlock(required=False, default=True, label='filtro per tag')
    show_geo_filter = blocks.BooleanBlock(required=False, default=True, label='filtro geografico')

    class Meta:
        icon = 'list-ul'
        label = 'elenco articoli'


class TabbedArticleListTabBlock(blocks.StructBlock):
    label = blocks.CharBlock(label='etichetta del tab')
    article_type = TipoArticoloBlock(label='tipo di articolo')
    layout = blocks.ChoiceBlock(choices=vocab.LAYOUT_CHOICES, default='grid',
                                label='visualizzazione')
    columns = blocks.ChoiceBlock(choices=[(str(n), str(n)) for n in (1, 2, 3, 4)],
                                 default='3', label='colonne')

    class Meta:
        icon = 'list-ul'
        label = 'tab'


class TabbedArticleListBlock(blocks.StructBlock):
    """Elenco a tab: ogni tab ha il suo tipo di articolo.

    Un tipo per tab e non uno per sezione, perche' i tab della stessa sezione
    sono oggetti diversi: `testimonianze` nasconde perfino il titolo, mentre
    `storie` ha titolo e copertina.
    """

    heading = blocks.CharBlock(required=False, label='titolo')
    accent = blocks.ChoiceBlock(choices=ACCENT_CHOICES, default='brand-primary',
                                label='colore')
    tabs = blocks.ListBlock(TabbedArticleListTabBlock(), label='tab')
    show_search = blocks.BooleanBlock(required=False, default=True, label='campo di ricerca')
    show_tag_filter = blocks.BooleanBlock(required=False, default=True, label='filtro per tag')
    show_geo_filter = blocks.BooleanBlock(required=False, default=True, label='filtro geografico')

    class Meta:
        icon = 'list-ul'
        label = 'elenco articoli a tab'


class TextBandBlock(blocks.StructBlock):
    """Fascia di testo centrata — app/cip/components/WhatIsCIP.tsx"""

    title = blocks.CharBlock(label='titolo')
    body = blocks.TextBlock(label='testo')
    surface = blocks.ChoiceBlock(choices=SURFACE_CHOICES, default='light', label='sfondo')

    class Meta:
        icon = 'doc-full'
        label = 'fascia di testo'


class TaskBlock(blocks.StructBlock):
    title = blocks.CharBlock(label='voce')
    link = LinkBlock(required=False, label='approfondimento')

    class Meta:
        icon = 'tick'
        label = 'voce'


class TaskListBlock(blocks.StructBlock):
    """Elenco puntato di compiti — i compiti dei CIP in app/cip/page.tsx"""

    title = blocks.CharBlock(label='titolo')
    subtitle = blocks.TextBlock(required=False, label='sottotitolo')
    items = blocks.ListBlock(TaskBlock(), label='voci')
    note = blocks.TextBlock(required=False, label='nota finale')
    surface = blocks.ChoiceBlock(choices=SURFACE_CHOICES, default='white', label='sfondo')

    class Meta:
        icon = 'list-ol'
        label = 'elenco di voci'


class PersonBlock(blocks.StructBlock):
    name = blocks.CharBlock(label='nome')
    role = blocks.CharBlock(required=False, label='ruolo')
    email = blocks.EmailBlock(required=False, label='email')
    photo = ImmagineBlock(required=False, label='foto')
    areas = blocks.ListBlock(blocks.CharBlock(label='area'), required=False,
                             label='aree di competenza',
                             help_text='Es. i paesi seguiti da un referente.')

    class Meta:
        icon = 'user'
        label = 'persona'


class PeopleGridBlock(blocks.StructBlock):
    """Elenco di referenti — app/cip/components/ReferentiCIP.tsx

    Oggi i referenti sono scritti dentro il componente con un commento che dice
    "Mock data - sostituire con dati reali": qui diventano contenuto, e il
    cliente puo' aggiornarli quando cambiano gli incarichi.
    """

    title = blocks.CharBlock(label='titolo')
    description = blocks.TextBlock(required=False, label='descrizione')
    columns = blocks.ChoiceBlock(choices=[(str(n), str(n)) for n in (1, 2, 3)],
                                 default='2', label='colonne')
    surface = blocks.ChoiceBlock(choices=SURFACE_CHOICES, default='white', label='sfondo')
    items = blocks.ListBlock(PersonBlock(), label='persone')

    class Meta:
        icon = 'group'
        label = 'elenco persone'


class TierCardBlock(blocks.StructBlock):
    tier = blocks.ChoiceBlock(
        choices=[('bronze', 'Bronzo'), ('silver', 'Argento'), ('gold', 'Oro')],
        label='livello')
    title = blocks.CharBlock(label='titolo')
    description = blocks.TextBlock(label='descrizione')

    class Meta:
        icon = 'pick'
        label = 'livello'


class TierCardsBlock(blocks.StructBlock):
    """Livelli di gemellaggio — i badge di app/progetto/page.tsx.

    Lo stile di ciascun livello resta in lib/badgeConfig.ts: il CMS sceglie il
    livello, non i suoi colori.
    """

    title = blocks.CharBlock(required=False, label='titolo')
    subtitle = blocks.TextBlock(required=False, label='sottotitolo')
    surface = blocks.ChoiceBlock(choices=SURFACE_CHOICES, default='white', label='sfondo')
    items = blocks.ListBlock(TierCardBlock(), label='livelli')

    class Meta:
        icon = 'pick'
        label = 'livelli'

class PageBodyBlock(blocks.StreamBlock):
    hero = HeroBlock()
    rich_text = blocks.RichTextBlock(features=RICH_TEXT_FEATURES, label='testo')
    icon_card_grid = IconCardGridBlock()
    explanation_steps = ExplanationStepsBlock()
    partner_grid = PartnerGridBlock()
    quote = QuoteBlock()
    text_band = TextBandBlock()
    task_list = TaskListBlock()
    people_grid = PeopleGridBlock()
    tier_cards = TierCardsBlock()
    cta_banner = CtaBannerBlock()
    article_list = ArticleListBlock()
    tabbed_article_list = TabbedArticleListBlock()
    image = ImmagineBlock(label='immagine')

    class Meta:
        label = 'contenuto'
