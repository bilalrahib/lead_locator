# apps/ai_toolkit/serializers/business_tools_serializers.py
from rest_framework import serializers
from decimal import Decimal
from ..models import BusinessCalculation


class LeadValueCalculationSerializer(serializers.Serializer):
    """Serializer for lead value estimation requests."""
    
    # Business Goals
    monthly_revenue_goal = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal('100')
    )
    
    # Pricing Model
    commission_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, 
        min_value=Decimal('5'), max_value=Decimal('70'),
        help_text="Commission percentage (5-70%)"
    )
    monthly_revenue_per_machine = serializers.DecimalField(
        max_digits=8, decimal_places=2, min_value=Decimal('50'),
        help_text="Expected monthly revenue per machine"
    )
    
    # Outreach Strategy
    success_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, 
        min_value=Decimal('1'), max_value=Decimal('50'),
        help_text="Placement success rate percentage (1-50%)"
    )
    cost_per_lead = serializers.DecimalField(
        max_digits=6, decimal_places=2, min_value=Decimal('0.1'),
        help_text="Cost per lead in dollars"
    )

    def validate_monthly_revenue_goal(self, value):
        """Validate revenue goal is realistic."""
        if value > Decimal('100000'):
            raise serializers.ValidationError("Monthly revenue goal seems unrealistic (max $100,000).")
        return value

    def validate_monthly_revenue_per_machine(self, value):
        """Validate machine revenue is realistic."""
        if value > Decimal('5000'):
            raise serializers.ValidationError("Revenue per machine seems high (max $5,000/month).")
        return value

    def to_internal_value(self, data):
        """Convert to internal format for calculation."""
        validated_data = super().to_internal_value(data)
        
        return {
            'business_goals': {
                'monthly_revenue_goal': validated_data['monthly_revenue_goal']
            },
            'pricing_model': {
                'commission_rate': validated_data['commission_rate'],
                'monthly_revenue_per_machine': validated_data['monthly_revenue_per_machine']
            },
            'outreach_strategy': {
                'success_rate': validated_data['success_rate'],
                'cost_per_lead': validated_data['cost_per_lead']
            }
        }


# class SnackPriceCalculationSerializer(serializers.Serializer):
#     """Serializer for snack price calculation requests."""
    
#     # Product Details
#     wholesale_cost = serializers.DecimalField(
#         max_digits=6, decimal_places=2, min_value=Decimal('0.01'),
#         help_text="Wholesale cost per unit"
#     )
    
#     # Pricing Strategy
#     sale_price = serializers.DecimalField(
#         max_digits=6, decimal_places=2, min_value=Decimal('0.25'),
#         help_text="Sale price per unit"
#     )
#     estimated_daily_sales = serializers.IntegerField(
#         min_value=1, max_value=500,
#         help_text="Estimated units sold per day"
#     )
    
#     # Location Details
#     state_tax_rate = serializers.DecimalField(
#         max_digits=5, decimal_places=2, 
#         min_value=Decimal('0'), max_value=Decimal('15'),
#         help_text="State tax rate percentage (0-15%)"
#     )
#     commission_rate = serializers.DecimalField(
#         max_digits=5, decimal_places=2, 
#         min_value=Decimal('10'), max_value=Decimal('60'),
#         help_text="Commission to location owner percentage (10-60%)"
#     )

#     def validate(self, attrs):
#         """Cross-field validation."""
#         wholesale_cost = attrs['wholesale_cost']
#         sale_price = attrs['sale_price']
        
#         if sale_price <= wholesale_cost:
#             raise serializers.ValidationError({
#                 'sale_price': 'Sale price must be higher than wholesale cost.'
#             })
        
#         # Check for reasonable profit margin
#         margin = (sale_price - wholesale_cost) / sale_price
#         if margin < Decimal('0.20'):  # Less than 20% margin
#             raise serializers.ValidationError({
#                 'sale_price': 'Profit margin is very low (less than 20%). Consider adjusting prices.'
#             })
        
#         return attrs

#     def to_internal_value(self, data):
#         """Convert to internal format for calculation."""
#         validated_data = super().to_internal_value(data)
        
#         return {
#             'snack_details': {
#                 'wholesale_cost': validated_data['wholesale_cost']
#             },
#             'pricing_strategy': {
#                 'sale_price': validated_data['sale_price'],
#                 'estimated_daily_sales': validated_data['estimated_daily_sales']
#             },
#             'location_details': {
#                 'state_tax_rate': validated_data['state_tax_rate'],
#                 'commission_rate': validated_data['commission_rate']
#             }
#         }


# apps/ai_toolkit/serializers/business_tools_serializers.py

class SnackPriceCalculationSerializer(serializers.Serializer):
    """Serializer for snack price calculation requests."""
    
    # Product Details
    wholesale_cost = serializers.DecimalField(
        max_digits=6, decimal_places=2, min_value=Decimal('0.01'),
        help_text="Wholesale cost per unit"
    )
    
    # Pricing Strategy
    sale_price = serializers.DecimalField(
        max_digits=6, decimal_places=2, min_value=Decimal('0.25'),
        help_text="Sale price per unit"
    )
    estimated_daily_sales = serializers.IntegerField(
        min_value=1, max_value=500,
        help_text="Estimated units sold per day"
    )
    
    # Location Details
    state_tax_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, 
        min_value=Decimal('0'), max_value=Decimal('15'),
        help_text="State tax rate percentage (0-15%)"
    )
    commission_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, 
        min_value=Decimal('10'), max_value=Decimal('60'),
        help_text="Commission to location owner percentage (10-60%)"
    )

    # def validate(self, attrs):
    #     """Cross-field validation."""
    #     # FIX: Access the validated data directly, not from internal conversion
    #     wholesale_cost = attrs['wholesale_cost']
    #     sale_price = attrs['sale_price']
        
    #     if sale_price <= wholesale_cost:
    #         raise serializers.ValidationError({
    #             'sale_price': 'Sale price must be higher than wholesale cost.'
    #         })
        
    #     # Check for reasonable profit margin
    #     margin = (sale_price - wholesale_cost) / sale_price
    #     if margin < Decimal('0.20'):  # Less than 20% margin
    #         raise serializers.ValidationError({
    #             'sale_price': 'Profit margin is very low (less than 20%). Consider adjusting prices.'
    #         })
        
    #     return attrs


    def to_internal_value(self, data):
        """Convert to internal format for calculation."""
        # IMPORTANT: Call parent's to_internal_value FIRST to get validated data
        validated_data = super().to_internal_value(data)
        
        return {
            'snack_details': {
                'wholesale_cost': validated_data['wholesale_cost']
            },
            'pricing_strategy': {
                'sale_price': validated_data['sale_price'],
                'estimated_daily_sales': validated_data['estimated_daily_sales']
            },
            'location_details': {
                'state_tax_rate': validated_data['state_tax_rate'],
                'commission_rate': validated_data['commission_rate']
            }
        }


class BusinessCalculationSerializer(serializers.ModelSerializer):
    """Serializer for business calculation results."""
    
    calculation_type_display = serializers.CharField(source='get_calculation_type_display', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = BusinessCalculation
        fields = [
            'id', 'user_email', 'calculation_type', 'calculation_type_display',
            'input_parameters', 'calculation_results', 'notes', 'created_at'
        ]
        read_only_fields = [
            'id', 'user_email', 'calculation_type_display', 'created_at'
        ]

    def update(self, instance, validated_data):
        """Only allow updating notes."""
        instance.notes = validated_data.get('notes', instance.notes)
        instance.save()
        return instance


class LeadValueResultSerializer(serializers.Serializer):
    """Serializer for lead value calculation results."""
    
    revenue_projections = serializers.DictField()
    lead_requirements = serializers.DictField()
    roi_analysis = serializers.DictField()
    recommendations = serializers.ListField(child=serializers.CharField())
    calculation_id = serializers.CharField()


class SnackPriceResultSerializer(serializers.Serializer):
    """Serializer for snack price calculation results."""
    
    per_unit_analysis = serializers.DictField()
    daily_projections = serializers.DictField()
    monthly_projections = serializers.DictField()
    break_even_analysis = serializers.DictField()
    pricing_recommendations = serializers.ListField(child=serializers.CharField())
    calculation_id = serializers.CharField()