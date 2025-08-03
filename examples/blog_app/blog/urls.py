"""URL patterns for blog app."""

from django.urls import path
from . import views

app_name = "blog"

urlpatterns = [
    path("", views.index, name="index"),
    path("post/<slug:slug>/", views.post_detail, name="post_detail"),
    path("category/<slug:slug>/", views.category_posts, name="category"),
    path("search/", views.search, name="search"),
    path("api/posts/", views.api_posts, name="api_posts"),
]
