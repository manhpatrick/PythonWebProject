from django.contrib import admin
from . import views
from django.urls import path,include 
from django.contrib.auth.models import User
urlpatterns = [ 
    path('signup/', views.signup, name="signup"),
    path('signin/', views.signin, name="signin"),
    path('signout/', views.signout, name="signout"),
    path('activate/<uidb64>/<token>/', views.activate, name="activate"),
    path("reset_password/", views.reset_password, name="reset_password"),
    path("reset_password_confirm/<uidb64>/<token>/", views.reset_password_confirm, name="reset_password_confirm"),
    path('guide/', views.guide, name="guide"),
    path('policy/', views.policy, name="policy"),
    path('profile/', views.profile, name="profile"),
    path('update_profile/', views.update_profile, name="update_profile"),
    path('addresses/', views.address_list, name='address_list'),
    path('addresses/add/', views.address_add, name='address_add'),
    path('addresses/<int:address_id>/edit/', views.address_edit, name='address_edit'),
    path('addresses/<int:address_id>/delete/', views.address_delete, name='address_delete'),
    path('addresses/<int:address_id>/set_default/', views.address_set_default, name='address_set_default'),
    path('google-callback/', views.google_oauth_callback, name='google_oauth_callback'),
]