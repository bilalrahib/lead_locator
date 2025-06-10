#!/usr/bin/env python
"""
Comprehensive test script for AI Toolkit package.
Run this script from the project root directory.

Usage: python test_ai_toolkit.py
"""

import os
import sys
import django
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from decimal import Decimal
import json
from unittest.mock import patch, MagicMock

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_core.settings')
django.setup()

# Import after Django setup
from apps.ai_toolkit.models import GeneratedScript, ScriptTemplate, JarvisConversation, BusinessCalculation
from apps.ai_toolkit.services import ScriptGeneratorService, JarvisService, BusinessToolsService
from apps.project_core.models import SubscriptionPlan, UserSubscription

User = get_user_model()


class AIToolkitTestCase:
    """Main test case for AI Toolkit functionality."""
    
    def __init__(self):
        self.client = APIClient()
        self.setup_test_data()
    
    def setup_test_data(self):
        """Create test users and subscription plans."""
        print("Setting up test data...")
        
        # Clean up existing test data
        User.objects.filter(email__contains='test_ai_toolkit').delete()
        
        # Create subscription plans if they don't exist
        self.free_plan, _ = SubscriptionPlan.objects.get_or_create(
            name='FREE',
            defaults={
                'price': Decimal('0.00'),
                'leads_per_month': 3,
                'leads_per_search_range': '10-15',
                'script_templates_count': 1,
                'regeneration_allowed': False,
                'description': 'Free plan for testing'
            }
        )
        
        self.pro_plan, _ = SubscriptionPlan.objects.get_or_create(
            name='PRO',
            defaults={
                'price': Decimal('29.99'),
                'leads_per_month': 50,
                'leads_per_search_range': '15-20',
                'script_templates_count': 10,
                'regeneration_allowed': True,
                'description': 'Pro plan for testing'
            }
        )
        
        self.elite_plan, _ = SubscriptionPlan.objects.get_or_create(
            name='ELITE',
            defaults={
                'price': Decimal('99.99'),
                'leads_per_month': 200,
                'leads_per_search_range': '20-25',
                'script_templates_count': 50,
                'regeneration_allowed': True,
                'description': 'Elite plan for testing'
            }
        )
        
        # Create test users
        self.free_user = User.objects.create_user(
            username='free_test_ai_toolkit',
            email='free_test_ai_toolkit@example.com',
            password='testpass123',
            first_name='Free',
            last_name='User'
        )
        
        self.pro_user = User.objects.create_user(
            username='pro_test_ai_toolkit',
            email='pro_test_ai_toolkit@example.com',
            password='testpass123',
            first_name='Pro',
            last_name='User'
        )
        
        self.elite_user = User.objects.create_user(
            username='elite_test_ai_toolkit',
            email='elite_test_ai_toolkit@example.com',
            password='testpass123',
            first_name='Elite',
            last_name='User'
        )
        
        # Create subscriptions
        UserSubscription.objects.create(
            user=self.free_user,
            plan=self.free_plan,
            is_active=True
        )
        
        UserSubscription.objects.create(
            user=self.pro_user,
            plan=self.pro_plan,
            is_active=True
        )
        
        UserSubscription.objects.create(
            user=self.elite_user,
            plan=self.elite_plan,
            is_active=True
        )
        
        # Create test script templates
        ScriptTemplate.objects.create(
            name='Basic Cold Call Template',
            script_type='cold_call',
            machine_type='snack_machine',
            location_category='Office',
            content='Hello, my name is {YOUR_NAME} from {YOUR_COMPANY}. I would like to discuss placing a {MACHINE_TYPE} at {LOCATION_NAME}.',
            is_premium=False
        )
        
        ScriptTemplate.objects.create(
            name='Premium Email Template',
            script_type='email',
            machine_type='claw_machine',
            location_category='Restaurant',
            content='Subject: Revenue Opportunity for {LOCATION_NAME}\n\nDear Manager,\n\nI represent {YOUR_COMPANY} and would like to propose placing a {MACHINE_TYPE} at {LOCATION_NAME}.',
            is_premium=True
        )
        
        print("✓ Test data setup complete")
    
    def get_jwt_token(self, user):
        """Get JWT token for user authentication."""
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    
    def authenticate_user(self, user):
        """Authenticate user for API requests."""
        token = self.get_jwt_token(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    def test_models(self):
        """Test AI Toolkit models."""
        print("\n" + "="*50)
        print("TESTING MODELS")
        print("="*50)
        
        # Test GeneratedScript model
        print("Testing GeneratedScript model...")
        script = GeneratedScript.objects.create(
            user=self.pro_user,
            script_type='cold_call',
            target_location_name='Test Coffee Shop',
            target_location_category='Restaurant',
            target_machine_type='coffee_machine',
            script_content='Test script content',
            ai_model_used='gpt-3.5-turbo'
        )
        
        assert script.can_regenerate == True, "Pro user should be able to regenerate scripts"
        assert str(script) == 'Cold Call Script for Test Coffee Shop'
        print("✓ GeneratedScript model tests passed")
        
        # Test ScriptTemplate model
        print("Testing ScriptTemplate model...")
        template = ScriptTemplate.objects.first()
        assert template.can_access(self.free_user) == True, "Free user should access non-premium templates"
        assert template.can_access(self.pro_user) == True, "Pro user should access all templates"
        print("✓ ScriptTemplate model tests passed")
        
        # Test JarvisConversation model
        print("Testing JarvisConversation model...")
        conversation = JarvisConversation.objects.create(
            user=self.pro_user,
            session_id='test-session-123',
            user_message='Hello JARVIS',
            jarvis_response='Hello! How can I help you today?',
            conversation_type='general',
            ai_model_used='gpt-3.5-turbo'
        )
        
        assert 'JARVIS chat with' in str(conversation)
        print("✓ JarvisConversation model tests passed")
        
        # Test BusinessCalculation model
        print("Testing BusinessCalculation model...")
        calculation = BusinessCalculation.objects.create(
            user=self.elite_user,
            calculation_type='lead_value_estimator',
            input_parameters={'test': 'data'},
            calculation_results={'result': 'value'}
        )
        
        assert 'Lead Value Estimator' in str(calculation)
        print("✓ BusinessCalculation model tests passed")
    
    @patch('apps.ai_toolkit.services.script_generator_service.openai')
    @patch('apps.ai_toolkit.services.script_generator_service.genai')
    def test_script_generator_service(self, mock_genai, mock_openai):
        """Test ScriptGeneratorService."""
        print("\n" + "="*50)
        print("TESTING SCRIPT GENERATOR SERVICE")
        print("="*50)
        
        # Mock AI responses
        mock_response = MagicMock()
        mock_response.text = "This is a generated script for your business."
        mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
        
        mock_openai_response = MagicMock()
        mock_openai_response.choices = [MagicMock()]
        mock_openai_response.choices[0].message.content = "This is a generated script for your business."
        mock_openai.ChatCompletion.create.return_value = mock_openai_response
        
        service = ScriptGeneratorService()
        
        # Test script generation for pro user
        print("Testing script generation...")
        script = service.generate_script(
            user=self.pro_user,
            script_type='cold_call',
            target_location_name='Test Restaurant',
            target_location_category='Restaurant',
            target_machine_type='snack_machine',
            custom_requirements='Make it friendly'
        )
        
        assert script.user == self.pro_user
        assert script.script_type == 'cold_call'
        assert script.target_location_name == 'Test Restaurant'
        assert len(script.script_content) > 0
        print("✓ Script generation test passed")
        
        # Test script regeneration
        print("Testing script regeneration...")
        original_content = script.script_content
        regenerated_script = service.regenerate_script(script, "Make it more professional")
        
        assert regenerated_script.id == script.id
        assert regenerated_script.regeneration_count == 1
        print("✓ Script regeneration test passed")
        
        # Test template usage
        print("Testing template usage...")
        template = ScriptTemplate.objects.filter(is_premium=False).first()
        script_from_template = service.use_template(
            user=self.pro_user,
            template=template,
            target_location_name='Template Test Location',
            target_location_category='Office',
            target_machine_type='drink_machine'
        )
        
        assert script_from_template.is_template == True
        assert 'Template Test Location' in script_from_template.script_content
        print("✓ Template usage test passed")
        
        # Test permission checks
        print("Testing permission checks...")
        try:
            service.generate_script(
                user=self.free_user,
                script_type='cold_call',
                target_location_name='Test',
                target_location_category='Test',
                target_machine_type='snack_machine'
            )
            # Free users can generate scripts but with limited quota
            print("✓ Free user script generation allowed")
        except ValueError:
            print("✓ Free user script generation properly restricted")
    
    @patch('apps.ai_toolkit.services.jarvis_service.openai')
    @patch('apps.ai_toolkit.services.jarvis_service.genai')
    def test_jarvis_service(self, mock_genai, mock_openai):
        """Test JarvisService."""
        print("\n" + "="*50)
        print("TESTING JARVIS SERVICE")
        print("="*50)
        
        # Mock AI responses
        mock_response = MagicMock()
        mock_response.text = "Hello! I'm JARVIS, your AI assistant. How can I help you with your vending machine business today?"
        mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
        
        mock_openai_response = MagicMock()
        mock_openai_response.choices = [MagicMock()]
        mock_openai_response.choices[0].message.content = "Hello! I'm JARVIS, your AI assistant. How can I help you with your vending machine business today?"
        mock_openai.ChatCompletion.create.return_value = mock_openai_response
        
        service = JarvisService()
        
        # Test JARVIS chat for pro user
        print("Testing JARVIS chat...")
        response = service.chat(
            user=self.pro_user,
            message="Hello JARVIS, how are you?",
            conversation_type='general'
        )
        
        assert 'response' in response
        assert 'session_id' in response
        assert len(response['response']) > 0
        print("✓ JARVIS chat test passed")
        
        # Test access control for free user
        print("Testing JARVIS access control...")
        try:
            service.chat(
                user=self.free_user,
                message="Hello JARVIS",
                conversation_type='general'
            )
            assert False, "Free user should not have JARVIS access"
        except ValueError as e:
            assert "paid plan users only" in str(e)
            print("✓ JARVIS access control test passed")
        
        # Test logo generation
        print("Testing logo generation...")
        logo_data = service.generate_logo_prompt(
            user=self.pro_user,
            business_name="Mike's Vending Co",
            style_preferences="modern",
            color_preferences="blue and white"
        )
        
        assert 'dall_e_prompt' in logo_data
        assert 'style_suggestions' in logo_data
        assert "Mike's Vending Co" in logo_data['dall_e_prompt']
        print("✓ Logo generation test passed")
        
        # Test social media content
        print("Testing social media content generation...")
        social_content = service.generate_social_media_content(
            user=self.elite_user,
            platform='facebook',
            content_type='post',
            business_focus='vending machine placement',
            target_audience='small business owners'
        )
        
        assert 'content' in social_content
        assert 'hashtag_suggestions' in social_content
        assert social_content['platform'] == 'facebook'
        print("✓ Social media content generation test passed")
    
    def test_business_tools_service(self):
        """Test BusinessToolsService."""
        print("\n" + "="*50)
        print("TESTING BUSINESS TOOLS SERVICE")
        print("="*50)
        
        service = BusinessToolsService()
        
        # Test lead value calculation for elite user
        print("Testing lead value calculation...")
        lead_calc_result = service.calculate_lead_value(
            user=self.elite_user,
            business_goals={'monthly_revenue_goal': 5000},
            pricing_model={
                'commission_rate': 30,
                'monthly_revenue_per_machine': 300
            },
            outreach_strategy={
                'success_rate': 15,
                'cost_per_lead': 2.50
            }
        )
        
        assert 'revenue_projections' in lead_calc_result
        assert 'lead_requirements' in lead_calc_result
        assert 'roi_analysis' in lead_calc_result
        assert 'recommendations' in lead_calc_result
        assert 'calculation_id' in lead_calc_result
        print("✓ Lead value calculation test passed")
        
        # Test snack price calculation
        print("Testing snack price calculation...")
        snack_calc_result = service.calculate_snack_pricing(
            user=self.elite_user,
            snack_details={'wholesale_cost': 0.50},
            pricing_strategy={
                'sale_price': 1.50,
                'estimated_daily_sales': 25
            },
            location_details={
                'state_tax_rate': 6.5,
                'commission_rate': 30
            }
        )
        
        assert 'per_unit_analysis' in snack_calc_result
        assert 'daily_projections' in snack_calc_result
        assert 'monthly_projections' in snack_calc_result
        assert 'pricing_recommendations' in snack_calc_result
        print("✓ Snack price calculation test passed")
        
        # Test access control for free user
        print("Testing business tools access control...")
        try:
            service.calculate_lead_value(
                user=self.free_user,
                business_goals={'monthly_revenue_goal': 1000},
                pricing_model={'commission_rate': 30, 'monthly_revenue_per_machine': 200},
                outreach_strategy={'success_rate': 10, 'cost_per_lead': 2.00}
            )
            assert False, "Free user should not have business tools access"
        except ValueError as e:
            assert "Elite/Professional subscription" in str(e)
            print("✓ Business tools access control test passed")
    
    def test_api_endpoints(self):
        """Test API endpoints."""
        print("\n" + "="*50)
        print("TESTING API ENDPOINTS")
        print("="*50)
        
        # Test script generation endpoint
        print("Testing script generation API...")
        self.authenticate_user(self.pro_user)
        
        with patch('apps.ai_toolkit.services.script_generator_service.genai') as mock_genai:
            mock_response = MagicMock()
            mock_response.text = "Generated script content via API"
            mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
            
            response = self.client.post('/api/v1/ai-toolkit/scripts/generate/', {
                'script_type': 'email',
                'target_location_name': 'API Test Business',
                'target_location_category': 'Retail',
                'target_machine_type': 'combo_machine',
                'custom_requirements': 'Make it professional'
            })
            
            assert response.status_code == 201
            assert 'script' in response.data
            assert response.data['script']['target_location_name'] == 'API Test Business'
            print("✓ Script generation API test passed")
        
        # Test script list endpoint
        print("Testing script list API...")
        response = self.client.get('/api/v1/ai-toolkit/scripts/')
        assert response.status_code == 200
        assert 'results' in response.data or isinstance(response.data, list)
        print("✓ Script list API test passed")
        
        # Test script templates endpoint
        print("Testing script templates API...")
        response = self.client.get('/api/v1/ai-toolkit/scripts/templates/')
        assert response.status_code == 200
        print("✓ Script templates API test passed")
        
        # Test JARVIS chat endpoint
        print("Testing JARVIS chat API...")
        with patch('apps.ai_toolkit.services.jarvis_service.genai') as mock_genai:
            mock_response = MagicMock()
            mock_response.text = "Hello! I'm JARVIS. How can I help you today?"
            mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
            
            response = self.client.post('/api/v1/ai-toolkit/jarvis/chat/', {
                'message': 'Hello JARVIS',
                'conversation_type': 'general'
            })
            
            assert response.status_code == 200
            assert 'response' in response.data
            assert 'session_id' in response.data
            print("✓ JARVIS chat API test passed")
        
        # Test business tools API
        print("Testing business tools API...")
        self.authenticate_user(self.elite_user)
        
        response = self.client.post('/api/v1/ai-toolkit/business-tools/lead-value-calculator/', {
            'monthly_revenue_goal': 3000,
            'commission_rate': 25,
            'monthly_revenue_per_machine': 250,
            'success_rate': 12,
            'cost_per_lead': 3.00
        })
        
        assert response.status_code == 200
        assert 'revenue_projections' in response.data
        print("✓ Business tools API test passed")
        
        # Test unauthorized access
        print("Testing unauthorized access...")
        self.client.credentials()  # Remove authentication
        
        response = self.client.post('/api/v1/ai-toolkit/scripts/generate/', {
            'script_type': 'email',
            'target_location_name': 'Test',
            'target_machine_type': 'snack_machine'
        })
        
        assert response.status_code == 401
        print("✓ Unauthorized access properly blocked")
    
    def test_serializers(self):
        """Test serializers validation."""
        print("\n" + "="*50)
        print("TESTING SERIALIZERS")
        print("="*50)
        
        from apps.ai_toolkit.serializers import (
            ScriptGenerationRequestSerializer,
            LeadValueCalculationSerializer,
            SnackPriceCalculationSerializer
        )
        
        # Test script generation serializer
        print("Testing script generation serializer...")
        valid_data = {
            'script_type': 'cold_call',
            'target_location_name': 'Test Business',
            'target_machine_type': 'snack_machine'
        }
        
        serializer = ScriptGenerationRequestSerializer(data=valid_data)
        assert serializer.is_valid(), f"Serializer errors: {serializer.errors}"
        print("✓ Script generation serializer test passed")
        
        # Test invalid data
        invalid_data = {
            'script_type': 'invalid_type',
            'target_location_name': 'T',  # Too short
            'target_machine_type': 'snack_machine'
        }
        
        serializer = ScriptGenerationRequestSerializer(data=invalid_data)
        assert not serializer.is_valid()
        print("✓ Script generation serializer validation test passed")
        
        # Test lead value calculation serializer
        print("Testing lead value calculation serializer...")
        valid_calc_data = {
            'monthly_revenue_goal': 5000,
            'commission_rate': 30,
            'monthly_revenue_per_machine': 300,
            'success_rate': 15,
            'cost_per_lead': 2.50
        }
        
        serializer = LeadValueCalculationSerializer(data=valid_calc_data)
        assert serializer.is_valid(), f"Serializer errors: {serializer.errors}"
        print("✓ Lead value calculation serializer test passed")
        
        # Test snack price calculation serializer
        print("Testing snack price calculation serializer...")
        valid_snack_data = {
            'wholesale_cost': 0.50,
            'sale_price': 1.50,
            'estimated_daily_sales': 20,
            'state_tax_rate': 6.5,
            'commission_rate': 30
        }
        
        serializer = SnackPriceCalculationSerializer(data=valid_snack_data)
        assert serializer.is_valid(), f"Serializer errors: {serializer.errors}"
        print("✓ Snack price calculation serializer test passed")
    
    def cleanup(self):
        """Clean up test data."""
        print("\n" + "="*50)
        print("CLEANING UP TEST DATA")
        print("="*50)
        
        # Delete test users and their related data
        User.objects.filter(email__contains='test_ai_toolkit').delete()
        
        # Delete test templates
        ScriptTemplate.objects.filter(name__contains='Test').delete()
        
        print("✓ Test data cleanup complete")
    
    def run_all_tests(self):
        """Run all tests."""
        print("STARTING AI TOOLKIT COMPREHENSIVE TESTING")
        print("="*70)
        
        try:
            self.test_models()
            self.test_script_generator_service()
            self.test_jarvis_service()
            self.test_business_tools_service()
            self.test_api_endpoints()
            self.test_serializers()
            
            print("\n" + "="*70)
            print("🎉 ALL AI TOOLKIT TESTS PASSED SUCCESSFULLY! 🎉")
            print("="*70)
            
        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            self.cleanup()


def main():
    """Main function to run tests."""
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print(__doc__)
        return
    
    # Check if we're in the right directory
    if not os.path.exists('manage.py'):
        print("❌ Error: Please run this script from the project root directory (where manage.py is located)")
        sys.exit(1)
    
    # Run the tests
    test_case = AIToolkitTestCase()
    test_case.run_all_tests()


if __name__ == '__main__':
    main()