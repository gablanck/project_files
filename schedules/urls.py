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
    path('api/calendar-events/', views.get_calendar_events, name='get_calendar_events'),
    # Connection management URLs
    path('users/search/', views.user_search, name='user_search'),
    path('users/connect/<int:user_id>/', views.connect_user, name='connect_user'),
    path('users/disconnect/<int:user_id>/', views.disconnect_user, name='disconnect_user'),
    path('my-connections/', views.my_connections, name='my_connections'),
]
