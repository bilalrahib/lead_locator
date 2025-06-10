from django.shortcuts import get_object_or_404
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from datetime import timedelta
import logging

from .models import AffiliateProfile, AffiliateResource, CommissionLedger
from .serializers import (
    AffiliateApplicationSerializer, AffiliateProfileSerializer, PayoutInfoSerializer,
    AffiliateDashboardSerializer, AffiliateResourceSerializer, CommissionLedgerSerializer,
    EarningsSummarySerializer
)
from .services import AffiliateService, CommissionService, ReferralService

logger = logging.getLogger(__name__)


class AffiliateApplicationView(generics.CreateAPIView):
    """
    API endpoint for affiliate application submission.
    """
    serializer_class = AffiliateApplicationSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """Handle affiliate application creation."""
        # Check if user already has affiliate profile
        if hasattr(request.user, 'affiliate_profile'):
            return Response(
                {'error': 'You already have an affiliate application'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            try:
                affiliate = AffiliateService.create_affiliate_application(
                    user=request.user,
                    application_data=serializer.validated_data
                )
                
                response_serializer = AffiliateProfileSerializer(affiliate)
                return Response(
                    {
                        'message': 'Affiliate application submitted successfully',
                        'affiliate': response_serializer.data
                    },
                    status=status.HTTP_201_CREATED
                )
                
            except ValueError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                logger.error(f"Error creating affiliate application: {e}")
                return Response(
                    {'error': 'Failed to submit application'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AffiliateDashboardView(APIView):
    """
    API endpoint for affiliate dashboard data.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get comprehensive affiliate dashboard data."""
        try:
            # Check if user is an approved affiliate
            if not hasattr(request.user, 'affiliate_profile'):
                return Response(
                    {'error': 'User is not an affiliate'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            affiliate = request.user.affiliate_profile
            
            if not affiliate.is_active:
                return Response(
                    {'error': 'Affiliate account is not active'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get dashboard data
            dashboard_data = AffiliateService.get_affiliate_dashboard_data(affiliate)
            
            # Serialize data
            from .serializers.affiliate_serializers import (
                ReferralClickSerializer, ReferralConversionSerializer
            )
            
            response_data = {
                'profile': AffiliateProfileSerializer(dashboard_data['profile']).data,
                'recent_clicks': ReferralClickSerializer(dashboard_data['recent_clicks'], many=True).data,
                'recent_conversions': ReferralConversionSerializer(dashboard_data['recent_conversions'], many=True).data,
                'earnings_summary': dashboard_data['earnings_summary'],
                'performance_metrics': dashboard_data['performance_metrics'],
                'available_resources': AffiliateResourceSerializer(dashboard_data['available_resources'], many=True).data
            }
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"Error getting affiliate dashboard: {e}")
            return Response(
                {'error': 'Failed to load dashboard'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AffiliateProfileView(generics.RetrieveUpdateAPIView):
    """
    API endpoint for affiliate profile management.
    """
    serializer_class = AffiliateProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Get affiliate profile for current user."""
        try:
            return self.request.user.affiliate_profile
        except AffiliateProfile.DoesNotExist:
            return None

    def retrieve(self, request, *args, **kwargs):
        """Get affiliate profile."""
        instance = self.get_object()
        if instance is None:
            return Response(
                {'error': 'Affiliate profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """Update affiliate profile."""
        instance = self.get_object()
        if instance is None:
            return Response(
                {'error': 'Affiliate profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PayoutInfoView(APIView):
    """
    API endpoint for managing payout information.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get current payout information."""
        try:
            affiliate = request.user.affiliate_profile
            serializer = PayoutInfoSerializer(affiliate)
            return Response(serializer.data)
            
        except AffiliateProfile.DoesNotExist:
            return Response(
                {'error': 'Affiliate profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def put(self, request):
        """Update payout information."""
        try:
            affiliate = request.user.affiliate_profile
            serializer = PayoutInfoSerializer(affiliate, data=request.data, partial=True)
            
            if serializer.is_valid():
                # Use service to update payout info securely
                success = AffiliateService.update_payout_info(
                    affiliate=affiliate,
                    payout_data=serializer.validated_data
                )
                
                if success:
                    updated_serializer = PayoutInfoSerializer(affiliate)
                    return Response({
                        'message': 'Payout information updated successfully',
                        'payout_info': updated_serializer.data
                    })
                else:
                    return Response(
                        {'error': 'Failed to update payout information'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except AffiliateProfile.DoesNotExist:
            return Response(
                {'error': 'Affiliate profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class CommissionHistoryView(generics.ListAPIView):
    """
    API endpoint for commission history.
    """
    serializer_class = CommissionLedgerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get commission history for current user."""
        try:
            affiliate = self.request.user.affiliate_profile
            return CommissionLedger.objects.filter(
                affiliate=affiliate
            ).order_by('-created_at')
        except AffiliateProfile.DoesNotExist:
            return CommissionLedger.objects.none()

    def list(self, request, *args, **kwargs):
        """List commission history with summary."""
        try:
            affiliate = request.user.affiliate_profile
            
            # Get commission history
            queryset = self.get_queryset()
            page = self.paginate_queryset(queryset)
            
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                response = self.get_paginated_response(serializer.data)
            else:
                serializer = self.get_serializer(queryset, many=True)
                response = Response(serializer.data)
            
            # Add earnings summary
            earnings_summary = AffiliateService.get_earnings_summary(affiliate)
            response.data['earnings_summary'] = earnings_summary
            
            return response
            
        except AffiliateProfile.DoesNotExist:
            return Response(
                {'error': 'Affiliate profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class AffiliateResourcesView(generics.ListAPIView):
    """
    API endpoint for affiliate resources.
    """
    serializer_class = AffiliateResourceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get available affiliate resources."""
        return AffiliateResource.objects.filter(is_active=True).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        """List resources and track access."""
        # Verify user is an affiliate
        try:
            affiliate = request.user.affiliate_profile
            if not affiliate.is_active:
                return Response(
                    {'error': 'Affiliate account is not active'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except AffiliateProfile.DoesNotExist:
            return Response(
                {'error': 'Affiliate access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().list(request, *args, **kwargs)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def download_resource(request, resource_id):
    """
    Track resource download.
    """
    try:
        affiliate = request.user.affiliate_profile
        
        if not affiliate.is_active:
            return Response(
                {'error': 'Affiliate account is not active'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Track download
        AffiliateService.track_resource_download(resource_id, affiliate)
        
        return Response({'message': 'Download tracked successfully'})
        
    except AffiliateProfile.DoesNotExist:
        return Response(
            {'error': 'Affiliate access required'},
            status=status.HTTP_403_FORBIDDEN
        )
    except Exception as e:
        logger.error(f"Error tracking resource download: {e}")
        return Response(
            {'error': 'Failed to track download'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def affiliate_analytics(request):
    """
    Get detailed affiliate analytics.
    """
    try:
        affiliate = request.user.affiliate_profile
        
        if not affiliate.is_active:
            return Response(
                {'error': 'Affiliate account is not active'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get analytics period from query params
        days = int(request.GET.get('days', 30))
        
        # Get referral analytics
        analytics = ReferralService.get_referral_analytics(affiliate, days)
        
        return Response(analytics)
        
    except AffiliateProfile.DoesNotExist:
        return Response(
            {'error': 'Affiliate profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error getting affiliate analytics: {e}")
        return Response(
            {'error': 'Failed to load analytics'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def affiliate_leaderboard(request):
    """
    Get public affiliate leaderboard.
    """
    try:
        limit = int(request.GET.get('limit', 10))
        leaderboard = AffiliateService.get_affiliate_leaderboard(limit)
        
        return Response({
            'leaderboard': leaderboard,
            'updated_at': timezone.now()
        })
        
    except Exception as e:
        logger.error(f"Error getting affiliate leaderboard: {e}")
        return Response(
            {'error': 'Failed to load leaderboard'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def affiliate_health_check(request):
    """
    Health check for affiliates app.
    """
    try:
        # Test database connection
        affiliate_count = AffiliateProfile.objects.count()
        
        return Response({
            'status': 'healthy',
            'total_affiliates': affiliate_count,
            'app': 'affiliates'
        })
        
    except Exception as e:
        logger.error(f"Affiliates health check failed: {e}")
        return Response({
            'status': 'unhealthy',
            'error': str(e),
            'app': 'affiliates'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)