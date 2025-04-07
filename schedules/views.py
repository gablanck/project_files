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

@login_required
def home(request):
    events = Event.objects.filter(user=request.user)
    return render(request, 'schedules/home.html', {'events': events})

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
def event_update(request, pk):
    event = get_object_or_404(Event, pk=pk, user=request.user)
    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = EventForm(instance=event)
    return render(request, 'schedules/event_form.html', {'form': form})

@login_required
def event_edit(request, pk):
    event = get_object_or_404(Event, pk=pk, user=request.user)
    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
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
def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk, user=request.user)
    event.delete()  
    return redirect('home')

@login_required
def schedule_view(request):
    """Render the schedule page with initial events"""
    # We don't need to pass events directly since they'll be loaded via AJAX
    # But we can pass user info or other context data if needed
    return render(request, 'schedules/schedule.html', {
        'user_name': request.user.username,
        'calendar_title': 'My Schedule'
    })

@login_required
def get_calendar_events(request):
    """Get all events for the logged-in user and connected users"""
    # Get user's events
    events = list(Event.objects.filter(user=request.user))
    
    # Get connected users' events
    connected_users = Connection.objects.filter(user=request.user).values_list('connected_to', flat=True)
    connected_events = Event.objects.filter(
        user__in=connected_users,
        is_shared=True
    )
    events.extend(connected_events)
    
    calendar_events = []
    
    for event in events:
        is_owner = event.user == request.user
        event_data = {
            'id': event.id,
            'title': f"{event.title} ({event.user.username})" if not is_owner else event.title,
            'start': event.date.isoformat(),
            'description': event.description,
            'allDay': True,
            'backgroundColor': '#3788d8' if is_owner else '#28a745',
            'borderColor': '#3788d8' if is_owner else '#28a745',
            'textColor': '#ffffff',
            'editable': is_owner,
        }
        calendar_events.append(event_data)
    
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
