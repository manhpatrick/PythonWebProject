from django.contrib import admin
from . import views
from django.urls import path,include 
from django.contrib.auth.models import User

urlpatterns = [
    path('purchase/', views.purchase, name='purchase'),
]