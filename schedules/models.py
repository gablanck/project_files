from django.db import models
from django.contrib.auth.models import User
from datetime import date
from django.utils import timezone

class Event(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateField()  # Keep the DateField for the event date
    start_time = models.TimeField()  # Change to TimeField
    end_time = models.TimeField()    # Change to TimeField
    is_shared = models.BooleanField(default=False)

    is_recurring = models.BooleanField(default=False)
    recurrence_type = models.CharField(
        max_length=10,
        choices=[('daily', 'Daily'), ('weekly', 'Weekly')],
        blank=True,
        null=True
    )
    recurrence_end_date = models.DateField(blank=True, null=True)
    reminder_minutes_before = models.IntegerField(default=15)

    def __str__(self):
        return self.title

class SharedSchedule(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    shared_with = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.event.title} shared with {self.shared_with.username}"

class Connection(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='connections')
    connected_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='connected_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'connected_to']

    def __str__(self):
        return f"{self.user.username} -> {self.connected_to.username}"
    
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey('Event', on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    snoozed_until = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:30]}"

class Comment(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} on {self.event.title}: {self.content[:30]}"