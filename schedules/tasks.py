from django_q.tasks import schedule
from django.core.mail import send_mail
from django.utils import timezone
from .models import Event

def send_reminder(event_id):
    event = Event.objects.get(pk=event_id)
    send_mail(
        'Event Reminder',
        f'Your event "{event.title}" is starting soon.',
        'from@example.com',
        [event.user.email],
        fail_silently=False,
    )

def schedule_reminders():
    now = timezone.now()
    events = Event.objects.filter(start_time__gt=now, start_time__lte=now + timezone.timedelta(minutes=30))
    for event in events:
        schedule('schedules.tasks.send_reminder', event.pk, schedule_type='O', next_run=event.start_time - timezone.timedelta(minutes=30))
