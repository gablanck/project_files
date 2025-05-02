from django.contrib import admin
from .models import Event
from .models import ConnectionRequest

admin.site.register(Event)
admin.site.register(ConnectionRequest)
# Register your models here.
