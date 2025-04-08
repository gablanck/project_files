from django.urls import path
from . import views
from .views import register 

urlpatterns = [
    path('', views.home, name='home'),
    path('events/create/', views.create_or_edit_event, name='event_create'),
    path('events/<int:event_id>/edit/', views.create_or_edit_event, name='event_edit'),
    path('events/<int:event_id>/delete/', views.event_delete, name='event_delete'),
    path('events/<int:event_id>/share/', views.share_event, name='share_event'),
    path('schedule/', views.schedule_view, name='schedule'),

    path('schedules/api/calendar-events/', views.get_calendar_events, name='get_calendar_events'),

    path('api/calendar-events/', views.get_calendar_events, name='get_calendar_events'),
    path('api/calendar-events/<int:event_id>/update/', views.update_event, name='update_event'),

    path('users/search/', views.user_search, name='user_search'),
    path('users/connect/<int:user_id>/', views.connect_user, name='connect_user'),
    path('users/disconnect/<int:user_id>/', views.disconnect_user, name='disconnect_user'),
    path('my-connections/', views.my_connections, name='my_connections'),

    path('events/<int:event_id>/edit/', views.create_or_edit_event, name='event_edit'),
]

