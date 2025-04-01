from django_q.tasks import schedule
from django.core.mail import send_mail
from django.utils import timezone
from .models import Event

def send_reminder(event_id):
    event = Event.objects.get(pk=event_id)
    send_mail(
        'Event Reminder',
        f'Your event "{event.title}" is happening today.',
        'from@example.com',
        [event.user.email],
        fail_silently=False,
    )

def schedule_reminders():
    now = timezone.now().date()  # Get current date without time
    events = Event.objects.filter(date=now)  # Get all events for today
    for event in events:
        # Schedule reminder for today's events
        schedule(
            'schedules.tasks.send_reminder',
            event.pk,
            schedule_type='O',
            next_run=timezone.now()  # Send reminder immediately for today's events
        )
