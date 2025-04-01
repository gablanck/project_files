from django.apps import AppConfig


class SchedulesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'schedules'

    def ready(self):
        # Temporarily commented out to allow migrations
        # from .tasks import schedule_reminders
        # schedule_reminders()
        pass
