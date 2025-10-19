from django.contrib import admin
from . import views
from django.urls import path,include 
from django.contrib.auth.models import User
urlpatterns = [
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('update_item/', views.updateItem, name="update_item"),
    path('apply-coupon/', views.apply_coupon, name='apply_coupon'),
    path('remove-coupon/', views.remove_coupon, name='remove_coupon'),
]