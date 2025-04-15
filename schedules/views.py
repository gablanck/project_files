from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Event, SharedSchedule, Connection, Comment
from .forms import EventForm
from django.contrib.auth import login
from .forms import RegisterForm
from django.contrib.auth.models import User 
from django.http import JsonResponse
from django.db.models import Q
from django.contrib import messages
from datetime import datetime, time
from django.views.decorators.csrf import csrf_exempt
import json
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
import json
from datetime import datetime, timedelta
from .models import Notification
from django.utils.timezone import now
from django.utils import timezone
from .forms import CommentForm



@login_required
def home(request):
    events = Event.objects.filter(user=request.user).order_by('date', 'start_time')
    return render(request, 'schedules/home.html', {'events': events})


def create_or_edit_event(request, event_id=None):
    if event_id:
        event = get_object_or_404(Event, id=event_id)
        is_edit = True
    else:
        event = Event(user=request.user)
        is_edit = False

    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            event = form.save(commit=False)
            event.user = request.user
            event.save()

            # ✅ Only create recurring events when adding a new one
            if not is_edit and event.is_recurring and event.recurrence_type and event.recurrence_end_date:
                from datetime import timedelta

                current_date = event.date
                while True:
                    if event.recurrence_type == 'daily':
                        current_date += timedelta(days=1)
                    elif event.recurrence_type == 'weekly':
                        current_date += timedelta(weeks=1)

                    if current_date > event.recurrence_end_date:
                        break

                    # Create copies of the recurring event
                    Event.objects.create(
                        user=event.user,
                        title=event.title,
                        description=event.description,
                        date=current_date,
                        start_time=event.start_time,
                        end_time=event.end_time,
                        is_shared=event.is_shared,
                        is_recurring=False  # prevent child events from looping
                    )

            return redirect('home')
    else:
        form = EventForm(instance=event)

    context = {
        'form': form,
        'is_edit': is_edit,
        'event': event
    }
    return render(request, 'schedules/event_form.html', context)


@login_required
def event_create(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.user = request.user
            event.save()
            return redirect('home')
    else:
        form = EventForm()
    return render(request, 'schedules/event_form.html', {'form': form})

@login_required
def event_edit(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            # No need to clean time anymore as it's now properly handled in the form
            form.save()
            return redirect('home')
    else:
        form = EventForm(instance=event)
    
    return render(request, 'schedules/event_form.html', {'form': form})

@login_required
def share_event(request, pk):
    event = get_object_or_404(Event, pk=pk, user=request.user)
    if request.method == 'POST':
        shared_with_username = request.POST.get('shared_with')
        shared_with = User.objects.get(username=shared_with_username)
        SharedSchedule.objects.create(event=event, shared_with=shared_with)
        event.is_shared = True
        event.save()
        return redirect('home')
    return render(request, 'schedules/share_event.html', {'event': event})

def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = RegisterForm()

    return render(request, "registration/register.html", {"form": form})


@login_required
def event_delete(request, event_id):
    event = get_object_or_404(Event, pk=event_id, user=request.user)
    event.delete()  
    return redirect('home')

@login_required
def schedule_view(request):
    """Render the schedule page with initial events"""
    
    return render(request, 'schedules/schedule.html', {
        'user_name': request.user.username,
        'calendar_title': 'My Schedule',
        
    })
    
@login_required
def get_calendar_events(request):
    events = list(Event.objects.filter(user=request.user))
    connected_users = Connection.objects.filter(user=request.user).values_list('connected_to', flat=True)
    connected_events = Event.objects.filter(user__in=connected_users)

    calendar_events = []
    all_events = events + list(connected_events)

    for event in all_events:
        is_owner = event.user == request.user
        start_dt = datetime.combine(event.date, event.start_time or time(0, 0))
        end_dt = datetime.combine(event.date, event.end_time or time(23, 59))

        calendar_events.append({
            'id': event.id,
            'title': f"{event.title} ({event.user.username})" if not is_owner else event.title,
            'start': start_dt.isoformat(),
            'end': end_dt.isoformat(),
            'description': event.description,
            'allDay': False,
            'backgroundColor': '#3788d8' if is_owner else '#28a745',
            'borderColor': '#3788d8' if is_owner else '#28a745',
            'textColor': '#ffffff',
            'editable': is_owner,
            'extendedProps': {
                'creatorId': str(event.user.id),  # Add this line
                'creatorName': event.user.username  # Optional: include creator's name
            }
        })
        # Handle recurrence
        if event.is_recurring and event.recurrence_end_date:
            current_date = event.date
            while True:
                if event.recurrence_type == 'daily':
                    current_date += timedelta(days=1)
                elif event.recurrence_type == 'weekly':
                    current_date += timedelta(weeks=1)
                else:
                    break

                if current_date > event.recurrence_end_date:
                    break

                recur_start = datetime.combine(current_date, event.start_time or time(0, 0))
                recur_end = datetime.combine(current_date, event.end_time or time(23, 59))

                calendar_events.append({
                    'id': f"{event.id}-{current_date.isoformat()}",  # pseudo-unique ID
                    'title': f"{event.title} ({event.user.username})" if not is_owner else event.title,
                    'start': recur_start.isoformat(),
                    'end': recur_end.isoformat(),
                    'description': event.description,
                    'backgroundColor': '#3788d8' if is_owner else '#28a745',
                    'borderColor': '#3788d8' if is_owner else '#28a745',
                    'textColor': '#ffffff',
                    'editable': False  # You can make them read-only unless you handle recurrence updates
                })

    return JsonResponse(calendar_events, safe=False)
@login_required
def user_search(request):
    """
    View for searching users and displaying connection status
    """
    query = request.GET.get('q', '')
    
    # Get all users except the current user
    users = User.objects.exclude(id=request.user.id)
    
    # Apply search filter if query exists
    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query)
        )

    # Get current connections for the logged-in user
    connected_users = Connection.objects.filter(user=request.user).values_list('connected_to_id', flat=True)
    
    # Add connection status to each user
    for user in users:
        user.is_connected = user.id in connected_users

    context = {
        'users': users,
        'query': query
    }
    
    return render(request, 'connections/user_search.html', context)

@login_required
def connect_user(request, user_id):
    """
    View for creating a connection with another user
    """
    if request.method == 'POST':
        try:
            user_to_connect = User.objects.get(id=user_id)
            if user_to_connect != request.user:
                connection, created = Connection.objects.get_or_create(
                    user=request.user,
                    connected_to=user_to_connect
                )
                if created:
                    messages.success(request, f'Successfully connected with {user_to_connect.username}')
                else:
                    messages.info(request, f'Already connected with {user_to_connect.username}')
            else:
                messages.error(request, "You can't connect with yourself")
        except User.DoesNotExist:
            messages.error(request, "User not found")
    return redirect('user_search')

@login_required
def disconnect_user(request, user_id):
    """
    View for removing a connection with another user
    """
    if request.method == 'POST':
        Connection.objects.filter(
            user=request.user,
            connected_to_id=user_id
        ).delete()
        messages.success(request, 'Successfully disconnected')
    return redirect('user_search')

@login_required
def my_connections(request):
    connections = Connection.objects.filter(user=request.user).select_related('connected_to')
    return render(request, 'connections/my_connections.html', {
        'connections': connections
    })

@login_required
def get_events_api(request):
    """API endpoint to fetch events in a simple format for other applications"""
    events = Event.objects.filter(user=request.user)
    home = []
    
    for event in events:
        event_data = {
            'id': event.id,
            'title': event.title,
            'date': event.date.isoformat(),
            'description': event.description if hasattr(event, 'description') else '',
            'is_shared': event.is_shared if hasattr(event, 'is_shared') else False
        }
        
        # Add start_time and end_time if they exist
        if hasattr(event, 'start_time') and event.start_time:
            event_data['start_time'] = event.start_time.isoformat()
            
        if hasattr(event, 'end_time') and event.end_time:
            event_data['end_time'] = event.end_time.isoformat()
        elif hasattr(event, 'end_date') and event.end_date:
            event_data['end_date'] = event.end_date.isoformat()
            
        home.append(event_data)
    
    return JsonResponse(home, safe=False)

@csrf_exempt
@login_required
def update_event(request, event_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            event = Event.objects.get(id=event_id, user=request.user)
            
            # Get the explicit date components if available
            event_date = data.get('date')
            start_time_str = data.get('startTime')
            end_time_str = data.get('endTime')
            
            # If explicit components are provided, use them
            if event_date and start_time_str and not data.get('preserveTime', False):
                # Parse the date
                from datetime import datetime, time
                
                # Update just the date
                event.date = datetime.strptime(event_date, '%Y-%m-%d').date()
                
                # Update the time if not preserving it
                start_time_parts = start_time_str.split(':')
                event.start_time = time(
                    int(start_time_parts[0]), 
                    int(start_time_parts[1]),
                    int(start_time_parts[2].split('.')[0]) if '.' in start_time_parts[2] else int(start_time_parts[2])
                )
                
                # Update end time if provided
                if end_time_str:
                    end_time_parts = end_time_str.split(':')
                    event.end_time = time(
                        int(end_time_parts[0]), 
                        int(end_time_parts[1]),
                        int(end_time_parts[2].split('.')[0]) if '.' in end_time_parts[2] else int(end_time_parts[2])
                    )
            else:
                # Handle the ISO string approach (but be cautious of timezone issues)
                start = parse_datetime(data['start'])
                end = parse_datetime(data['end']) if data.get('end') else None
                
                # Update the date in all cases
                event.date = start.date()
                
                # Only update time if not preserving it
                if not data.get('preserveTime', False):
                    event.start_time = start.time()
                    if end:
                        event.end_time = end.time()

            event.save()

            return JsonResponse({
                'success': True,
                'event': {
                    'id': event.id,
                    'title': event.title,
                    'date': event.date.isoformat(),
                    'start_time': event.start_time.isoformat() if event.start_time else None,
                    'end_time': event.end_time.isoformat() if event.end_time else None
                }
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid method'})

@login_required
def get_notifications(request):
    notifications = Notification.objects.filter(user=request.user, is_read=False).exclude(snoozed_until__gt=timezone.now()).order_by('-created_at')[:10]
    
    data = [
        {
            'id': n.id,
            'message': n.message,
            'created_at': n.created_at.strftime('%Y-%m-%d %H:%M'),
            'is_read': n.is_read
        }
        for n in notifications
    ]
    return JsonResponse({'notifications': data})

def snooze_notification(request, notification_id):
    if request.user.is_authenticated:
        minutes = int(request.GET.get('minutes', 5))  # default snooze = 5 mins
        try:
            notif = Notification.objects.get(id=notification_id, user=request.user)
            notif.snoozed_until = now() + timedelta(minutes=minutes)
            notif.save()
            return JsonResponse({'status': 'snoozed', 'until': notif.snoozed_until})
        except Notification.DoesNotExist:
            return JsonResponse({'error': 'Notification not found'}, status=404)
    return JsonResponse({'error': 'Unauthorized'}, status=403)

@require_POST
def mark_notification_read(request, notification_id):
    if request.user.is_authenticated:
        try:
            notif = Notification.objects.get(id=notification_id, user=request.user)
            notif.is_read = True
            notif.save()
            return JsonResponse({'status': 'marked_read'})
        except Notification.DoesNotExist:
            return JsonResponse({'error': 'Notification not found'}, status=404)
    return JsonResponse({'error': 'Unauthorized'}, status=403)

@login_required
def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    comments = event.comments.order_by('-timestamp')
    
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.event = event
            comment.save()
            if event.user != request.user:
                Notification.objects.create(
                    user=event.user,
                    message=f"New comment on your event: '{event.title}' by {request.user.username}",
                )
                
            return redirect('event_detail', event_id=event_id)
    else:
        form = CommentForm()

    return render(request, 'schedules/event_detail.html', {
        'event': event,
        'comments': comments,
        'form': form
    })