from django.urls import path
from . import views
from .views import register 

urlpatterns = [
    path('', views.home, name='home'),
    path('events/create/', views.event_create, name='event_create'),
    path('events/<int:pk>/edit/', views.event_update, name='event_edit'),
    path('events/<int:pk>/delete/', views.event_delete, name='event_delete'),
    path('events/<int:pk>/share/', views.share_event, name='share_event'),
    path("register/", register, name="register"),  
    path('schedule/', views.schedule_view, name='schedule'),
    path('api/calendar-events/', views.get_calendar_events, name='get_calendar_events')
]
