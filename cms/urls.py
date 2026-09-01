from django.urls import path

from cms import api

app_name = 'cms'

urlpatterns = [
    path('article-types/', api.article_types, name='article-types'),
    path('geo/', api.geo_areas, name='geo-areas'),
]
