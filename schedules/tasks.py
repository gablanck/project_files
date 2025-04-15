from django_q.tasks import schedule
from django.core.mail import send_mail
from django.utils import timezone
from .models import Event, Notification
from datetime import datetime, timedelta
from django.utils.timezone import localtime, make_aware


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

def generate_event_notifications(*args, **kwargs):
    local_now = localtime()
    upcoming = local_now + timedelta(minutes=15)

    print(f"[DEBUG] local_now: {local_now}")
    print(f"[DEBUG] upcoming: {upcoming}")

    local_today = local_now.date()
    events = Event.objects.filter(date=local_today)
    print(f"[DEBUG] Events today: {events.count()}")

    for event in events:
        event_start = make_aware(datetime.combine(event.date, event.start_time))

        reminder_time = event_start - timedelta(minutes=event.reminder_minutes_before)
        
        print(f"[DEBUG] Checking event: {event.title} @ {event_start}")

        if local_now >= reminder_time and local_now <= event_start:
            print(f"[DEBUG] --> MATCHED: creating notification for {event.title}")
            if not Notification.objects.filter(user=event.user, event=event).exists():
                Notification.objects.create(
                    user=event.user,
                    event=event,
                    message=f"Reminder: '{event.title}' is starting soon!",
                    is_read=False
                )
        else:
            print(f"[DEBUG] --> SKIPPED: not within 15-minute window")
