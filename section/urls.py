# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('cards/', views.list_cards, name='list-cards'),
    path('cards/create/', views.create_card, name='create-card'),
    path('cards/<slug:slug>/', views.get_card, name='get-card'),
]