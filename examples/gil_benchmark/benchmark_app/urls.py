from django.urls import path
from . import views

app_name = 'benchmark_app'

urlpatterns = [
    path('', views.index, name='index'),
    path('results/', views.results, name='results'),
    path('run/', views.run_benchmark, name='run_benchmark'),
]