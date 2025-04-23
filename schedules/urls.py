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
    path('schedules/update_event/<int:event_id>/', views.update_event, name='update_event'),

    path('api/calendar-events/', views.get_calendar_events, name='get_calendar_events'),
    path('api/calendar-events/<int:event_id>/update/', views.update_event, name='update_event'),
    path('api/update-event/<int:event_id>/', views.update_event, name='update_event_drag'),

    path('users/search/', views.user_search, name='user_search'),
    path('users/connect/<int:user_id>/', views.connect_user, name='connect_user'),
    path('users/disconnect/<int:user_id>/', views.disconnect_user, name='disconnect_user'),
    path('my-connections/', views.my_connections, name='my_connections'),

    path('notifications/', views.get_notifications, name='get_notifications'),
    path('snooze_notification/<int:notification_id>/', views.snooze_notification, name='snooze_notification'),
    path('notifications/mark_read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),

    path('event/<int:event_id>/', views.event_detail, name='event_detail'),

    path('connection-request/<int:request_id>/accept/', views.accept_connection, name='accept_connection'),
    path('connection-request/<int:request_id>/reject/', views.reject_connection, name='reject_connection'),
    path('connection-request/<int:request_id>/cancel/', views.cancel_request, name='cancel_request'),
    path('connection-request/<int:request_id>/<str:decision>/', views.process_connection_request, name='process_connection_request'),

    path('connections/<int:connection_id>/toggle-sharing/', views.toggle_schedule_sharing, name='toggle_schedule_sharing'),

    path('groups/create/', views.group_create, name='group_create'),
    path('groups/<int:group_id>/invite/', views.group_invite, name='group_invite'),
    path('groups/<int:group_id>/leave/', views.leave_group, name='leave_group'),
    path('group-invitation/<int:invitation_id>/accept/', views.group_accept_invite, name='group_accept_invite'),
    path('group-invitation/<int:invitation_id>/decline/', views.group_decline_invite, name='group_decline_invite'),
    path('groups/<int:group_id>/', views.group_detail, name='group_detail'),

    path('profile/', views.profile_view, name='profile'),
    path('connections/<int:user_id>/profile/', views.view_user_profile, name='view_user_profile'),
    
]

