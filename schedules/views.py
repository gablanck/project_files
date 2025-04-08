from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Event, SharedSchedule, Connection
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
from django.http import JsonResponse
import json
from datetime import datetime


@login_required
def home(request):
    events = Event.objects.filter(user=request.user).order_by('date', 'start_time')
    return render(request, 'schedules/home.html', {'events': events})


def create_or_edit_event(request, event_id=None):
    if event_id:
        event = get_object_or_404(Event, id=event_id)
        is_edit = True
    else:
        event = Event(user=request.user)  # Ensure a new event is created
        is_edit = False

    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            return redirect('home')  # Redirect after save (to the homepage or event list)
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
        'calendar_title': 'My Schedule'
    })
    
@login_required
def get_calendar_events(request):
    # Get all events for the current user
    events = list(Event.objects.filter(user=request.user))

    # Get connected users and their events
    connected_users = Connection.objects.filter(user=request.user).values_list('connected_to', flat=True)
    connected_events = Event.objects.filter(user__in=connected_users)

    calendar_events = []

    # Combine events for the user and connected users
    all_events = events + list(connected_events)

    for event in all_events:
        is_owner = event.user == request.user

        # Handle None start_time and end_time by providing defaults (00:00 and 23:59)
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

            # Ensure the start and end are correctly parsed
            start = parse_datetime(data['start'])
            end = parse_datetime(data['end'])

            # Update the event's date and time
            event.date = start.date()  # Update the event date
            event.start_time = start.time()  # Update start time
            event.end_time = end.time()  # Update end time
            event.save()

            print(f"Updated event {event.id}: {event.date} from {event.start_time} to {event.end_time}")
            print(f"Raw start: {data['start']}")
            print(f"Parsed start: {start} | Parsed end: {end}")

            return JsonResponse({'success': True})
        except Exception as e:
            print(f"Error updating event: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid method'})



