from django.urls import path
from . import views
from .views import register 

urlpatterns = [
    path('', views.event_list, name='event_list'),
    path('event/new/', views.event_create, name='event_create'),
    path('event/<int:pk>/edit/', views.event_update, name='event_edit'),
    path('event/<int:pk>/delete/', views.event_delete, name='event_delete'),
    path('event/<int:pk>/share/', views.share_event, name='share_event'),
    path("register/", register, name="register"),  
    path('schedule/', views.schedule_view, name='schedule'),  # New URL pattern
]
