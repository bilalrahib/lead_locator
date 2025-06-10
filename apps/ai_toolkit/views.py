from django.shortcuts import get_object_or_404
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.utils import timezone
import logging

from .models import GeneratedScript, ScriptTemplate, JarvisConversation, BusinessCalculation
from .serializers import (
    GeneratedScriptSerializer, ScriptGenerationRequestSerializer,
    ScriptRegenerationRequestSerializer, ScriptTemplateSerializer,
    TemplateUsageRequestSerializer, JarvisConversationSerializer,
    JarvisChatRequestSerializer, LogoGenerationRequestSerializer,
    SocialMediaRequestSerializer, LeadValueCalculationSerializer,
    SnackPriceCalculationSerializer, BusinessCalculationSerializer
)
from .services import ScriptGeneratorService, JarvisService, BusinessToolsService

logger = logging.getLogger(__name__)


# Script Generation Views
class GeneratedScriptListAPIView(generics.ListAPIView):
    """
    API endpoint for listing user's generated scripts.
    """
    serializer_class = GeneratedScriptSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = GeneratedScript.objects.filter(user=self.request.user)
        
        # Filter by script type if specified
        script_type = self.request.query_params.get('script_type')
        if script_type:
            queryset = queryset.filter(script_type=script_type)
        
        # Filter by machine type if specified
        machine_type = self.request.query_params.get('machine_type')
        if machine_type:
            queryset = queryset.filter(target_machine_type=machine_type)
        
        return queryset.order_by('-created_at')


class ScriptGenerationAPIView(APIView):
    """
    API endpoint for generating new scripts.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Generate a new script."""
        serializer = ScriptGenerationRequestSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            script_service = ScriptGeneratorService()
            script = script_service.generate_script(
                user=request.user,
                script_type=serializer.validated_data['script_type'],
                target_location_name=serializer.validated_data['target_location_name'],
                target_location_category=serializer.validated_data.get('target_location_category', ''),
                target_machine_type=serializer.validated_data['target_machine_type'],
                custom_requirements=serializer.validated_data.get('custom_requirements', '')
            )

            script_serializer = GeneratedScriptSerializer(script)
            return Response({
                'script': script_serializer.data,
                'message': 'Script generated successfully'
            }, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error generating script for {request.user.email}: {e}")
            return Response({
                'error': 'Failed to generate script. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ScriptRegenerationAPIView(APIView):
    """
    API endpoint for regenerating existing scripts.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Regenerate an existing script."""
        serializer = ScriptRegenerationRequestSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            script = GeneratedScript.objects.get(
                id=serializer.validated_data['script_id'],
                user=request.user
            )
            
            script_service = ScriptGeneratorService()
            updated_script = script_service.regenerate_script(
                script=script,
                custom_requirements=serializer.validated_data.get('custom_requirements', '')
            )

            script_serializer = GeneratedScriptSerializer(updated_script)
            return Response({
                'script': script_serializer.data,
                'message': 'Script regenerated successfully'
            })

        except GeneratedScript.DoesNotExist:
            return Response({
                'error': 'Script not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error regenerating script for {request.user.email}: {e}")
            return Response({
                'error': 'Failed to regenerate script. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ScriptTemplateListAPIView(generics.ListAPIView):
    """
    API endpoint for listing available script templates.
    """
    serializer_class = ScriptTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        script_service = ScriptGeneratorService()
        return script_service.get_available_templates(self.request.user)


class TemplateUsageAPIView(APIView):
    """
    API endpoint for using script templates.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Create script from template."""
        serializer = TemplateUsageRequestSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            template = ScriptTemplate.objects.get(
                id=serializer.validated_data['template_id'],
                is_active=True
            )
            
            script_service = ScriptGeneratorService()
            script = script_service.use_template(
                user=request.user,
                template=template,
                target_location_name=serializer.validated_data['target_location_name'],
                target_location_category=serializer.validated_data.get('target_location_category', ''),
                target_machine_type=serializer.validated_data.get('target_machine_type', '')
            )

            script_serializer = GeneratedScriptSerializer(script)
            return Response({
                'script': script_serializer.data,
                'message': 'Script created from template successfully'
            }, status=status.HTTP_201_CREATED)

        except ScriptTemplate.DoesNotExist:
            return Response({
                'error': 'Template not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error using template for {request.user.email}: {e}")
            return Response({
                'error': 'Failed to create script from template. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# JARVIS AI Assistant Views
class JarvisChatAPIView(APIView):
    """
    API endpoint for JARVIS AI chat.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Chat with JARVIS AI assistant."""
        serializer = JarvisChatRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            jarvis_service = JarvisService()
            response_data = jarvis_service.chat(
                user=request.user,
                message=serializer.validated_data['message'],
                session_id=serializer.validated_data.get('session_id'),
                conversation_type=serializer.validated_data['conversation_type']
            )

            return Response(response_data)

        except ValueError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f"Error in JARVIS chat for {request.user.email}: {e}")
            return Response({
                'error': 'JARVIS is temporarily unavailable. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class JarvisConversationHistoryAPIView(generics.ListAPIView):
    """
    API endpoint for JARVIS conversation history.
    """
    serializer_class = JarvisConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = JarvisConversation.objects.filter(user=self.request.user)
        
        # Filter by session if specified
        session_id = self.request.query_params.get('session_id')
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        
        # Filter by conversation type if specified
        conversation_type = self.request.query_params.get('conversation_type')
        if conversation_type:
            queryset = queryset.filter(conversation_type=conversation_type)
        
        return queryset.order_by('-created_at')


class LogoGenerationAPIView(APIView):
    """
    API endpoint for logo generation prompts.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Generate logo creation prompt."""
        serializer = LogoGenerationRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            jarvis_service = JarvisService()
            logo_data = jarvis_service.generate_logo_prompt(
                user=request.user,
                business_name=serializer.validated_data['business_name'],
                style_preferences=serializer.validated_data.get('style_preferences', ''),
                color_preferences=serializer.validated_data.get('color_preferences', '')
            )

            return Response(logo_data)

        except ValueError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f"Error generating logo prompt for {request.user.email}: {e}")
            return Response({
                'error': 'Failed to generate logo prompt. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SocialMediaGenerationAPIView(APIView):
    """
    API endpoint for social media content generation.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Generate social media content."""
        serializer = SocialMediaRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            jarvis_service = JarvisService()
            content_data = jarvis_service.generate_social_media_content(
                user=request.user,
                platform=serializer.validated_data['platform'],
                content_type=serializer.validated_data['content_type'],
                business_focus=serializer.validated_data.get('business_focus', ''),
                target_audience=serializer.validated_data.get('target_audience', '')
            )

            return Response(content_data)

        except ValueError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f"Error generating social media content for {request.user.email}: {e}")
            return Response({
                'error': 'Failed to generate social media content. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Business Tools Views
class LeadValueCalculationAPIView(APIView):
    """
    API endpoint for lead value calculations.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Calculate lead value and ROI projections."""
        serializer = LeadValueCalculationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            business_tools_service = BusinessToolsService()
            calculation_data = serializer.to_internal_value(request.data)
            
            results = business_tools_service.calculate_lead_value(
                user=request.user,
                business_goals=calculation_data['business_goals'],
                pricing_model=calculation_data['pricing_model'],
                outreach_strategy=calculation_data['outreach_strategy']
            )

            return Response(results)

        except ValueError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f"Error in lead value calculation for {request.user.email}: {e}")
            return Response({
                'error': 'Failed to calculate lead value. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SnackPriceCalculationAPIView(APIView):
    """
    API endpoint for snack price calculations.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Calculate snack pricing and profit projections."""
        serializer = SnackPriceCalculationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            business_tools_service = BusinessToolsService()
            calculation_data = serializer.to_internal_value(request.data)
            
            results = business_tools_service.calculate_snack_pricing(
                user=request.user,
                snack_details=calculation_data['snack_details'],
                pricing_strategy=calculation_data['pricing_strategy'],
                location_details=calculation_data['location_details']
            )

            return Response(results)

        except ValueError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f"Error in snack price calculation for {request.user.email}: {e}")
            return Response({
                'error': 'Failed to calculate snack pricing. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BusinessCalculationHistoryAPIView(generics.ListAPIView):
    """
    API endpoint for business calculation history.
    """
    serializer_class = BusinessCalculationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = BusinessCalculation.objects.filter(user=self.request.user)
        
        # Filter by calculation type if specified
        calculation_type = self.request.query_params.get('calculation_type')
        if calculation_type:
            queryset = queryset.filter(calculation_type=calculation_type)
        
        return queryset.order_by('-created_at')


class BusinessCalculationDetailAPIView(generics.RetrieveUpdateAPIView):
    """
    API endpoint for individual business calculation details.
    """
    serializer_class = BusinessCalculationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BusinessCalculation.objects.filter(user=self.request.user)

    def get_object(self):
        return get_object_or_404(
            self.get_queryset(),
            id=self.kwargs['calculation_id']
        )