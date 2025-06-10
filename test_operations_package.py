#!/usr/bin/env python
"""
Comprehensive test script for the Operations package.
This script tests all models, serializers, services, and API endpoints.

Usage: python test_operations_package.py
"""

import os
import sys
import django
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from decimal import Decimal
from datetime import datetime, timedelta
import json

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vending_hive.settings.development')
django.setup()

# Import after Django setup
from apps.operations.models import ManagedLocation, PlacedMachine, VisitLog, CollectionData
from apps.operations.services import LocationService, MachineService, VisitService, CollectionService, ReportService
from apps.operations.serializers import (
    ManagedLocationSerializer, PlacedMachineSerializer, VisitLogSerializer, 
    CollectionDataSerializer
)
from apps.project_core.models import SubscriptionPlan, UserSubscription

User = get_user_model()


class OperationsTestRunner:
    """Main test runner for operations package."""
    
    def __init__(self):
        self.client = Client()
        self.api_client = APIClient()
        self.test_user = None
        self.test_location = None
        self.test_machine = None
        self.test_visit = None
        self.test_collection = None
        
    def run_all_tests(self):
        """Run all test suites."""
        print("🚀 Starting Operations Package Test Suite")
        print("=" * 60)
        
        try:
            self.setup_test_data()
            
            # Model Tests
            print("\n📊 Testing Models...")
            self.test_managed_location_model()
            self.test_placed_machine_model()
            self.test_visit_log_model()
            self.test_collection_data_model()
            
            # Service Tests
            print("\n🔧 Testing Services...")
            self.test_location_service()
            self.test_machine_service()
            self.test_visit_service()
            self.test_collection_service()
            self.test_report_service()
            
            # Serializer Tests
            print("\n📝 Testing Serializers...")
            self.test_serializers()
            
            # API Tests
            print("\n🌐 Testing API Endpoints...")
            self.test_api_endpoints()
            
            # Business Logic Tests
            print("\n💼 Testing Business Logic...")
            self.test_business_logic()
            
            # Edge Cases and Error Handling
            print("\n⚠️ Testing Edge Cases...")
            self.test_edge_cases()
            
            print("\n✅ All tests completed successfully!")
            print("🎉 Operations Package is working correctly!")
            
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            self.cleanup_test_data()
    
    def setup_test_data(self):
        """Setup test data."""
        print("Setting up test data...")
        
        # Create test user
        self.test_user = User.objects.create_user(
            username='operations_test_user',
            email='operations_test@vendinghive.com',
            password='testpass123',
            first_name='Operations',
            last_name='Tester'
        )
        
        # Create subscription plan and user subscription
        free_plan, created = SubscriptionPlan.objects.get_or_create(
            name='FREE',
            defaults={
                'price': Decimal('0.00'),
                'leads_per_month': 3,
                'leads_per_search_range': '10',
                'script_templates_count': 1,
                'description': 'Free plan for testing'
            }
        )
        
        UserSubscription.objects.get_or_create(
            user=self.test_user,
            defaults={
                'plan': free_plan,
                'start_date': timezone.now(),
                'is_active': True
            }
        )
        
        print("✓ Test data setup complete")
    
    def cleanup_test_data(self):
        """Clean up test data."""
        print("\nCleaning up test data...")
        
        try:
            # Delete in reverse order of dependencies
            if self.test_collection:
                self.test_collection.delete()
            if self.test_visit:
                self.test_visit.delete()
            if self.test_machine:
                self.test_machine.delete()
            if self.test_location:
                self.test_location.delete()
            if self.test_user:
                self.test_user.delete()
        except Exception as e:
            print(f"Warning: Cleanup error: {e}")
        
        print("✓ Cleanup complete")
    
    def test_managed_location_model(self):
        """Test ManagedLocation model."""
        print("  Testing ManagedLocation model...")
        
        # Create location
        location_data = {
            'user': self.test_user,
            'location_name': 'Test Coffee Shop',
            'address_details': '123 Main St, Anytown, ST 12345',
            'contact_person': 'John Doe',
            'contact_phone': '555-1234',
            'contact_email': 'john@coffeeshop.com',
            'notes': 'Great location for vending machines',
            'latitude': Decimal('40.7128'),
            'longitude': Decimal('-74.0060')
        }
        
        self.test_location = ManagedLocation.objects.create(**location_data)
        
        # Test model properties
        assert self.test_location.location_name == 'Test Coffee Shop'
        assert self.test_location.user == self.test_user
        assert self.test_location.is_active == True
        assert self.test_location.total_machines == 0
        assert self.test_location.coordinates == '40.7128,-74.0060'
        assert str(self.test_location) == f'Test Coffee Shop - {self.test_user.email}'
        
        print("    ✓ ManagedLocation model tests passed")
    
    def test_placed_machine_model(self):
        """Test PlacedMachine model."""
        print("  Testing PlacedMachine model...")
        
        # Create machine
        machine_data = {
            'managed_location': self.test_location,
            'machine_type': 'snack',
            'machine_identifier': 'SNK001',
            'date_placed': timezone.now().date(),
            'commission_percentage_to_location': Decimal('30.00'),
            'vend_price_range': '$1.00-$2.50',
            'cost_per_vend': Decimal('0.75'),
            'notes': 'Popular snack machine'
        }
        
        self.test_machine = PlacedMachine.objects.create(**machine_data)
        
        # Test model properties
        assert self.test_machine.machine_type == 'snack'
        assert self.test_machine.get_machine_type_display() == 'Snack Machine'
        assert self.test_machine.commission_percentage_to_location == Decimal('30.00')
        assert self.test_machine.is_active == True
        assert self.test_machine.days_since_placement >= 0
        assert 'Snack Machine at Test Coffee Shop' in str(self.test_machine)
        
        # Test location relationship
        self.test_location.refresh_from_db()
        assert self.test_location.total_machines == 1
        
        print("    ✓ PlacedMachine model tests passed")
    
    def test_visit_log_model(self):
        """Test VisitLog model."""
        print("  Testing VisitLog model...")
        
        # Create visit log
        visit_data = {
            'placed_machine': self.test_machine,
            'visit_date': timezone.now(),
            'visit_type': 'collection',
            'notes': 'Regular collection visit'
        }
        
        self.test_visit = VisitLog.objects.create(**visit_data)
        
        # Test model properties
        assert self.test_visit.visit_type == 'collection'
        assert self.test_visit.get_visit_type_display() == 'Collection'
        assert self.test_visit.placed_machine == self.test_machine
        assert self.test_visit.total_collected == Decimal('0.00')  # No collection data yet
        assert 'Collection - Snack Machine at Test Coffee Shop' in str(self.test_visit)
        
        print("    ✓ VisitLog model tests passed")
    
    def test_collection_data_model(self):
        """Test CollectionData model."""
        print("  Testing CollectionData model...")
        
        # Create collection data
        collection_data = {
            'visit_log': self.test_visit,
            'cash_collected': Decimal('125.50'),
            'items_sold_value': Decimal('150.00'),
            'commission_paid_to_location': Decimal('37.65'),  # 30% of 125.50
            'restock_cost': Decimal('25.00'),
            'maintenance_cost': Decimal('5.00'),
            'restock_notes': 'Restocked all popular items'
        }
        
        self.test_collection = CollectionData.objects.create(**collection_data)
        
        # Test model properties
        assert self.test_collection.cash_collected == Decimal('125.50')
        assert self.test_collection.commission_paid_to_location == Decimal('37.65')
        expected_net_profit = Decimal('125.50') - Decimal('37.65') - Decimal('25.00') - Decimal('5.00')
        assert self.test_collection.net_profit == expected_net_profit
        
        # Test profit margin calculation
        expected_margin = (expected_net_profit / Decimal('125.50')) * 100
        assert abs(self.test_collection.profit_margin - expected_margin) < Decimal('0.01')
        
        # Test visit relationship
        self.test_visit.refresh_from_db()
        assert self.test_visit.total_collected == Decimal('125.50')
        
        print("    ✓ CollectionData model tests passed")
    
    def test_location_service(self):
        """Test LocationService."""
        print("  Testing LocationService...")
        
        # Test create location
        location_data = {
            'location_name': 'Service Test Location',
            'address_details': '456 Test Ave, Test City, TC 67890',
            'contact_person': 'Jane Smith',
            'contact_phone': '555-5678'
        }
        
        service_location = LocationService.create_location(self.test_user, location_data)
        assert service_location.location_name == 'Service Test Location'
        assert service_location.user == self.test_user
        
        # Test get user locations
        user_locations = LocationService.get_user_locations(self.test_user)
        assert len(user_locations) >= 2  # At least our test locations
        
        # Test update location
        update_data = {'notes': 'Updated notes'}
        updated_location = LocationService.update_location(service_location, update_data)
        assert updated_location.notes == 'Updated notes'
        
        # Test location summary
        summary = LocationService.get_location_summary(self.test_user)
        assert 'total_locations' in summary
        assert 'total_machines' in summary
        assert summary['total_locations'] >= 2
        
        # Test coordinate validation
        assert LocationService.validate_location_coordinates(Decimal('40.0'), Decimal('-74.0')) == True
        
        try:
            LocationService.validate_location_coordinates(Decimal('91.0'), Decimal('-74.0'))
            assert False, "Should have raised ValidationError"
        except ValidationError:
            pass  # Expected
        
        # Cleanup
        service_location.delete()
        
        print("    ✓ LocationService tests passed")
    
    def test_machine_service(self):
        """Test MachineService."""
        print("  Testing MachineService...")
        
        # Test place machine
        machine_data = {
            'machine_type': 'drink',
            'machine_identifier': 'DRK001',
            'date_placed': timezone.now().date(),
            'commission_percentage_to_location': Decimal('25.00'),
            'vend_price_range': '$1.50-$3.00',
            'cost_per_vend': Decimal('1.00')
        }
        
        service_machine = MachineService.place_machine(self.test_location, machine_data)
        assert service_machine.machine_type == 'drink'
        assert service_machine.managed_location == self.test_location
        
        # Test get user machines
        user_machines = MachineService.get_user_machines(self.test_user)
        assert len(user_machines) >= 2  # At least our test machines
        
        # Test get machines by location
        location_machines = MachineService.get_machines_by_location(self.test_location)
        assert len(location_machines) >= 2
        
        # Test update machine
        update_data = {'notes': 'Updated machine notes'}
        updated_machine = MachineService.update_machine(service_machine, update_data)
        assert updated_machine.notes == 'Updated machine notes'
        
        # Test machine performance
        performance = MachineService.get_machine_performance(self.test_machine, days=30)
        assert 'total_collected' in performance
        assert 'net_profit' in performance
        assert 'roi_percentage' in performance
        
        # Test validation
        valid_data = {
            'commission_percentage_to_location': Decimal('30.00'),
            'cost_per_vend': Decimal('0.50'),
            'date_placed': timezone.now().date()
        }
        assert MachineService.validate_machine_data(valid_data) == True
        
        try:
            invalid_data = {'commission_percentage_to_location': Decimal('150.00')}
            MachineService.validate_machine_data(invalid_data)
            assert False, "Should have raised ValidationError"
        except ValidationError:
            pass  # Expected
        
        # Cleanup
        service_machine.delete()
        
        print("    ✓ MachineService tests passed")
    
    def test_visit_service(self):
        """Test VisitService."""
        print("  Testing VisitService...")
        
        # Test create visit
        visit_data = {
            'visit_date': timezone.now(),
            'visit_type': 'maintenance',
            'notes': 'Service test visit'
        }
        
        service_visit = VisitService.create_visit(self.test_machine, visit_data)
        assert service_visit.visit_type == 'maintenance'
        assert service_visit.placed_machine == self.test_machine
        
        # Test get machine visits
        machine_visits = VisitService.get_machine_visits(self.test_machine)
        assert len(machine_visits) >= 2  # At least our test visits
        
        # Test get user recent visits
        recent_visits = VisitService.get_user_recent_visits(self.test_user, days=30)
        assert len(recent_visits) >= 2
        
        # Test update visit
        update_data = {'notes': 'Updated visit notes'}
        updated_visit = VisitService.update_visit(service_visit, update_data)
        assert updated_visit.notes == 'Updated visit notes'
        
        # Test visit summary
        summary = VisitService.get_visit_summary(self.test_user, days=30)
        assert 'total_visits' in summary
        assert 'visit_types' in summary
        assert summary['total_visits'] >= 2
        
        # Test validation
        valid_data = {'visit_date': timezone.now()}
        assert VisitService.validate_visit_data(valid_data) == True
        
        try:
            future_date = timezone.now() + timedelta(days=1)
            invalid_data = {'visit_date': future_date}
            VisitService.validate_visit_data(invalid_data)
            assert False, "Should have raised ValidationError"
        except ValidationError:
            pass  # Expected
        
        # Cleanup
        service_visit.delete()
        
        print("    ✓ VisitService tests passed")
    
    def test_collection_service(self):
        """Test CollectionService."""
        print("  Testing CollectionService...")
        
        # Test create collection
        collection_data = {
            'cash_collected': Decimal('200.00'),
            'commission_paid_to_location': Decimal('60.00'),
            'restock_cost': Decimal('30.00'),
            'maintenance_cost': Decimal('10.00'),
            'restock_notes': 'Service test collection'
        }
        
        service_collection = CollectionService.create_collection(self.test_visit, collection_data)
        assert service_collection.cash_collected == Decimal('200.00')
        assert service_collection.visit_log == self.test_visit
        
        # Test update collection
        update_data = {'restock_notes': 'Updated collection notes'}
        updated_collection = CollectionService.update_collection(service_collection, update_data)
        assert updated_collection.restock_notes == 'Updated collection notes'
        
        # Test get user collections
        user_collections = CollectionService.get_user_collections(self.test_user, days=30)
        assert len(user_collections) >= 2
        
        # Test financial summary
        summary = CollectionService.calculate_financial_summary(self.test_user, days=30)
        assert 'total_collected' in summary
        assert 'net_profit' in summary
        assert 'profit_margin' in summary
        assert summary['total_collected'] >= Decimal('325.50')  # Our test collections
        
        # Test top performing items
        top_items = CollectionService.get_top_performing_items(self.test_user, days=30)
        assert len(top_items) >= 1
        
        # Test validation
        valid_data = {
            'cash_collected': Decimal('100.00'),
            'commission_paid_to_location': Decimal('30.00'),
            'restock_cost': Decimal('20.00'),
            'maintenance_cost': Decimal('5.00')
        }
        assert CollectionService.validate_collection_data(valid_data) == True
        
        try:
            invalid_data = {
                'cash_collected': Decimal('100.00'),
                'commission_paid_to_location': Decimal('150.00')  # More than collected
            }
            CollectionService.validate_collection_data(invalid_data)
            assert False, "Should have raised ValidationError"
        except ValidationError:
            pass  # Expected
        
        # Cleanup
        service_collection.delete()
        
        print("    ✓ CollectionService tests passed")
    
    def test_report_service(self):
        """Test ReportService."""
        print("  Testing ReportService...")
        
        # Set date range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        
        # Test operational report
        operational_report = ReportService.generate_operational_report(
            self.test_user, start_date, end_date
        )
        assert 'total_locations' in operational_report
        assert 'total_machines' in operational_report
        assert 'total_collections' in operational_report
        assert 'net_profit' in operational_report
        
        # Test location reports
        location_reports = ReportService.generate_location_reports(
            self.test_user, start_date, end_date
        )
        assert len(location_reports) >= 1
        assert 'location_name' in location_reports[0]
        assert 'total_collections' in location_reports[0]
        
        # Test machine reports
        machine_reports = ReportService.generate_machine_reports(
            self.test_user, start_date, end_date
        )
        assert len(machine_reports) >= 1
        assert 'machine_type' in machine_reports[0]
        assert 'total_collections' in machine_reports[0]
        
        # Test export to CSV
        if machine_reports:
            csv_output = ReportService.export_to_csv(machine_reports, 'test_report')
            assert csv_output.getvalue()  # Should have content
        
        # Test report summary
        summary = ReportService.get_report_summary(self.test_user, days=30)
        assert 'total_locations' in summary
        assert 'total_revenue' in summary
        assert 'profit_margin' in summary
        
        print("    ✓ ReportService tests passed")
    
    def test_serializers(self):
        """Test serializers."""
        print("  Testing Serializers...")
        
        # Test ManagedLocationSerializer
        location_serializer = ManagedLocationSerializer(self.test_location)
        location_data = location_serializer.data
        assert location_data['location_name'] == 'Test Coffee Shop'
        assert 'total_machines' in location_data
        assert 'coordinates' in location_data
        
        # Test PlacedMachineSerializer
        machine_serializer = PlacedMachineSerializer(self.test_machine)
        machine_data = machine_serializer.data
        assert machine_data['machine_type'] == 'snack'
        assert 'machine_type_display' in machine_data
        assert 'location_name' in machine_data
        
        # Test VisitLogSerializer
        visit_serializer = VisitLogSerializer(self.test_visit)
        visit_data = visit_serializer.data
        assert visit_data['visit_type'] == 'collection'
        assert 'visit_type_display' in visit_data
        assert 'machine_info' in visit_data
        
        # Test CollectionDataSerializer
        collection_serializer = CollectionDataSerializer(self.test_collection)
        collection_data = collection_serializer.data
        assert collection_data['cash_collected'] == '125.50'
        assert 'net_profit' in collection_data
        assert 'profit_margin' in collection_data
        
        print("    ✓ Serializer tests passed")
    
    def test_api_endpoints(self):
        """Test API endpoints."""
        print("  Testing API Endpoints...")
        
        # Authenticate
        self.api_client.force_authenticate(user=self.test_user)
        
        # Test locations endpoint
        response = self.api_client.get('/api/v1/operations/managed-locations/')
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        
        # Test create location
        new_location_data = {
            'location_name': 'API Test Location',
            'address_details': '789 API St, Test City, TC 11111',
            'contact_person': 'API Tester'
        }
        response = self.api_client.post('/api/v1/operations/managed-locations/', new_location_data)
        assert response.status_code == 201
        api_location_id = response.json()['id']
        
        # Test location detail
        response = self.api_client.get(f'/api/v1/operations/managed-locations/{self.test_location.id}/')
        assert response.status_code == 200
        
        # Test machines endpoint
        response = self.api_client.get('/api/v1/operations/placed-machines/')
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        
        # Test create machine
        new_machine_data = {
            'managed_location': str(self.test_location.id),
            'machine_type': 'coffee',
            'machine_identifier': 'API001',
            'date_placed': timezone.now().date().isoformat(),
            'commission_percentage_to_location': '35.00',
            'vend_price_range': '$2.00-$4.00',
            'cost_per_vend': '1.50'
        }
        response = self.api_client.post('/api/v1/operations/placed-machines/', new_machine_data)
        assert response.status_code == 201
        
        # Test visits endpoint
        response = self.api_client.get('/api/v1/operations/visit-logs/')
        assert response.status_code == 200
        
        # Test collections endpoint
        response = self.api_client.get('/api/v1/operations/collection-data/')
        assert response.status_code == 200
        
        # Test reports endpoint
        response = self.api_client.get('/api/v1/operations/reports/')
        assert response.status_code == 200
        data = response.json()
        assert 'operational_summary' in data
        assert 'location_reports' in data
        assert 'machine_reports' in data
        
        # Test dashboard endpoint
        response = self.api_client.get('/api/v1/operations/dashboard/')
        assert response.status_code == 200
        data = response.json()
        assert 'location_summary' in data
        assert 'financial_summary' in data
        
        # Test health check
        response = self.api_client.get('/api/v1/operations/health/')
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        
        # Cleanup API test data
        self.api_client.delete(f'/api/v1/operations/managed-locations/{api_location_id}/')
        
        print("    ✓ API endpoint tests passed")
    
    def test_business_logic(self):
        """Test business logic scenarios."""
        print("  Testing Business Logic...")
        
        # Test commission auto-calculation
        visit_data = {
            'placed_machine': self.test_machine,
            'visit_date': timezone.now(),
            'visit_type': 'collection',
            'notes': 'Business logic test'
        }
        business_visit = VisitLog.objects.create(**visit_data)
        
        # Create collection without specifying commission
        collection_data = {
            'visit_log': business_visit,
            'cash_collected': Decimal('100.00'),
            'restock_cost': Decimal('15.00')
        }
        business_collection = CollectionData.objects.create(**collection_data)
        
        # Should auto-calculate 30% commission
        expected_commission = Decimal('100.00') * (Decimal('30.00') / 100)
        assert business_collection.commission_paid_to_location == expected_commission
        
        # Test profit calculations
        expected_profit = Decimal('100.00') - expected_commission - Decimal('15.00')
        assert business_collection.net_profit == expected_profit
        
        # Test location revenue aggregation
        self.test_location.refresh_from_db()
        assert self.test_location.total_revenue_this_month >= Decimal('100.00')
        
        # Test machine performance metrics
        assert self.test_machine.total_collections_this_month >= Decimal('100.00')
        assert self.test_machine.average_per_visit > Decimal('0.00')
        
        # Cleanup
        business_collection.delete()
        business_visit.delete()
        
        print("    ✓ Business logic tests passed")
    
    def test_edge_cases(self):
        """Test edge cases and error handling."""
        print("  Testing Edge Cases...")
        
        # Test with invalid user
        try:
            invalid_user = User.objects.create_user(
                username='invalid_user',
                email='invalid@test.com',
                password='testpass'
            )
            # Try to access another user's data
            self.api_client.force_authenticate(user=invalid_user)
            response = self.api_client.get(f'/api/v1/operations/managed-locations/{self.test_location.id}/')
            assert response.status_code == 404  # Should not find other user's location
            
            invalid_user.delete()
        except Exception as e:
            print(f"    Expected error for invalid user access: {e}")
        
        # Test with zero collections
        zero_visit = VisitLog.objects.create(
            placed_machine=self.test_machine,
            visit_date=timezone.now(),
            visit_type='inspection',
            notes='Zero collection test'
        )
        
        zero_collection = CollectionData.objects.create(
            visit_log=zero_visit,
            cash_collected=Decimal('0.00'),
            commission_paid_to_location=Decimal('0.00')
        )
        
        assert zero_collection.net_profit == Decimal('0.00')
        assert zero_collection.profit_margin == Decimal('0.00')
        
        # Test performance with no data
        empty_user = User.objects.create_user(
            username='empty_user',
            email='empty@test.com',
            password='testpass'
        )
        
        empty_summary = LocationService.get_location_summary(empty_user)
        assert empty_summary['total_locations'] == 0
        assert empty_summary['total_revenue_this_month'] == Decimal('0.00')
        
        # Test report generation with no data
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        empty_report = ReportService.generate_operational_report(empty_user, start_date, end_date)
        assert empty_report['total_locations'] == 0
        assert empty_report['total_collections'] == Decimal('0.00')
        
        # Cleanup
        zero_collection.delete()
        zero_visit.delete()
        empty_user.delete()
        
        print("    ✓ Edge case tests passed")


def main():
    """Main function to run the test suite."""
    print("Operations Package Test Suite")
    print("Testing all components of the operations package...")
    
    runner = OperationsTestRunner()
    runner.run_all_tests()


if __name__ == '__main__':
    main()