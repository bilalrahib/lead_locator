from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import cache_page
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
import logging

# Import models
from .models import SupportTicket, WeatherLocation, SystemNotification, ContactMessage, SubscriptionPlan

# Import serializers
from .serializers import (
    SupportTicketSerializer, SupportTicketCreateSerializer, WeatherLocationSerializer,
    SystemNotificationSerializer, ContactMessageSerializer, WeatherDataSerializer,
    SubscriptionPlanSerializer, HomepageDataSerializer
)

# Import services
from .services import WeatherService, EmailService, NotificationService

logger = logging.getLogger(__name__)


# Public Views (No Authentication Required)
class HomepageView(TemplateView):
    """
    Public homepage view.
    """
    template_name = 'project_core/homepage.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get active subscription plans
        plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price')
        
        # Get homepage notifications
        notification_service = NotificationService()
        notifications = notification_service.get_active_notifications(show_on_homepage=True)
        
        context.update({
            'subscription_plans': plans,
            'notifications': notifications,
            'features': self._get_feature_list(),
            'testimonials': self._get_testimonials(),
        })
        
        return context

    def _get_feature_list(self):
        """Get list of key features for homepage."""
        return [
            {
                'title': 'Smart Location Discovery',
                'description': 'Find optimal vending locations using AI and geospatial data',
                'icon': 'location'
            },
            {
                'title': 'AI-Powered Sales Scripts',
                'description': 'Generate custom sales scripts tailored to your target locations',
                'icon': 'script'
            },
            {
                'title': 'Lead Management',
                'description': 'Organize and track your leads with our comprehensive CRM',
                'icon': 'leads'
            },
            {
                'title': 'Operations Dashboard',
                'description': 'Manage your placed machines and track performance',
                'icon': 'dashboard'
            },
            {
                'title': 'Affiliate Program',
                'description': 'Earn commissions by referring new customers',
                'icon': 'affiliate'
            },
            {
                'title': 'Pro Tools',
                'description': 'Advanced tools for business owners managing multiple clients',
                'icon': 'pro'
            }
        ]

    def _get_testimonials(self):
        """Get testimonials for homepage."""
        return [
            {
                'name': 'John Smith',
                'business': 'Vending Solutions LLC',
                'text': 'Vending Hive helped me find 20 new locations in just 2 months. The AI scripts are incredibly effective!',
                'rating': 5
            },
            {
                'name': 'Sarah Johnson',
                'business': 'Quick Snack Ventures',
                'text': 'The location discovery tool is a game-changer. I\'ve tripled my machine placements since joining.',
                'rating': 5
            },
            {
                'name': 'Mike Rodriguez',
                'business': 'Elite Vending Co.',
                'text': 'The pro dashboard makes managing my clients\' locations effortless. Highly recommended!',
                'rating': 5
            }
        ]


# API Views
class HomepageDataAPIView(APIView):
    """
    API endpoint for homepage data.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            # Get subscription plans
            plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price')
            plans_serializer = SubscriptionPlanSerializer(plans, many=True)
            
            # Get notifications
            notification_service = NotificationService()
            notifications = notification_service.get_active_notifications(show_on_homepage=True)
            notifications_serializer = SystemNotificationSerializer(notifications, many=True)
            
            data = {
                'company_name': 'Vending Hive',
                'tagline': 'AI-Powered SaaS Platform for Vending Machine Operators',
                'features': HomepageView()._get_feature_list(),
                'subscription_plans': plans_serializer.data,
                'testimonials': HomepageView()._get_testimonials(),
                'notifications': notifications_serializer.data
            }
            
            serializer = HomepageDataSerializer(data)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error in HomepageDataAPIView: {e}")
            return Response(
                {'error': 'Unable to fetch homepage data'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ContactMessageCreateAPIView(generics.CreateAPIView):
    """
    API endpoint for creating contact messages.
    """
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        contact_message = serializer.save()
        
        # Send notification email to admin
        try:
            email_service = EmailService()
            email_service.send_contact_form_notification(contact_message)
        except Exception as e:
            logger.error(f"Failed to send contact form notification: {e}")
        
        logger.info(f"Contact message created from {contact_message.email}")


# Protected Views (Authentication Required)
class SupportTicketListCreateAPIView(generics.ListCreateAPIView):
    """
    API endpoint for listing and creating support tickets.
    """
    serializer_class = SupportTicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SupportTicket.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SupportTicketCreateSerializer
        return SupportTicketSerializer

    def perform_create(self, serializer):
        ticket = serializer.save(user=self.request.user)
        
        # Send confirmation email
        try:
            email_service = EmailService()
            email_service.send_support_ticket_confirmation(ticket)
        except Exception as e:
            logger.error(f"Failed to send support ticket confirmation: {e}")
        
        logger.info(f"Support ticket created by {self.request.user.username}: {ticket.id}")


class SupportTicketDetailAPIView(generics.RetrieveAPIView):
    """
    API endpoint for retrieving support ticket details.
    """
    serializer_class = SupportTicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SupportTicket.objects.filter(user=self.request.user)


class WeatherLocationAPIView(APIView):
    """
    API endpoint for managing user's weather location.
    Custom APIView to handle GET, POST, and PUT operations.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = WeatherLocationSerializer

    def get(self, request):
        """Get user's weather location."""
        try:
            weather_location = WeatherLocation.objects.get(user=request.user)
            serializer = self.serializer_class(weather_location)
            return Response(serializer.data)
        except WeatherLocation.DoesNotExist:
            return Response(
                {'detail': 'Weather location not configured'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error retrieving weather location: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request):
        """Create user's weather location."""
        try:
            # Check if user already has a weather location
            if WeatherLocation.objects.filter(user=request.user).exists():
                return Response(
                    {'error': 'Weather location already exists. Use PUT to update.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = self.serializer_class(data=request.data, context={'request': request})
            if serializer.is_valid():
                weather_location = serializer.save(user=request.user)
                self._geocode_address(weather_location)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating weather location: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def put(self, request):
        """Update user's weather location."""
        try:
            weather_location = WeatherLocation.objects.get(user=request.user)
            serializer = self.serializer_class(
                weather_location, 
                data=request.data, 
                context={'request': request}
            )
            if serializer.is_valid():
                weather_location = serializer.save()
                self._geocode_address(weather_location)
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except WeatherLocation.DoesNotExist:
            return Response(
                {'error': 'Weather location not found. Use POST to create.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error updating weather location: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _geocode_address(self, weather_location):
        """Geocode address to get coordinates and location details."""
        try:
            # This would typically use a geocoding service
            # For now, we'll just log that we need to implement this
            logger.info(f"Need to geocode address: {weather_location.address}")
            # TODO: Implement geocoding using Google Maps API or similar
        except Exception as e:
            logger.error(f"Error geocoding address: {e}")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_weather_data(request):
    """
    API endpoint for getting weather data for user's location.
    """
    try:
        weather_location = WeatherLocation.objects.get(user=request.user)
        weather_service = WeatherService()
        
        if weather_location.coordinates:
            weather_data = weather_service.get_weather_by_coordinates(
                float(weather_location.latitude),
                float(weather_location.longitude)
            )
        else:
            weather_data = weather_service.get_weather_by_zip(weather_location.zip_code)
        
        if weather_data:
            serializer = WeatherDataSerializer(weather_data)
            return Response(serializer.data)
        else:
            return Response(
                {'error': 'Unable to fetch weather data'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
            
    except WeatherLocation.DoesNotExist:
        return Response(
            {'error': 'Weather location not configured'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error fetching weather data: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class SystemNotificationListAPIView(generics.ListAPIView):
    """
    API endpoint for listing active system notifications.
    """
    serializer_class = SystemNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        notification_service = NotificationService()
        return notification_service.get_active_notifications()


# Dashboard Views
@method_decorator(login_required, name='dispatch')
class DashboardView(TemplateView):
    """
    Main dashboard view for authenticated users.
    """
    template_name = 'project_core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get user's recent support tickets
        recent_tickets = SupportTicket.objects.filter(user=user)[:5]
        
        # Get user's weather location
        try:
            weather_location = WeatherLocation.objects.get(user=user)
        except WeatherLocation.DoesNotExist:
            weather_location = None
        
        # Get active notifications
        notification_service = NotificationService()
        notifications = notification_service.get_active_notifications()
        
        context.update({
            'recent_tickets': recent_tickets,
            'weather_location': weather_location,
            'notifications': notifications,
        })
        
        return context


# Health Check Views
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Simple health check endpoint.
    """
    try:
        # Basic database check
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        
        return Response({
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'version': '1.0.0'
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return Response(
            {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def system_status(request):
    """
    System status endpoint with more detailed information.
    """
    try:
        from django.db import connection
        from django.core.cache import cache
        
        # Database check
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM django_migrations")
        db_status = "healthy"
        
        # Cache check (basic check without redis dependency)
        cache_status = "not_configured"
        try:
            cache_key = 'health_check_cache'
            cache.set(cache_key, 'test', 10)
            cache_value = cache.get(cache_key)
            cache_status = "healthy" if cache_value == 'test' else "unhealthy"
        except Exception:
            cache_status = "not_configured"
        
        # Service checks
        weather_service = WeatherService()
        weather_status = "healthy" if weather_service.api_key else "no_api_key"
        
        return Response({
            'status': 'healthy',
            'services': {
                'database': db_status,
                'cache': cache_status,
                'weather_service': weather_status,
            },
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"System status check failed: {e}")
        return Response(
            {
                'status': 'error',
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )