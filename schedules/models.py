from django.db import models
from django.contrib.auth.models import User

class Event(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateField()  # Changed from start_time and end_time
    is_shared = models.BooleanField(default=False)

    def __str__(self):
        return self.title

class SharedSchedule(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    shared_with = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.event.title} shared with {self.shared_with.username}"