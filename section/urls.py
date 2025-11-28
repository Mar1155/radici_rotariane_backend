# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('cards/<slug:slug>', views.get_card, name='get-card'),
    path('<section>/cards', views.list_cards, name='list-cards'),
    path('<section>/cards/create', views.create_card, name='create-card'),
]