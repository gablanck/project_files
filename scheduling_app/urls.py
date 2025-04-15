from django.contrib import admin
from django.urls import include, path
from django.contrib.auth import views as auth_views
from schedules import views  

urlpatterns = [
    path('', views.home, name='home'),
    path('admin/', admin.site.urls),
    path('schedules/', include('schedules.urls')),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
]