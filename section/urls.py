# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('cards/saved/', views.list_saved_cards, name='list-saved-cards'),
    path('cards/user/', views.list_user_cards, name='list-user-cards'),
    path('cards/<slug:slug>', views.get_card, name='get-card'),
    path('cards/<slug:slug>/save/', views.toggle_save_card, name='toggle-save-card'),
    path('cards/<slug:slug>/report/', views.report_card, name='report-card'),
    path('cards/<slug:slug>/translate/', views.translate_card, name='translate-card'),
    # Gli articoli si indirizzano per TIPO, non per sezione: e' il tipo a dire
    # a quale elenco appartengono. La sezione e' diventata una pagina del CMS
    # che sceglie quale tipo mostrare.
    path('articles/', views.list_articles, name='list-articles'),
    path('articles/<slug:type_key>/create', views.create_article, name='create-article'),
]