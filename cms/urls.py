from django.urls import path

from cms import api

app_name = 'cms'

urlpatterns = [
    path('article-types/', api.article_types, name='article-types'),
    path('geo/', api.geo_areas, name='geo-areas'),
    path('navigation/', api.navigation, name='navigation'),
    path('page/', api.page_by_path, name='page-by-path'),
    path('page-paths/', api.page_paths, name='page-paths'),
    path('preview/', api.preview, name='preview'),
]
