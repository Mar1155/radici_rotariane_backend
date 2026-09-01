"""Registrazione dei tipi di articolo nell'admin Wagtail.

I tipi di articolo vivono in una sezione separata ("Struttura") rispetto a
pagine e immagini. La ragione e' pratica: comporre una pagina e' un'attivita'
quotidiana del cliente, definire un tipo di articolo e' un'attivita' rara e
strutturale, che nella maggior parte dei casi resta a chi sviluppa.

L'accesso si governa con i permessi standard di Django: chi non ha
`cms.change_articletype` non vede nemmeno la voce di menu, perche' Wagtail
nasconde da solo le voci per cui manca il permesso. Basta quindi un gruppo
dedicato per decidere chi puo' entrarci.
"""

from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from cms.models import ArticleType, GeoArea


class ArticleTypeViewSet(SnippetViewSet):
    model = ArticleType
    icon = 'tasks'
    menu_label = 'Tipi di articolo'
    menu_name = 'article-types'
    list_display = ['name', 'name_plural', 'key']
    search_fields = ['name', 'name_plural', 'key']
    ordering = ['name']
    add_to_admin_menu = False   # sta dentro il gruppo, non da solo


class GeoAreaViewSet(SnippetViewSet):
    model = GeoArea
    icon = 'site'
    menu_label = 'Aree geografiche'
    menu_name = 'geo-areas'
    list_display = ['name', 'level', 'code', 'path']
    list_filter = ['level', 'is_active']
    search_fields = ['name', 'key', 'code']
    ordering = ['path']
    add_to_admin_menu = False


class StrutturaGroup(SnippetViewSetGroup):
    items = (ArticleTypeViewSet, GeoAreaViewSet)
    menu_icon = 'cogs'
    menu_label = 'Struttura'
    menu_name = 'struttura'
    menu_order = 900   # in fondo: non e' roba di uso quotidiano


register_snippet(StrutturaGroup)
