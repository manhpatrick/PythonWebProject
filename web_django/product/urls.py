from django.contrib import admin
from . import views
from django.urls import path,include 
from django.contrib.auth.models import User

urlpatterns = [
    path('', views.main, name='main'),
    path('api/product/<int:product_id>/', views.get_product_detail, name='get_product_detail'),
    path('product/<int:id>/', views.cart_item, name='cart_item'),
    path('category/<slug:slug>/', views.category, name='category'),
    path('search/', views.search, name='search'),
    path('profile/', views.profile, name='profile'),
]