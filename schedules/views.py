from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Event, SharedSchedule, Connection, Comment, ConnectionRequest
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
            event.is_shared = form.cleaned_data.get('is_shared', False)
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
    # Get user's own events
    events = list(Event.objects.filter(user=request.user))
    print(f"User's own events: {len(events)}")
    
    # Get connected users with sharing enabled
    connected_users = Connection.objects.filter(
        user=request.user, 
        share_schedule=True
    ).values_list('connected_to', flat=True)
    print(f"Connected users with sharing enabled: {list(connected_users)}")
    
    # Get all events from connected users (ignore is_shared flag)
    connected_events = Event.objects.filter(user__in=connected_users)
    print(f"Connected events: {len(list(connected_events))}")
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
    
    # Get sent connection requests
    sent_requests = ConnectionRequest.objects.filter(
        sender=request.user,
        accepted=False
    ).values_list('receiver_id', flat=True)
    
    # Get received connection requests
    received_requests = ConnectionRequest.objects.filter(
        receiver=request.user,
        accepted=False
    ).values_list('sender_id', flat=True)
    
    # Add connection status to each user
    for user in users:
        user.is_connected = user.id in connected_users
        user.request_sent = user.id in sent_requests
        user.request_received = user.id in received_requests

    context = {
        'users': users,
        'query': query
    }
    
    return render(request, 'connections/user_search.html', context)

@login_required
def connect_user(request, user_id):
    """
    View for sending a connection request to another user
    """
    if request.method == 'POST':
        try:
            user_to_connect = User.objects.get(id=user_id)
            if user_to_connect == request.user:
                messages.error(request, "You can't connect with yourself")
                return redirect('user_search')
                
            # Check if already connected
            if Connection.objects.filter(user=request.user, connected_to=user_to_connect).exists():
                messages.info(request, f'Already connected with {user_to_connect.username}')
                return redirect('user_search')
                
            # Check if request already sent
            request_exists = ConnectionRequest.objects.filter(
                sender=request.user, 
                receiver=user_to_connect,
                accepted=False
            ).exists()
            
            if request_exists:
                messages.info(request, f'Connection request already sent to {user_to_connect.username}')
            else:
                # Create new connection request
                ConnectionRequest.objects.create(
                    sender=request.user,
                    receiver=user_to_connect
                )
                
                # Create notification for the receiver
                Notification.objects.create(
                    user=user_to_connect,
                    message=f"{request.user.username} sent you a connection request"
                )
                
                messages.success(request, f'Connection request sent to {user_to_connect.username}')
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
    # Get existing connections
    connections = Connection.objects.filter(user=request.user).select_related('connected_to')
    
    # Get pending connection requests received by the user
    received_requests = ConnectionRequest.objects.filter(
        receiver=request.user, 
        accepted=False
    ).select_related('sender')
    
    # Get sent connection requests that are still pending
    sent_requests = ConnectionRequest.objects.filter(
        sender=request.user,
        accepted=False
    ).select_related('receiver')
    
    return render(request, 'connections/my_connections.html', {
        'connections': connections,
        'received_requests': received_requests,
        'sent_requests': sent_requests
    })

@login_required
def toggle_schedule_sharing(request, connection_id):
    if request.method == 'POST':
        connection = get_object_or_404(Connection, id=connection_id, user=request.user)
        connection.share_schedule = not connection.share_schedule  # toggle the flag
        connection.save()
        #next line displayed the messages when display is changed 
        # messages.success(request, f"Schedule sharing {'enabled' if connection.share_schedule else 'disabled'} for {connection.connected_to.username}")
    return redirect('my_connections')


@login_required
def process_connection_request(request, request_id, decision):
    """
    View for processing a connection request based on the decision.
    Now, when a request is accepted, sharing is automatic.
    """
    if request.method == 'POST':
        try:
            conn_request = get_object_or_404(
                ConnectionRequest, 
                id=request_id, 
                receiver=request.user, 
                accepted=False
            )
            
            if decision == 'accept':
                # Create bidirectional connection
                # Enable share_schedule=True by default when connecting
                Connection.objects.update_or_create(
                    user=request.user,
                    connected_to=conn_request.sender,
                    defaults={'share_schedule': True}
                )
                Connection.objects.update_or_create(
                    user=conn_request.sender,
                    connected_to=request.user,
                    defaults={'share_schedule': True}
                )
                
                # Mark request as accepted
                conn_request.accepted = True
                conn_request.save()
                
                # Create notification for the sender
                Notification.objects.create(
                    user=conn_request.sender,
                    message=f"{request.user.username} accepted your connection request"
                )
                
                messages.success(request, f"Successfully connected and automatically shared schedules with {conn_request.sender.username}")
            elif decision == 'reject':
                # Delete the connection request
                sender_name = conn_request.sender.username
                conn_request.delete()
                
                messages.success(request, f"Connection request from {sender_name} rejected")
            else:
                messages.error(request, "Invalid decision")
        except Exception as e:
            messages.error(request, f"Error processing connection request: {str(e)}")
    
    return redirect('my_connections')

# Keep these for backward compatibility
@login_required
def accept_connection(request, request_id):
    """
    View for accepting a connection request
    """
    return process_connection_request(request, request_id, 'accept')

@login_required
def reject_connection(request, request_id):
    """
    View for rejecting a connection request
    """
    return process_connection_request(request, request_id, 'reject')

@login_required
def cancel_request(request, request_id):
    """
    View for canceling a sent connection request
    """
    if request.method == 'POST':
        try:
            conn_request = get_object_or_404(
                ConnectionRequest, 
                id=request_id, 
                sender=request.user,
                accepted=False
            )
            
            # Delete the connection request
            receiver_name = conn_request.receiver.username
            conn_request.delete()
            
            messages.success(request, f"Connection request to {receiver_name} canceled")
        except Exception as e:
            messages.error(request, f"Error canceling connection request: {str(e)}")
    
    return redirect('my_connections')

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
    now_time = timezone.now()
    notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')[:10]

    data = [
        {
            'id': n.id,
            'message': n.message if not (n.snoozed_until and n.snoozed_until > now_time) else (
                n.message if n.message.startswith("[Snoozed]") else f"[Snoozed] {n.message}"
            ),
            'created_at': n.created_at.strftime('%Y-%m-%d %H:%M'),
            'is_read': n.is_read,
            'snoozed': bool(n.snoozed_until and n.snoozed_until > now_time)
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
