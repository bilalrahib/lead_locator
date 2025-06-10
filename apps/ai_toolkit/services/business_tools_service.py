# from django.contrib.auth import get_user_model
# from typing import Dict, List
# from decimal import Decimal, ROUND_HALF_UP
# import logging
# from ..models import BusinessCalculation

# User = get_user_model()
# logger = logging.getLogger(__name__)


# class BusinessToolsService:
#     """
#     Service for AI Business Tools calculations.
#     """
    
#     def calculate_lead_value(self, user: User, business_goals: Dict, 
#                            pricing_model: Dict, outreach_strategy: Dict) -> Dict:
#         """Calculate lead value and ROI projections."""
#         if not self._can_access_business_tools(user):
#             raise ValueError("AI Business Tools access requires Elite/Professional subscription")
        
#         # Extract parameters
#         monthly_revenue_goal = Decimal(str(business_goals.get('monthly_revenue_goal', 5000)))
#         commission_rate = Decimal(str(pricing_model.get('commission_rate', 30))) / 100
#         machine_revenue = Decimal(str(pricing_model.get('monthly_revenue_per_machine', 300)))
#         success_rate = Decimal(str(outreach_strategy.get('success_rate', 10))) / 100
#         cost_per_lead = Decimal(str(outreach_strategy.get('cost_per_lead', 2.50)))
        
#         # Calculate metrics
#         revenue_per_placement = machine_revenue * commission_rate
#         machines_needed = (monthly_revenue_goal / revenue_per_placement).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
#         leads_needed = (machines_needed / success_rate).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
#         total_lead_cost = leads_needed * cost_per_lead
#         net_revenue = monthly_revenue_goal - total_lead_cost
        
#         results = {
#             'revenue_projections': {
#                 'monthly_revenue_goal': float(monthly_revenue_goal),
#                 'machines_needed': int(machines_needed),
#                 'net_monthly_revenue': float(net_revenue)
#             },
#             'lead_requirements': {
#                 'leads_needed_monthly': int(leads_needed),
#                 'total_monthly_lead_cost': float(total_lead_cost),
#                 'cost_per_lead': float(cost_per_lead)
#             },
#             'roi_analysis': {
#                 'roi_percentage': float((net_revenue / total_lead_cost * 100)) if total_lead_cost > 0 else 0,
#                 'break_even_leads': int(total_lead_cost / cost_per_lead) if cost_per_lead > 0 else 0
#             },
#             'recommendations': ['Consider optimizing your lead generation strategy', 'Focus on higher-value locations']
#         }
        
#         # Save calculation
#         calculation = BusinessCalculation.objects.create(
#             user=user,
#             calculation_type='lead_value_estimator',
#             input_parameters={
#                 'business_goals': business_goals,
#                 'pricing_model': pricing_model,
#                 'outreach_strategy': outreach_strategy
#             },
#             calculation_results=results
#         )
        
#         results['calculation_id'] = str(calculation.id)
#         return results
    
#     def calculate_snack_pricing(self, user: User, snack_details: Dict, 
#                                pricing_strategy: Dict, location_details: Dict) -> Dict:
#         """Calculate snack pricing and projections."""
#         if not self._can_access_business_tools(user):
#             raise ValueError("AI Business Tools access requires Elite/Professional subscription")
        
#         # Extract parameters
#         wholesale_cost = Decimal(str(snack_details.get('wholesale_cost', 0.50)))
#         sale_price = Decimal(str(pricing_strategy.get('sale_price', 1.50)))
#         daily_sales = int(pricing_strategy.get('estimated_daily_sales', 20))
#         tax_rate = Decimal(str(location_details.get('state_tax_rate', 6.5))) / 100
#         commission_rate = Decimal(str(location_details.get('commission_rate', 30))) / 100
        
#         # Calculate per-unit analysis
#         gross_profit = sale_price - wholesale_cost
#         tax_per_unit = sale_price * tax_rate
#         net_price = sale_price - tax_per_unit
#         commission_per_unit = net_price * commission_rate
#         operator_profit = net_price - wholesale_cost - commission_per_unit
        
#         results = {
#             'per_unit_analysis': {
#                 'wholesale_cost': float(wholesale_cost),
#                 'sale_price': float(sale_price),
#                 'gross_profit_per_unit': float(gross_profit),
#                 'operator_profit_per_unit': float(operator_profit)
#             },
#             'daily_projections': {
#                 'estimated_units_sold': daily_sales,
#                 'gross_sales': float(sale_price * daily_sales),
#                 'operator_profit': float(operator_profit * daily_sales)
#             },
#             'monthly_projections': {
#                 'gross_sales': float(sale_price * daily_sales * 30),
#                 'operator_profit': float(operator_profit * daily_sales * 30)
#             },
#             'break_even_analysis': {
#                 'break_even_units_daily': max(1, int(Decimal('5.00') / operator_profit)) if operator_profit > 0 else daily_sales
#             },
#             'pricing_recommendations': ['Consider adjusting prices based on location traffic', 'Monitor competitor pricing']
#         }
        
#         # Save calculation
#         calculation = BusinessCalculation.objects.create(
#             user=user,
#             calculation_type='snack_price_calculator',
#             input_parameters={
#                 'snack_details': snack_details,
#                 'pricing_strategy': pricing_strategy,
#                 'location_details': location_details
#             },
#             calculation_results=results
#         )
        
#         results['calculation_id'] = str(calculation.id)
#         return results
    
#     def _can_access_business_tools(self, user: User) -> bool:
#         """Check if user can access AI Business Tools."""
#         if not hasattr(user, 'subscription') or not user.subscription:
#             return False
        
#         subscription = user.subscription
#         if not subscription.is_active:
#             return False
        
#         # Elite and Professional get access
#         return subscription.plan.name in ['ELITE', 'PROFESSIONAL']

from django.contrib.auth import get_user_model
from django.utils import timezone
from typing import Dict, List
from decimal import Decimal, ROUND_HALF_UP
import logging
from ..models import BusinessCalculation

User = get_user_model()
logger = logging.getLogger(__name__)


class BusinessToolsService:
    """
    Service for AI Business Tools calculations.
    """
    
    def __init__(self):
        pass
    
    def calculate_lead_value(self, user: User, business_goals: Dict, 
                           pricing_model: Dict, outreach_strategy: Dict) -> Dict:
        """
        Calculate lead value and ROI projections.
        
        Args:
            user: User requesting calculation
            business_goals: Business goals and targets
            pricing_model: Pricing and revenue model
            outreach_strategy: Outreach approach details
            
        Returns:
            Dict with ROI projections and recommendations
        """
        if not self._can_access_business_tools(user):
            raise ValueError("AI Business Tools access requires Elite/Professional subscription or $14.95/month add-on")
        
        # Extract parameters
        monthly_revenue_goal = Decimal(str(business_goals.get('monthly_revenue_goal', 5000)))
        average_commission_rate = Decimal(str(pricing_model.get('commission_rate', 30))) / 100
        average_machine_revenue = Decimal(str(pricing_model.get('monthly_revenue_per_machine', 300)))
        placement_success_rate = Decimal(str(outreach_strategy.get('success_rate', 10))) / 100
        cost_per_lead = Decimal(str(outreach_strategy.get('cost_per_lead', 2.50)))
        
        # Calculate required machines and placements
        revenue_per_placement = average_machine_revenue * average_commission_rate
        machines_needed = (monthly_revenue_goal / revenue_per_placement).quantize(
            Decimal('1'), rounding=ROUND_HALF_UP
        )
        
        # Calculate leads needed
        leads_for_placements = (machines_needed / placement_success_rate).quantize(
            Decimal('1'), rounding=ROUND_HALF_UP
        )
        
        # Calculate costs and ROI
        total_lead_cost = leads_for_placements * cost_per_lead
        monthly_net_revenue = monthly_revenue_goal - total_lead_cost
        
        # ROI calculations
        roi_percentage = ((monthly_net_revenue / total_lead_cost) * 100).quantize(
            Decimal('0.1'), rounding=ROUND_HALF_UP
        ) if total_lead_cost > 0 else Decimal('0')
        
        payback_months = (total_lead_cost / monthly_net_revenue).quantize(
            Decimal('0.1'), rounding=ROUND_HALF_UP
        ) if monthly_net_revenue > 0 else Decimal('999')
        
        # Value per lead
        value_per_lead = (monthly_revenue_goal / leads_for_placements).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        ) if leads_for_placements > 0 else Decimal('0')
        
        # Advanced metrics
        annual_revenue_projection = monthly_revenue_goal * 12
        annual_lead_cost = total_lead_cost * 12
        annual_net_profit = annual_revenue_projection - annual_lead_cost
        
        # Calculate lifetime value metrics
        avg_machine_lifespan_months = Decimal('24')  # 2 years average
        lifetime_revenue_per_machine = average_machine_revenue * avg_machine_lifespan_months
        lifetime_commission_per_machine = lifetime_revenue_per_machine * average_commission_rate
        
        # Market penetration analysis
        total_addressable_leads = leads_for_placements * Decimal('10')  # Estimate 10x lead pool
        market_penetration_rate = (machines_needed / total_addressable_leads * 100).quantize(
            Decimal('0.1'), rounding=ROUND_HALF_UP
        ) if total_addressable_leads > 0 else Decimal('0')
        
        # Efficiency metrics
        cost_per_placement = total_lead_cost / machines_needed if machines_needed > 0 else Decimal('0')
        revenue_multiple = (monthly_revenue_goal / total_lead_cost).quantize(
            Decimal('0.1'), rounding=ROUND_HALF_UP
        ) if total_lead_cost > 0 else Decimal('0')
        
        # Build comprehensive results
        results = {
            'revenue_projections': {
                'monthly_revenue_goal': float(monthly_revenue_goal),
                'revenue_per_machine': float(average_machine_revenue),
                'commission_per_machine': float(revenue_per_placement),
                'machines_needed': int(machines_needed),
                'net_monthly_revenue': float(monthly_net_revenue),
                'annual_revenue_projection': float(annual_revenue_projection),
                'annual_net_profit': float(annual_net_profit),
                'lifetime_revenue_per_machine': float(lifetime_revenue_per_machine),
                'lifetime_commission_per_machine': float(lifetime_commission_per_machine)
            },
            'lead_requirements': {
                'leads_needed_monthly': int(leads_for_placements),
                'placement_success_rate': float(placement_success_rate * 100),
                'cost_per_lead': float(cost_per_lead),
                'total_monthly_lead_cost': float(total_lead_cost),
                'annual_lead_cost': float(annual_lead_cost),
                'value_per_lead': float(value_per_lead),
                'cost_per_placement': float(cost_per_placement),
                'total_addressable_leads': int(total_addressable_leads)
            },
            'roi_analysis': {
                'roi_percentage': float(roi_percentage),
                'payback_period_months': float(payback_months),
                'break_even_leads': int(total_lead_cost / cost_per_lead) if cost_per_lead > 0 else 0,
                'profit_margin': float((monthly_net_revenue / monthly_revenue_goal * 100)) if monthly_revenue_goal > 0 else 0,
                'revenue_multiple': float(revenue_multiple),
                'market_penetration_rate': float(market_penetration_rate),
                'efficiency_score': self._calculate_efficiency_score(roi_percentage, payback_months, placement_success_rate * 100)
            },
            'growth_projections': {
                'month_3_machines': int(machines_needed * 3),
                'month_6_machines': int(machines_needed * 6),
                'month_12_machines': int(machines_needed * 12),
                'scaling_lead_requirement': int(leads_for_placements * 12),
                'scaling_monthly_cost': float(total_lead_cost * 12)
            },
            'recommendations': self._generate_lead_value_recommendations(
                roi_percentage, payback_months, placement_success_rate * 100, value_per_lead,
                cost_per_placement, revenue_multiple
            ),
            'optimization_suggestions': self._generate_optimization_suggestions(
                business_goals, pricing_model, outreach_strategy, {
                    'roi_percentage': roi_percentage,
                    'payback_months': payback_months,
                    'success_rate': placement_success_rate * 100,
                    'cost_per_lead': cost_per_lead
                }
            )
        }
        
        # Save calculation with converted values
        calculation = BusinessCalculation.objects.create(
            user=user,
            calculation_type='lead_value_estimator',
            input_parameters={
                'business_goals': {k: float(v) if isinstance(v, Decimal) else v for k, v in business_goals.items()},
                'pricing_model': {k: float(v) if isinstance(v, Decimal) else v for k, v in pricing_model.items()},
                'outreach_strategy': {k: float(v) if isinstance(v, Decimal) else v for k, v in outreach_strategy.items()}
            },
            calculation_results=results
        )
        
        results['calculation_id'] = str(calculation.id)
        
        logger.info(f"Lead value calculation for {user.email}: {int(leads_for_placements)} leads needed")
        return results
    
    def calculate_snack_pricing(self, user: User, snack_details: Dict, 
                               pricing_strategy: Dict, location_details: Dict) -> Dict:
        """
        Calculate snack pricing, profits, and projections.
        
        Args:
            user: User requesting calculation
            snack_details: Product cost and details
            pricing_strategy: Pricing approach
            location_details: Location and tax information
            
        Returns:
            Dict with pricing analysis and projections
        """
        if not self._can_access_business_tools(user):
            raise ValueError("AI Business Tools access requires Elite/Professional subscription or $14.95/month add-on")
        
        # Extract parameters
        wholesale_cost = Decimal(str(snack_details.get('wholesale_cost', 0.50)))
        sale_price = Decimal(str(pricing_strategy.get('sale_price', 1.50)))
        state_tax_rate = Decimal(str(location_details.get('state_tax_rate', 6.5))) / 100
        estimated_daily_sales = int(pricing_strategy.get('estimated_daily_sales', 20))
        commission_rate = Decimal(str(location_details.get('commission_rate', 30))) / 100
        
        # Calculate per-unit financials
        gross_profit_per_unit = sale_price - wholesale_cost
        tax_per_unit = sale_price * state_tax_rate
        net_sale_price = sale_price - tax_per_unit
        net_profit_per_unit = net_sale_price - wholesale_cost
        
        # Commission to location owner
        commission_per_unit = net_sale_price * commission_rate
        operator_profit_per_unit = net_profit_per_unit - commission_per_unit
        
        # Calculate margins
        gross_margin_percentage = (gross_profit_per_unit / sale_price * 100) if sale_price > 0 else Decimal('0')
        net_margin_percentage = (operator_profit_per_unit / sale_price * 100) if sale_price > 0 else Decimal('0')
        
        # Daily projections
        daily_gross_sales = sale_price * estimated_daily_sales
        daily_taxes_collected = tax_per_unit * estimated_daily_sales
        daily_net_sales = net_sale_price * estimated_daily_sales
        daily_product_cost = wholesale_cost * estimated_daily_sales
        daily_commission_owed = commission_per_unit * estimated_daily_sales
        daily_operator_profit = operator_profit_per_unit * estimated_daily_sales
        
        # Weekly projections (7 days)
        weekly_metrics = {
            'gross_sales': daily_gross_sales * 7,
            'net_sales': daily_net_sales * 7,
            'product_costs': daily_product_cost * 7,
            'taxes_collected': daily_taxes_collected * 7,
            'commission_owed': daily_commission_owed * 7,
            'operator_profit': daily_operator_profit * 7,
            'units_sold': estimated_daily_sales * 7
        }
        
        # Monthly projections (30 days)
        monthly_metrics = {
            'gross_sales': daily_gross_sales * 30,
            'net_sales': daily_net_sales * 30,
            'product_costs': daily_product_cost * 30,
            'taxes_collected': daily_taxes_collected * 30,
            'commission_owed': daily_commission_owed * 30,
            'operator_profit': daily_operator_profit * 30,
            'units_sold': estimated_daily_sales * 30
        }
        
        # Annual projections (365 days)
        annual_metrics = {
            'gross_sales': daily_gross_sales * 365,
            'net_sales': daily_net_sales * 365,
            'product_costs': daily_product_cost * 365,
            'taxes_collected': daily_taxes_collected * 365,
            'commission_owed': daily_commission_owed * 365,
            'operator_profit': daily_operator_profit * 365,
            'units_sold': estimated_daily_sales * 365
        }
        
        # Break-even analysis
        fixed_costs_per_day = Decimal('5.00')  # Estimated daily fixed costs
        break_even_units_daily = (fixed_costs_per_day / operator_profit_per_unit).quantize(
            Decimal('1'), rounding=ROUND_HALF_UP
        ) if operator_profit_per_unit > 0 else Decimal('999')
        
        break_even_revenue_daily = break_even_units_daily * sale_price
        days_to_break_even = (fixed_costs_per_day / daily_operator_profit).quantize(
            Decimal('0.1'), rounding=ROUND_HALF_UP
        ) if daily_operator_profit > 0 else Decimal('999')
        
        # Competitive analysis benchmarks
        market_average_price = sale_price * Decimal('1.1')  # Assume 10% above market
        price_competitiveness = 'competitive' if sale_price <= market_average_price else 'premium'
        
        # Profitability scoring
        profitability_score = self._calculate_profitability_score(
            gross_margin_percentage, net_margin_percentage, operator_profit_per_unit
        )
        
        # Seasonal adjustment factors
        seasonal_adjustments = {
            'summer_adjustment': Decimal('1.15'),  # 15% increase in summer
            'winter_adjustment': Decimal('0.95'),  # 5% decrease in winter
            'holiday_adjustment': Decimal('1.25'),  # 25% increase during holidays
            'back_to_school_adjustment': Decimal('1.20')  # 20% increase back to school
        }
        
        # Price optimization suggestions
        optimal_price_range = {
            'minimum_viable_price': wholesale_cost * Decimal('1.5'),  # 50% markup minimum
            'recommended_price': wholesale_cost * Decimal('2.0'),     # 100% markup recommended
            'premium_price_ceiling': wholesale_cost * Decimal('3.0')  # 200% markup maximum
        }
        
        # Build comprehensive results
        results = {
            'per_unit_analysis': {
                'wholesale_cost': float(wholesale_cost),
                'sale_price': float(sale_price),
                'state_tax_rate': float(state_tax_rate * 100),
                'tax_per_unit': float(tax_per_unit),
                'gross_profit_per_unit': float(gross_profit_per_unit),
                'commission_per_unit': float(commission_per_unit),
                'operator_profit_per_unit': float(operator_profit_per_unit),
                'gross_margin_percentage': float(gross_margin_percentage),
                'net_margin_percentage': float(net_margin_percentage),
                'profitability_score': profitability_score,
                'price_competitiveness': price_competitiveness
            },
            'daily_projections': {
                'estimated_units_sold': estimated_daily_sales,
                'gross_sales': float(daily_gross_sales),
                'net_sales': float(daily_net_sales),
                'product_costs': float(daily_product_cost),
                'taxes_collected': float(daily_taxes_collected),
                'commission_owed': float(daily_commission_owed),
                'operator_profit': float(daily_operator_profit)
            },
            'weekly_projections': {k: float(v) for k, v in weekly_metrics.items()},
            'monthly_projections': {k: float(v) for k, v in monthly_metrics.items()},
            'annual_projections': {k: float(v) for k, v in annual_metrics.items()},
            'break_even_analysis': {
                'break_even_units_daily': int(break_even_units_daily),
                'break_even_units_monthly': int(break_even_units_daily * 30),
                'break_even_revenue_daily': float(break_even_revenue_daily),
                'days_to_break_even': float(days_to_break_even),
                'fixed_costs_daily': float(fixed_costs_per_day)
            },
            'pricing_optimization': {
                'minimum_viable_price': float(optimal_price_range['minimum_viable_price']),
                'recommended_price': float(optimal_price_range['recommended_price']),
                'premium_price_ceiling': float(optimal_price_range['premium_price_ceiling']),
                'current_markup_percentage': float((sale_price - wholesale_cost) / wholesale_cost * 100),
                'recommended_markup_percentage': 100.0
            },
            'seasonal_projections': {
                'summer_monthly_profit': float(monthly_metrics['operator_profit'] * seasonal_adjustments['summer_adjustment']),
                'winter_monthly_profit': float(monthly_metrics['operator_profit'] * seasonal_adjustments['winter_adjustment']),
                'holiday_monthly_profit': float(monthly_metrics['operator_profit'] * seasonal_adjustments['holiday_adjustment']),
                'back_to_school_monthly_profit': float(monthly_metrics['operator_profit'] * seasonal_adjustments['back_to_school_adjustment'])
            },
            'pricing_recommendations': self._generate_pricing_recommendations(
                gross_margin_percentage, net_margin_percentage, operator_profit_per_unit, 
                sale_price, wholesale_cost, estimated_daily_sales
            ),
            'optimization_strategies': self._generate_pricing_optimization_strategies(
                snack_details, pricing_strategy, location_details, {
                    'profitability_score': profitability_score,
                    'gross_margin': gross_margin_percentage,
                    'net_margin': net_margin_percentage,
                    'daily_profit': daily_operator_profit
                }
            )
        }
        
        # Save calculation with converted values
        calculation = BusinessCalculation.objects.create(
            user=user,
            calculation_type='snack_price_calculator',
            input_parameters={
                'snack_details': {k: float(v) if isinstance(v, Decimal) else v for k, v in snack_details.items()},
                'pricing_strategy': {k: float(v) if isinstance(v, Decimal) else v for k, v in pricing_strategy.items()},
                'location_details': {k: float(v) if isinstance(v, Decimal) else v for k, v in location_details.items()}
            },
            calculation_results=results
        )
        
        results['calculation_id'] = str(calculation.id)
        
        logger.info(f"Snack pricing calculation for {user.email}: ${float(sale_price)} price point")
        return results
    
    def get_calculation_history(self, user: User, calculation_type: str = None,
                               limit: int = 20) -> List[BusinessCalculation]:
        """
        Get user's calculation history.
        
        Args:
            user: User requesting history
            calculation_type: Optional filter by calculation type
            limit: Maximum number of results
            
        Returns:
            List of BusinessCalculation objects
        """
        queryset = BusinessCalculation.objects.filter(user=user)
        
        if calculation_type:
            queryset = queryset.filter(calculation_type=calculation_type)
        
        return list(queryset.order_by('-created_at')[:limit])
    
    def _can_access_business_tools(self, user: User) -> bool:
        """Check if user can access AI Business Tools."""
        if not hasattr(user, 'subscription') or not user.subscription:
            return False
        
        subscription = user.subscription
        if not subscription.is_active:
            return False
        
        # Elite and Professional get free access
        if subscription.plan.name in ['ELITE', 'PROFESSIONAL']:
            return True
        
        # Other paid plans can purchase as add-on
        # For now, allow all paid plans (this would be enhanced with add-on purchase tracking)
        return subscription.plan.name != 'FREE'
    
    def _calculate_efficiency_score(self, roi_percentage: Decimal, payback_months: Decimal, 
                                   success_rate: Decimal) -> float:
        """Calculate overall efficiency score for lead value strategy."""
        # Normalize metrics to 0-100 scale
        roi_score = min(100, float(roi_percentage))
        payback_score = max(0, 100 - float(payback_months) * 10)  # Lower payback = higher score
        success_score = float(success_rate) * 5  # Max score at 20% success rate
        
        # Weighted average
        efficiency_score = (roi_score * 0.4 + payback_score * 0.3 + success_score * 0.3)
        return round(efficiency_score, 1)
    
    def _calculate_profitability_score(self, gross_margin: Decimal, net_margin: Decimal, 
                                     profit_per_unit: Decimal) -> float:
        """Calculate profitability score for pricing strategy."""
        # Score based on multiple factors
        margin_score = min(100, float(gross_margin))  # Cap at 100%
        net_margin_score = min(100, float(net_margin) * 2)  # Double weight for net margin
        unit_profit_score = min(100, float(profit_per_unit) * 100)  # $1 profit = 100 points
        
        # Weighted average
        profitability_score = (margin_score * 0.3 + net_margin_score * 0.4 + unit_profit_score * 0.3)
        return round(profitability_score, 1)
    
    def _generate_lead_value_recommendations(self, roi_percentage: Decimal, payback_months: Decimal, 
                                           success_rate: Decimal, value_per_lead: Decimal,
                                           cost_per_placement: Decimal, revenue_multiple: Decimal) -> List[str]:
        """Generate comprehensive recommendations for lead value calculation."""
        recommendations = []
        
        # ROI-based recommendations
        if roi_percentage < 50:
            recommendations.append("⚠️ Low ROI Alert: Consider increasing commission rates or targeting higher-revenue locations to improve returns")
        elif roi_percentage < 100:
            recommendations.append("🔍 ROI Improvement: Your ROI is moderate. Look for ways to reduce lead costs or improve conversion rates")
        elif roi_percentage > 300:
            recommendations.append("🚀 Excellent ROI: Your strategy is highly profitable. Consider scaling up your lead generation budget")
        
        # Payback period recommendations
        if payback_months > 6:
            recommendations.append("⏰ Long Payback: Focus on faster-converting lead sources or higher-value locations to reduce payback time")
        elif payback_months < 2:
            recommendations.append("⚡ Fast Payback: Excellent! Your quick payback allows for aggressive scaling")
        
        # Success rate recommendations
        if success_rate < 5:
            recommendations.append("📈 Low Conversion: Improve your sales approach, targeting, or script quality to boost placement success")
        elif success_rate < 10:
            recommendations.append("💪 Moderate Conversion: Good foundation. Refine your process to push success rate above 15%")
        elif success_rate > 20:
            recommendations.append("🎯 Outstanding Conversion: Your sales process is excellent. Focus on lead volume scaling")
        
        # Value per lead recommendations
        if value_per_lead < 50:
            recommendations.append("💰 Low Lead Value: Target higher-revenue locations like office buildings, hospitals, or busy retail centers")
        elif value_per_lead > 200:
            recommendations.append("💎 High Lead Value: Excellent targeting! Maintain this quality focus while increasing volume")
        
        # Cost efficiency recommendations
        if cost_per_placement > 100:
            recommendations.append("💸 High Acquisition Cost: Optimize your lead sources or improve conversion to reduce cost per placement")
        elif cost_per_placement < 20:
            recommendations.append("💡 Low Acquisition Cost: Great efficiency! Consider investing saved costs into higher-quality leads")
        
        # Revenue multiple recommendations
        if revenue_multiple < 2:
            recommendations.append("⚖️ Revenue Multiple: Aim for at least 2x revenue vs lead costs for sustainable growth")
        elif revenue_multiple > 5:
            recommendations.append("📊 Strong Multiple: Excellent revenue efficiency enables confident budget increases")
        
        # Strategic recommendations
        recommendations.extend([
            "🎯 Focus Strategy: Concentrate on your highest-performing location types and expand systematically",
            "📊 Track Performance: Monitor monthly metrics to identify trends and optimize continuously",
            "🤝 Relationship Building: Maintain strong location relationships for referrals and renewals",
            "🔄 Process Refinement: Regularly test and improve your sales scripts and approach"
        ])
        
        return recommendations[:8]  # Limit to most relevant recommendations
    
    def _generate_pricing_recommendations(self, gross_margin: Decimal, net_margin: Decimal, 
                                        profit_per_unit: Decimal, sale_price: Decimal,
                                        wholesale_cost: Decimal, daily_sales: int) -> List[str]:
        """Generate comprehensive pricing recommendations."""
        recommendations = []
        
        # Margin-based recommendations
        if gross_margin < 30:
            recommendations.append("⚠️ Low Gross Margin: Consider increasing prices or sourcing lower-cost products")
        elif gross_margin > 70:
            recommendations.append("💰 Strong Gross Margin: You have pricing flexibility for competitive advantage")
        
        if net_margin < 15:
            recommendations.append("📉 Thin Net Margin: Negotiate better commission rates or increase prices to improve profitability")
        elif net_margin > 40:
            recommendations.append("🎯 Excellent Net Margin: Strong profitability foundation for business growth")
        
        # Profit per unit recommendations
        if profit_per_unit < Decimal('0.20'):
            recommendations.append("💡 Low Unit Profit: Focus on premium products or higher-volume locations")
        elif profit_per_unit > Decimal('0.75'):
            recommendations.append("🚀 Strong Unit Profit: Excellent per-sale economics support scaling")
        
        # Price point recommendations
        markup_percentage = (sale_price - wholesale_cost) / wholesale_cost * 100
        if markup_percentage < 50:
            recommendations.append("📈 Low Markup: Consider increasing prices - aim for 100-200% markup on wholesale cost")
        elif markup_percentage > 300:
            recommendations.append("⚖️ High Markup: Monitor competitor pricing to ensure market competitiveness")
        
        # Volume-based recommendations
        if daily_sales < 10:
            recommendations.append("📊 Low Volume: Focus on high-traffic locations or consider product mix changes")
        elif daily_sales > 40:
            recommendations.append("🔥 High Volume: Excellent! Optimize restocking frequency and consider premium products")
        
        # Strategic pricing recommendations
        if sale_price < Decimal('1.00'):
            recommendations.append("💵 Low Price Point: Consider premium positioning for better margins")
        elif sale_price > Decimal('3.00'):
            recommendations.append("🏆 Premium Pricing: Ensure location demographics support high-end positioning")
        
        # Location-specific recommendations
        recommendations.extend([
            "🎯 Market Research: Regularly survey competitor pricing in your area",
            "📱 Dynamic Pricing: Consider seasonal adjustments for holidays and events",
            "🔄 Product Rotation: Test different products to optimize sales and margins",
            "📈 Performance Tracking: Monitor sales data to identify optimal price points"
        ])
        
        return recommendations[:8]  # Limit to most relevant recommendations
    
    def _generate_optimization_suggestions(self, business_goals: Dict, pricing_model: Dict, 
                                         outreach_strategy: Dict, metrics: Dict) -> List[str]:
        """Generate optimization suggestions for lead value strategy."""
        suggestions = []
        
        # Based on current performance metrics
        if metrics['roi_percentage'] < 100:
            suggestions.append("🎯 Target Optimization: Focus on office buildings and medical facilities for higher revenue potential")
        
        if metrics['success_rate'] < 15:
            suggestions.append("📞 Script Enhancement: A/B test different sales approaches and value propositions")
        
        if metrics['cost_per_lead'] > 3:
            suggestions.append("💡 Lead Source Diversification: Explore lower-cost channels like referrals and local networking")
        
        # Strategic suggestions
        suggestions.extend([
            "📊 Data-Driven Targeting: Use demographic data to identify high-potential areas",
            "🤝 Partnership Development: Build relationships with commercial real estate agents",
            "🔄 Process Automation: Implement CRM systems to streamline follow-up processes",
            "📈 Scaling Strategy: Gradually increase lead generation budget as conversion improves"
        ])
        
        return suggestions
    
    def _generate_pricing_optimization_strategies(self, snack_details: Dict, pricing_strategy: Dict,
                                                location_details: Dict, metrics: Dict) -> List[str]:
        """Generate optimization strategies for pricing."""
        strategies = []
        
        # Based on profitability metrics
        if metrics['profitability_score'] < 60:
            strategies.append("💰 Margin Improvement: Negotiate better wholesale rates or consider premium product lines")
        
        if metrics['gross_margin'] < 40:
            strategies.append("📈 Price Testing: Gradually test price increases to find optimal point")
        
        if metrics['daily_profit'] < 10:
            strategies.append("🎯 Location Enhancement: Focus on higher-traffic or premium locations")
        
        # Strategic optimization
        strategies.extend([
            "🔄 Product Mix Optimization: Regularly analyze best-selling items and adjust inventory",
            "📊 Competitive Analysis: Monitor competitor pricing and positioning strategies",
            "🎯 Demographic Targeting: Align product selection with location demographics",
            "📱 Technology Integration: Consider cashless payment options to increase sales"
        ])
        
        return strategies