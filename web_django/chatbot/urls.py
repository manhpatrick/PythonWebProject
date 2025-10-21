from django.urls import path
from . import views

urlpatterns = [
    path('chat/', views.chat, name='chatbot_chat'),
    path('clear/', views.clear_chat, name='chatbot_clear'),
]
