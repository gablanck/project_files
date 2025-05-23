from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import (
    Event, SharedSchedule, Connection, Comment, ConnectionRequest,
    Group, GroupMembership, GroupInvitation
)
from .forms import EventForm
from django.contrib.auth import login
from .forms import RegisterForm
from django.contrib.auth.models import User 
from django.http import JsonResponse
from django.db.models import Q
from django.db import transaction, IntegrityError
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
from .models import UserProfile
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from .models import UserProfile, Event
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render
from datetime import timedelta
import calendar
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
import json
import openai
from django.utils.timezone import now
from .models import Event
from datetime import timedelta
from openai import OpenAI
import json
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import Event
import re
import traceback
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils.timezone import make_aware, is_naive
import pytz
from django.conf import settings
from django.utils.dateparse import parse_datetime

@login_required
def home(request):
    # Separate personal events (not in any group)
    events = Event.objects.filter(
        user=request.user,
        group__isnull=True,
        recurring_parent__isnull=True  # Only original/parent events
    ).order_by('date', 'start_time')


    # Find all group memberships for user
    memberships = GroupMembership.objects.filter(user=request.user).select_related('group')
    groups = [mem.group for mem in memberships]

    # All users except self for inviting to groups
    all_other_users = User.objects.exclude(id=request.user.id)
    
    # Build group context for each group
    group_contexts = []
    for group in groups:
        # Find all current members
        member_ids = set(group.memberships.values_list('user_id', flat=True))
        # Find all in-flight invitations (status pending)
        already_invited = set(
            GroupInvitation.objects.filter(group=group, status='pending')
            .values_list('invited_user_id', flat=True)
        )
        invitable_users = all_other_users.exclude(id__in=member_ids | already_invited)
        
        # Only show events for THIS group!
        group_events = Event.objects.filter(group=group).order_by('date', 'start_time')

        group_contexts.append({
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "creator": group.creator,
            "memberships": group.memberships.select_related('user').all(),
            "events": group_events,
            "invitable_users": invitable_users,
        })

    # All pending invites to this user (to display in template)
    pending_group_invitations = GroupInvitation.objects.filter(
        invited_user=request.user, 
        status="pending"
    ).select_related('group', 'invited_by')

    return render(request, 'schedules/home.html', {
        "events": events,
        "groups": group_contexts,
        "pending_group_invitations": pending_group_invitations,
    })


def create_or_edit_event(request, event_id=None):
    # For new events, check if there's a group parameter
    group = None
    group_id = request.GET.get('group')
    
    if event_id:
        event = get_object_or_404(Event, id=event_id)
        is_edit = True
        
        # For existing events, get the group from the event
        if event.group:
            group = event.group
            
        # Check permissions - user must be owner of the event
        if event.user != request.user:
            messages.error(request, "You can only edit your own events.")
            return redirect('home')
    else:
        event = Event(user=request.user)
        is_edit = False
        
        # For new events with a group parameter
        if group_id:
            try:
                group = Group.objects.get(id=group_id)
                # Verify user is a member of the group
                if not GroupMembership.objects.filter(group=group, user=request.user).exists():
                    messages.error(request, "You must be a member of the group to create events.")
                    return redirect('home')
                event.group = group
            except Group.DoesNotExist:
                messages.error(request, "Group not found.")
                return redirect('home')

    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            event = form.save(commit=False)
            event.user = request.user
            
            # Make sure group is preserved
            if group:
                event.group = group
                
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
                        group=event.group,  # Include group in recurring events
                        title=event.title,
                        description=event.description,
                        date=current_date,
                        start_time=event.start_time,
                        end_time=event.end_time,
                        is_shared=event.is_shared,
                        is_recurring=False,  # prevent child events from looping
                        recurring_parent=event
                    )

            return redirect('home')
    else:
        form = EventForm(instance=event)

    context = {
        'form': form,
        'is_edit': is_edit,
        'event': event,
        'group': group
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
    CATEGORY_COLORS = {
        "personal": "#007bff",
        "work": "#0ec9a3",
        "school": "#28a745",
        "fun": "#ffc107",
        "gym": "#ff8800",
        "other": "#ff0000"
    }
    
    # Get connected users with sharing enabled
    connected_users = Connection.objects.filter(
        user=request.user, 
        share_schedule=True
    ).values_list('connected_to', flat=True)
    print(f"Connected users with sharing enabled: {list(connected_users)}")

    # Get user's own events
    # Group memberships with calendar visibility
    group_ids = GroupMembership.objects.filter(
        user=request.user,
        show_in_calendar=True
    ).values_list('group_id', flat=True)

    # Fetch events: personal + connected + group-visible
    events = Event.objects.filter(
        Q(user=request.user, group__isnull=True) |
        Q(user__in=connected_users, group__isnull=True) |
        Q(group_id__in=group_ids)
    ).exclude(
        is_recurring=True,  # Exclude parents
        recurring_parent__isnull=True  # Only if they are actual parents
    ).order_by('date', 'start_time')

    print(f"User's own events: {len(events)}")
    
    calendar_events = []
    
    # Get all events from connected users (ignore is_shared flag)
    connected_events = Event.objects.filter(user__in=connected_users)
    print(f"Connected events: {len(list(connected_events))}")
    
    all_events = list(events) 

    for event in all_events:
        is_owner = event.user == request.user
        start_dt = datetime.combine(event.date, event.start_time or time(0, 0))
        end_dt = datetime.combine(event.date, event.end_time or time(23, 59))
        print(f"Event ID {event.id} | Title: {event.title} | Category: {event.category}")
        category = event.recurring_parent.category if hasattr(event, 'recurring_parent') and event.recurring_parent else event.category
        tag_color = CATEGORY_COLORS.get(category, "#cccccc")
        print(f"Event ID {event.id} | Title: {event.title} | Raw category: {event.category} | Final used category: {category}")

        #bg_color = YOUR_EVENT_COLOR if is_owner else color

        calendar_events.append({
            'id': event.id,
            'title': f"👤 {event.title}" if is_owner else f"🤝 {event.title}",
            'start': start_dt.isoformat(),
            'end': end_dt.isoformat(),
            'description': event.description,
            'allDay': False,
            'backgroundColor': "#2c5364",
            'borderColor': tag_color,
            'textColor': '#ffffff',
            'editable': is_owner,
            'extendedProps': {
                'creatorId': event.user.id,
                'creatorName': event.user.username,
                'isOwner': is_owner,
                'category': event.category,
            }
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
                
            # Check if request already sent (either direction)
            existing_request = ConnectionRequest.objects.filter(
                Q(sender=request.user, receiver=user_to_connect) |
                Q(sender=user_to_connect, receiver=request.user),
                accepted=False
            ).first()

            if existing_request:
                # Update timestamp instead of creating a duplicate
                existing_request.created_at = timezone.now()
                existing_request.save()
                messages.info(request, f"Connection request to {user_to_connect.username} refreshed.")
            else:
                try:
                    # Create new connection request with transaction handling
                    with transaction.atomic():
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
                except IntegrityError:
                    messages.warning(request, f"Couldn't send request to {user_to_connect.username}. A request may already exist.")
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
    
    # Get groups the user is a member of
    group_memberships = GroupMembership.objects.filter(user=request.user).select_related('group', 'group__creator')
    groups = [membership.group for membership in group_memberships]
    
    # Get pending group invitations for this user
    pending_group_invitations = GroupInvitation.objects.filter(
        invited_user=request.user, 
        status="pending"
    ).select_related('group', 'invited_by')
    
    return render(request, 'connections/my_connections.html', {
        'connections': connections,
        'received_requests': received_requests,
        'sent_requests': sent_requests,
        'groups': groups,  # Added groups
        'pending_group_invitations': pending_group_invitations,  # Added pending invitations
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
def cancel_request_from_search(request, user_id):
    """
    View for canceling a connection request from the user search page
    """
    if request.method == 'POST':
        try:
            # Find the connection request
            conn_request = ConnectionRequest.objects.get(
                sender=request.user,
                receiver_id=user_id,
                accepted=False
            )
            
            # Store receiver's username for the message
            receiver_name = conn_request.receiver.username
            
            # Delete the connection request
            conn_request.delete()
            
            messages.success(request, f"Connection request to {receiver_name} canceled")
        except ConnectionRequest.DoesNotExist:
            messages.error(request, "Connection request not found")
        except Exception as e:
            messages.error(request, f"Error canceling request: {str(e)}")
    
    return redirect('user_search')

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
    from django.utils.timezone import make_aware, is_naive
    import pytz
    from django.conf import settings

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            event = Event.objects.get(id=event_id, user=request.user)

            event_date = data.get('date')
            start_time_str = data.get('startTime')
            end_time_str = data.get('endTime')

            if event_date and start_time_str and not data.get('preserveTime', False):
                from datetime import datetime, time

                event.date = datetime.strptime(event_date, '%Y-%m-%d').date()

                start_parts = start_time_str.split(':')
                event.start_time = time(
                    int(start_parts[0]),
                    int(start_parts[1]),
                    int(start_parts[2].split('.')[0]) if '.' in start_parts[2] else int(start_parts[2])
                )

                if end_time_str:
                    end_parts = end_time_str.split(':')
                    event.end_time = time(
                        int(end_parts[0]),
                        int(end_parts[1]),
                        int(end_parts[2].split('.')[0]) if '.' in end_parts[2] else int(end_parts[2])
                    )
            else:
                start_raw = data.get("start")
                end_raw = data.get("end")
                print(f"[DEBUG] Incoming start: {start_raw}")
                print(f"[DEBUG] Incoming end: {end_raw}")

                start = parse_datetime(start_raw)
                end = parse_datetime(end_raw) if end_raw else None

                print(f"[DEBUG] Parsed naive start: {start} (tzinfo={start.tzinfo})")

                # Ensure timezone-aware in local timezone
                local_tz = pytz.timezone(settings.TIME_ZONE)

                if is_naive(start):
                    start = make_aware(start, timezone=local_tz)
                    print(f"[DEBUG] Converted start to aware: {start} (local tz: {local_tz})")
                else:
                    start = start.astimezone(local_tz)
                    print(f"[DEBUG] Converted start to local tz: {start}")

                if end:
                    if is_naive(end):
                        end = make_aware(end, timezone=local_tz)
                        print(f"[DEBUG] Converted end to aware: {end}")
                    else:
                        end = end.astimezone(local_tz)
                        print(f"[DEBUG] Converted end to local tz: {end}")

                event.date = start.date()

                if not data.get('preserveTime', False):
                    event.start_time = start.time()
                    if end:
                        event.end_time = end.time()

            # ✅ This must run in both branches
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

@login_required
def group_create(request):
    if request.method == "POST":
        name = request.POST.get("name")
        desc = request.POST.get("description")
        if not name:
            messages.error(request, "Group must have a name.")
            return redirect('home')
        
        # Create group
        group = Group.objects.create(
            name=name,
            description=desc or "",
            creator=request.user
        )
        # Add creator as admin/member
        GroupMembership.objects.create(
            group=group,
            user=request.user,
            is_admin=True
        )
        messages.success(request, f"Group '{name}' created.")
        return redirect('home')
    return redirect('home')

@login_required
def group_invite(request, group_id):
    # Only admins can invite
    group = get_object_or_404(Group, id=group_id)
    membership = GroupMembership.objects.filter(group=group, user=request.user, is_admin=True).first()
    if not membership:
        messages.error(request, "Only group admins can invite users.")
        return redirect('home')
        
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        invitee = get_object_or_404(User, id=user_id)
        
        # Prevent inviting current members
        if GroupMembership.objects.filter(group=group, user=invitee).exists():
            messages.info(request, f"{invitee.username} is already in the group.")
            return redirect('home')
            
        # Check for existing invitation of any status
        existing_invitation = GroupInvitation.objects.filter(
            group=group, 
            invited_user=invitee
        ).first()
        
        if existing_invitation:
            # If it was previously accepted/declined, change status back to pending
            if existing_invitation.status in ['accepted', 'declined']:
                existing_invitation.status = 'pending'
                existing_invitation.invited_by = request.user
                existing_invitation.invited_at = timezone.now()
                existing_invitation.save()
                messages.success(request, f"Invitation sent to {invitee.username}.")
            else:
                # It's already pending
                messages.info(request, f"{invitee.username} has already been invited to this group.")
        else:
            # Create new invitation if none exists
            GroupInvitation.objects.create(
                group=group, 
                invited_user=invitee, 
                invited_by=request.user
            )
            messages.success(request, f"Invitation sent to {invitee.username}.")
            
            # Create notification for the invitee
            Notification.objects.create(
                user=invitee,
                message=f"{request.user.username} invited you to join the group '{group.name}'."
            )
            
    return redirect('home')

@login_required
def group_accept_invite(request, invitation_id):
    """
    View for accepting a group invitation
    """
    if request.method == 'POST':
        try:
            # Get the invitation and verify it's for this user
            invitation = get_object_or_404(
                GroupInvitation,
                id=invitation_id,
                invited_user=request.user,
                status='pending'
            )
            
            # Use transaction to ensure data consistency
            with transaction.atomic():
                # Create the group membership
                GroupMembership.objects.create(
                    group=invitation.group,
                    user=request.user,
                    is_admin=False,
                    show_in_calendar=True  # Default to showing in calendar
                )
                
                # Update invitation status
                invitation.status = 'accepted'
                invitation.save()
                
                # Create notification for the inviter
                Notification.objects.create(
                    user=invitation.invited_by,
                    message=f"{request.user.username} accepted your invitation to join {invitation.group.name}"
                )
                
                messages.success(request, f"You have successfully joined {invitation.group.name}")
                
        except IntegrityError:
            messages.error(request, "You are already a member of this group")
        except Exception as e:
            messages.error(request, f"Error accepting invitation: {str(e)}")
    else:
        invitation = get_object_or_404(GroupInvitation, id=invitation_id, invited_user=request.user)
        if invitation.status == "pending":
            # Accepting invitation
            GroupMembership.objects.create(group=invitation.group, user=request.user)
            invitation.status = "accepted"
            invitation.save()
            messages.success(request, f"You joined group '{invitation.group.name}'.")
    return redirect('home')

@login_required
def group_decline_invite(_inviterequest, invitation_id):
    """
    View for declining a group invitation
    """
    if request.method == 'POST':
        try:
            # Get the invitation and verify it's for this user
            invitation = get_object_or_404(
                GroupInvitation,
                id=invitation_id,
                invited_user=request.user,
                status='pending'
            )
            
            # Update invitation status
            invitation.status = 'declined'
            invitation.save()
            
            # Create notification for the inviter
            Notification.objects.create(
                user=invitation.invited_by,
                message=f"{request.user.username} declined your invitation to join {invitation.group.name}"
            )
            
            messages.success(request, f"You have declined the invitation to {invitation.group.name}")
            
        except Exception as e:
            messages.error(request, f"Error declining invitation: {str(e)}")
    else:
        invitation = get_object_or_404(GroupInvitation, id=invitation_id, invited_user=request.user)
        if invitation.status == "pending":
            invitation.status = "declined"
            invitation.save()
            messages.info(request, f"You declined invite to '{invitation.group.name}'.")
    return redirect('home')

@login_required
def group_detail(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    # Check if user is member
    is_member = GroupMembership.objects.filter(group=group, user=request.user).exists()
    if not is_member:
        messages.error(request, "You are not a member of this group.")
        return redirect('home')
        
    # Get group events
    group_events = Event.objects.filter(group=group).order_by('date', 'start_time')
    
    # Get members
    members = GroupMembership.objects.filter(group=group).select_related('user')
    
    return render(request, 'schedules/home.html', {
        'group': group,
        'events': group_events,
        'members': members,
        'is_admin': GroupMembership.objects.filter(group=group, user=request.user, is_admin=True).exists()
    })

@login_required
def leave_group(request, group_id):
    if request.method != 'POST':
        messages.info(request, "You must use the Leave Group button.")
        return redirect('group_detail', group_id=group_id)

    group = get_object_or_404(Group, id=group_id)
    membership = get_object_or_404(GroupMembership, group=group, user=request.user)

    membership.delete()
    messages.success(request, f"You have left the group '{group.name}'.")
    return redirect('home')


@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        bio = request.POST.get("bio", "")
        profile.bio = bio
        profile.save()

    # Event Category Counts
    categories = Event.objects.filter(user=request.user).values('category').annotate(count=Count('id'))
    category_labels = [c['category'].capitalize() for c in categories]
    category_counts = [c['count'] for c in categories]

    # Events Per Weekday (0 = Monday, 6 = Sunday)
    weekday_counts_raw = [0] * 7
    for e in Event.objects.filter(user=request.user):
        weekday_counts_raw[e.date.weekday()] += 1
    weekday_labels = list(calendar.day_name)
    weekday_counts = weekday_counts_raw

    # Duration Buckets
    duration_labels = ["<30 mins", "30–60 mins", "1–2 hrs", ">2 hrs"]
    duration_counts = [0, 0, 0, 0]
    for e in Event.objects.filter(user=request.user):
        duration = datetime.combine(e.date, e.end_time) - datetime.combine(e.date, e.start_time)
        minutes = duration.total_seconds() / 60
        if minutes < 30:
            duration_counts[0] += 1
        elif minutes < 60:
            duration_counts[1] += 1
        elif minutes < 120:
            duration_counts[2] += 1
        else:
            duration_counts[3] += 1

    # Events Per Month
    monthly = Event.objects.filter(user=request.user)
    month_labels = [calendar.month_name[i] for i in range(1, 13)]
    month_counts = [0] * 12
    for e in monthly:
        month_counts[e.date.month - 1] += 1

    return render(request, 'schedules/profile.html', {
        "profile": profile,
        "category_labels": category_labels,
        "category_counts": category_counts,
        "weekday_labels": weekday_labels,
        "weekday_counts": weekday_counts,
        "duration_labels": duration_labels,
        "duration_counts": duration_counts,
        "month_labels": month_labels,
        "month_counts": month_counts
    })

@login_required
def view_user_profile(request, user_id):
    target_user = get_object_or_404(User, id=user_id)

    # Check if the user is connected
    is_connected = Connection.objects.filter(user=request.user, connected_to=target_user).exists()
    if not is_connected:
        messages.error(request, "You can only view the profile of users you are connected with.")
        return redirect('my_connections')

    # Load the profile and recent events
    target_profile, _ = UserProfile.objects.get_or_create(user=target_user)
    target_events = Event.objects.filter(user=target_user).order_by('-date')[:10]  # last 10 events

    return render(request, 'schedules/view_user_profile.html', {
        'target_user': target_user,
        'target_profile': target_profile,
        'target_events': target_events,
    })

@csrf_exempt
@login_required
def ask_ai(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            question = data.get("question", "").strip().lower()

            # 💡 SMART SUGGESTIONS: Free time detection
            match = re.search(r'(\d+)\s*(minute|hour)', question)
            if ("free" in question or "available" in question) and match:
                value = int(match.group(1))
                unit = match.group(2)
                duration = value * 60 if unit == "hour" else value

                user_events = Event.objects.filter(user=request.user).order_by('date', 'start_time')
                events = []
                for e in user_events:
                    start_dt = datetime.combine(e.date, e.start_time)
                    end_dt = datetime.combine(e.date, e.end_time)
                    events.append({'start_time': start_dt, 'end_time': end_dt})

                slots = find_available_slots(events, duration)

                return JsonResponse({
                    "answer_type": "suggestion",
                    "title": "Here are your available time slots:",
                    "slots": [
                        {
                            "start": slot["start"].strftime("%Y-%m-%d %H:%M"),
                            "end": slot["end"].strftime("%Y-%m-%d %H:%M")
                        }
                        for slot in slots
                    ]
                })

            # ⚠️ CONFLICT DETECTION
            if "conflict" in question or "overlap" in question:
                user_events = Event.objects.filter(user=request.user).order_by('date', 'start_time')
                formatted = []
                for e in user_events:
                    formatted.append({
                        "title": e.title,
                        "start_time": datetime.combine(e.date, e.start_time),
                        "end_time": datetime.combine(e.date, e.end_time)
                    })

                conflicts = find_conflicts(formatted)

                if not conflicts:
                    return JsonResponse({"answer": "✅ No overlapping events found. You're all clear!"})

                return JsonResponse({
                    "answer_type": "conflict_report",
                    "title": "⚠️ Conflicting Events Found",
                    "conflicts": conflicts
                })



            # 🤖 Default: fallback to Mixtral AI assistant
            user_events = Event.objects.filter(user=request.user).order_by('date', 'start_time')
            event_lines = [f"- {e.title} on {e.date} from {e.start_time} to {e.end_time}" for e in user_events[:10]]
            event_context = "\n".join(event_lines) or "(No events found.)"

                # Compose prompt
            prompt = (
                "You are a scheduling assistant. The user may ask to create a new event or ask about upcoming events or existing ones.\n"
                "If they want to create an event, respond ONLY with JSON like:\n"
                '{\"title\": \"Gym\", \"date\": \"2025-04-28\", \"start_time\": \"18:00\", \"end_time\": \"20:00\"}\n'
                "Do NOT add explanations or format it like a message. Only output JSON.\n"
                "If you're unsure, say: I need more information.\n\n"
                " Use the events below to answer any questions about their schedule."
                f"Events:\n{event_context or 'No events yet.'}\n\n"
                f"User: {question}\nAssistant:"
            )

                # Call Mixtral via /api/generate
            response = requests.post("http://localhost:11434/api/generate", json={
                "model": "mixtral",
                "prompt": prompt,
                "stream": False
            })

            response.raise_for_status()
            reply = response.json().get("response", "").strip()
            print("🧠 Raw AI Reply:", repr(reply))

            # Try parsing JSON for new event
            try:
                json_match = re.search(r'\{[^{}]+\}', reply)
                if json_match:
                    event_data = json.loads(json_match.group())
                    if all(k in event_data for k in ["title", "date", "start_time", "end_time"]):
                        Event.objects.create(
                            user=request.user,
                            title=event_data["title"],
                            date=event_data["date"],
                            start_time=event_data["start_time"],
                            end_time=event_data["end_time"],
                            description="(Created by AI Assistant)"
                        )
                        return JsonResponse({"answer": f"✅ Event '{event_data['title']}' was successfully created!"})
            except Exception as parse_err:
                print("❌ JSON parse error:", parse_err)

            return JsonResponse({"answer": reply or "🤖 I couldn't understand that. Please try again."})

        except Exception as e:
            import traceback
            print("🔥 Error in ask_ai():")
            traceback.print_exc()
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=400)

@login_required
@require_POST
def toggle_group_visibility(request, group_id):
    """
    Toggle whether a group's events are visible in the user's calendar view.
    This affects only the current user's view of the group events.
    """
    try:
        membership = GroupMembership.objects.get(
            group_id=group_id,
            user=request.user
        )
        visibility = request.POST.get('visibility') == 'true'
        membership.show_in_calendar = visibility
        membership.save()
        return JsonResponse({'success': True})
    except GroupMembership.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Membership not found'}, status=404)

def find_available_slots(events, duration_minutes):
    """Find available time slots based on sorted event list."""
    slots = []
    events = sorted(events, key=lambda e: e['start_time'])
    day_start = datetime.combine(events[0]['start_time'].date(), datetime.min.time()) + timedelta(hours=8)
    day_end = datetime.combine(events[0]['start_time'].date(), datetime.min.time()) + timedelta(hours=22)

    # Check for slot before the first event
    if (events[0]['start_time'] - day_start).total_seconds() >= duration_minutes * 60:
        slots.append({'start': day_start, 'end': events[0]['start_time']})

    for i in range(len(events) - 1):
        gap = (events[i+1]['start_time'] - events[i]['end_time']).total_seconds()
        if gap >= duration_minutes * 60:
            slots.append({'start': events[i]['end_time'], 'end': events[i+1]['start_time']})

    # Check for slot after the last event
    if (day_end - events[-1]['end_time']).total_seconds() >= duration_minutes * 60:
        slots.append({'start': events[-1]['end_time'], 'end': day_end})

    return slots

def find_conflicts(events):
    """Return list of overlapping event pairs"""
    conflicts = []
    events = sorted(events, key=lambda e: e['start_time'])

    for i in range(len(events) - 1):
        current = events[i]
        next_event = events[i + 1]
        if current['end_time'] > next_event['start_time']:
            conflicts.append({
                "date": current['start_time'].date().isoformat(),
                "events": [current['title'], next_event['title']],
                "times": [
                    f"{current['start_time'].strftime('%H:%M')} - {current['end_time'].strftime('%H:%M')}",
                    f"{next_event['start_time'].strftime('%H:%M')} - {next_event['end_time'].strftime('%H:%M')}"
                ]
            })
    return conflicts
