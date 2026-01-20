# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('cards/<slug:slug>', views.get_card, name='get-card'),
    path('cards/<slug:slug>/report/', views.report_card, name='report-card'),
    path('cards/<slug:slug>/translate/', views.translate_card, name='translate-card'),
    path('<section>/<tab>/cards', views.list_cards, name='list-cards'),
    path('<section>/<tab>/cards/create', views.create_card, name='create-card'),
]