#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append('D:/mike/new/vending_hive')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vending_hive.settings.development')
django.setup()

print("Testing imports...")

try:
    from apps.subscriptions.models import LeadCreditPackage, PaymentHistory
    print("✅ Models import successfully")
except ImportError as e:
    print(f"❌ Models import failed: {e}")

try:
    from apps.subscriptions.serializers import SubscriptionPlanDetailSerializer
    print("✅ Serializers import successfully")
except ImportError as e:
    print(f"❌ Serializers import failed: {e}")

try:
    from apps.subscriptions.services import SubscriptionService
    print("✅ Services import successfully")
except ImportError as e:
    print(f"❌ Services import failed: {e}")

try:
    from apps.subscriptions.admin import LeadCreditPackageAdmin
    print("✅ Admin imports successfully")
except ImportError as e:
    print(f"❌ Admin import failed: {e}")

print("\nAll imports tested!")