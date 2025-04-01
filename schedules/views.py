from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Event, SharedSchedule
from .forms import EventForm
from django.contrib.auth import login
from .forms import RegisterForm
from django.contrib.auth.models import User 
from django.http import JsonResponse

@login_required
def event_list(request):
    events = Event.objects.filter(user=request.user)
    return render(request, 'schedules/event_list.html', {'events': events})

@login_required
def event_create(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.user = request.user
            event.save()
            return redirect('event_list')
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
            return redirect('event_list')
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
            return redirect('event_list')
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
        return redirect('event_list')
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
    return redirect('event_list')

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
    """Get all events for the logged-in user and format them for FullCalendar"""
    events = Event.objects.filter(user=request.user)
    event_list = []
    
    for event in events:
        # Create base event data
        event_data = {
            'id': event.id,
            'title': event.title,
            'start': event.date.isoformat(),
            'description': event.description if hasattr(event, 'description') else '',
            'allDay': True,  # Default to all-day event
            'backgroundColor': '#3788d8',  # Default calendar color
            'borderColor': '#3788d8',
            'textColor': '#ffffff',
            'editable': True,  # Allow events to be dragged and resized
        }
        
        # Handle start and end times if they exist
        if hasattr(event, 'start_time') and event.start_time:
            event_data['start'] = event.start_time.isoformat()
            event_data['allDay'] = False
            
        if hasattr(event, 'end_time') and event.end_time:
            event_data['end'] = event.end_time.isoformat()
            event_data['allDay'] = False
        elif hasattr(event, 'end_date') and event.end_date:
            event_data['end'] = event.end_date.isoformat()
            event_data['allDay'] = False
            
        # Add any shared status indicators
        if hasattr(event, 'is_shared') and event.is_shared:
            event_data['backgroundColor'] = '#28a745'  # Green for shared events
            event_data['borderColor'] = '#28a745'
            
        event_list.append(event_data)
    
    return JsonResponse(event_list, safe=False)

@login_required
def get_events_api(request):
    """API endpoint to fetch events in a simple format for other applications"""
    events = Event.objects.filter(user=request.user)
    event_list = []
    
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
            
        event_list.append(event_data)
    
    return JsonResponse(event_list, safe=False)
