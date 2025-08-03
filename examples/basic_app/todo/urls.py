"""URL patterns for todo app."""

from django.urls import path
from . import views

app_name = "todo"

urlpatterns = [
    path("", views.index, name="index"),
    path("add/", views.add_todo, name="add"),
    path("toggle/<int:todo_id>/", views.toggle_todo, name="toggle"),
    path("delete/<int:todo_id>/", views.delete_todo, name="delete"),
    path("categories/", views.categories, name="categories"),
]
