# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('api/cards/', views.list_cards, name='list-cards'),
    path('api/cards/create/', views.create_card, name='create-card'),
    path('api/cards/<slug:slug>/', views.get_card, name='get-card'),
]