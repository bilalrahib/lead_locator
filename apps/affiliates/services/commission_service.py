from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Count, Q
from typing import Dict, List
from datetime import timedelta, datetime
from decimal import Decimal
import logging

from ..models import AffiliateProfile, ReferralConversion, CommissionLedger

logger = logging.getLogger(__name__)


class CommissionService:
    """Service for commission calculation and management."""

    @staticmethod
    @transaction.atomic
    def calculate_monthly_commissions(month_year: str = None) -> Dict:
        """
        Calculate commissions for a specific month.
        
        Args:
            month_year: Month in YYYY-MM format (defaults to current month)
            
        Returns:
            Dict with calculation results
        """
        if not month_year:
            month_year = timezone.now().strftime('%Y-%m')
        
        # Parse month_year
        year, month = map(int, month_year.split('-'))
        period_start = datetime(year, month, 1)
        
        # Calculate period end
        if month == 12:
            period_end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            period_end = datetime(year, month + 1, 1) - timedelta(seconds=1)
        
        period_start = timezone.make_aware(period_start)
        period_end = timezone.make_aware(period_end)
        
        logger.info(f"Calculating commissions for {month_year}")
        
        # Get all active subscriptions for referred users in this period
        from apps.project_core.models import UserSubscription
        
        active_subscriptions = UserSubscription.objects.filter(
            user__referral_source__isnull=False,  # User was referred
            is_active=True,
            start_date__lte=period_end,
            created_at__lte=period_end
        ).select_related('user__referral_source__affiliate', 'plan')
        
        created_count = 0
        total_commission = Decimal('0.00')
        
        for subscription in active_subscriptions:
            try:
                conversion = subscription.user.referral_source
                affiliate = conversion.affiliate
                
                # Check if commission already exists for this period
                existing_commission = CommissionLedger.objects.filter(
                    affiliate=affiliate,
                    referred_user_subscription=subscription,
                    month_year=month_year
                ).first()
                
                if existing_commission:
                    continue  # Skip if already calculated
                
                # Calculate commission
                subscription_amount = subscription.plan.price
                commission_rate = affiliate.commission_rate
                commission_amount = subscription_amount * (commission_rate / 100)
                
                # Create commission ledger entry
                CommissionLedger.objects.create(
                    affiliate=affiliate,
                    referred_user_subscription=subscription,
                    conversion=conversion,
                    subscription_amount=subscription_amount,
                    commission_rate=commission_rate,
                    amount_earned=commission_amount,
                    month_year=month_year,
                    billing_period_start=period_start,
                    billing_period_end=period_end,
                    status='pending'
                )
                
                created_count += 1
                total_commission += commission_amount
                
                logger.info(
                    f"Commission created: {affiliate.referral_code} - "
                    f"${commission_amount} for {subscription.user.email}"
                )
                
            except Exception as e:
                logger.error(f"Error calculating commission for subscription {subscription.id}: {e}")
        
        result = {
            'month_year': month_year,
            'commissions_created': created_count,
            'total_commission_amount': float(total_commission),
            'period_start': period_start,
            'period_end': period_end
        }
        
        logger.info(f"Commission calculation completed: {result}")
        return result

    @staticmethod
    def get_commission_summary(affiliate: AffiliateProfile = None) -> Dict:
        """
        Get commission summary for affiliate or all affiliates.
        
        Args:
            affiliate: Specific affiliate (None for all)
            
        Returns:
            Dict with commission summary
        """
        queryset = CommissionLedger.objects.all()
        if affiliate:
            queryset = queryset.filter(affiliate=affiliate)
        
        # Total commissions by status
        summary = queryset.aggregate(
            total_pending=Sum('amount_earned', filter=Q(status='pending')),
            total_approved=Sum('amount_earned', filter=Q(status='approved')),
            total_paid=Sum('amount_earned', filter=Q(status='paid')),
            total_cancelled=Sum('amount_earned', filter=Q(status='cancelled')),
            count_pending=Count('id', filter=Q(status='pending')),
            count_approved=Count('id', filter=Q(status='approved')),
            count_paid=Count('id', filter=Q(status='paid')),
            count_cancelled=Count('id', filter=Q(status='cancelled'))
        )
        
        # Convert None to 0
        for key, value in summary.items():
            if value is None:
                summary[key] = 0 if 'count_' in key else Decimal('0.00')
        
        # Calculate totals
        summary['total_amount'] = (
            summary['total_pending'] + summary['total_approved'] + 
            summary['total_paid'] + summary['total_cancelled']
        )
        summary['total_count'] = (
            summary['count_pending'] + summary['count_approved'] + 
            summary['count_paid'] + summary['count_cancelled']
        )
        
        return summary

    @staticmethod
    @transaction.atomic
    def approve_commissions(commission_ids: List[str], admin_user) -> Dict:
        """
        Approve pending commissions.
        
        Args:
            commission_ids: List of commission IDs to approve
            admin_user: Admin user performing approval
            
        Returns:
            Dict with approval results
        """
        try:
            commissions = CommissionLedger.objects.filter(
                id__in=commission_ids,
                status='pending'
            )
            
            updated_count = commissions.update(status='approved')
            total_amount = commissions.aggregate(
                total=Sum('amount_earned')
            )['total'] or Decimal('0.00')
            
            logger.info(
                f"Approved {updated_count} commissions totaling ${total_amount} "
                f"by {admin_user.email}"
            )
            
            return {
                'approved_count': updated_count,
                'total_amount': float(total_amount),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error approving commissions: {e}")
            return {
                'approved_count': 0,
                'total_amount': 0,
                'success': False,
                'error': str(e)
            }

    @staticmethod
    @transaction.atomic
    def process_payout(affiliate: AffiliateProfile, payout_method: str, 
                      transaction_id: str, fee: Decimal = None) -> Dict:
        """
        Process payout for affiliate's approved commissions.
        
        Args:
            affiliate: AffiliateProfile instance
            payout_method: Payment method used
            transaction_id: Transaction ID from payment processor
            fee: Optional payout fee
            
        Returns:
            Dict with payout results
        """
        try:
            # Get approved commissions for this affiliate
            approved_commissions = CommissionLedger.objects.filter(
                affiliate=affiliate,
                status='approved'
            )
            
            if not approved_commissions.exists():
                return {
                    'success': False,
                    'error': 'No approved commissions found'
                }
            
            total_amount = approved_commissions.aggregate(
                total=Sum('amount_earned')
            )['total']
            
            # Check minimum payout threshold
            if total_amount < affiliate.minimum_payout:
                return {
                    'success': False,
                    'error': f'Amount ${total_amount} below minimum payout of ${affiliate.minimum_payout}'
                }
            
            # Mark commissions as paid
            updated_count = 0
            for commission in approved_commissions:
                commission.mark_as_paid(payout_method, transaction_id, fee)
                updated_count += 1
            
            logger.info(
                f"Processed payout for {affiliate.referral_code}: "
                f"${total_amount} via {payout_method}"
            )
            
            return {
                'success': True,
                'payout_count': updated_count,
                'total_amount': float(total_amount),
                'payout_method': payout_method,
                'transaction_id': transaction_id
            }
            
        except Exception as e:
            logger.error(f"Error processing payout: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def get_payout_report(affiliate: AffiliateProfile, start_date: datetime = None, 
                         end_date: datetime = None) -> List[Dict]:
        """
        Generate payout report for affiliate.
        
        Args:
            affiliate: AffiliateProfile instance
            start_date: Report start date
            end_date: Report end date
            
        Returns:
            List of payout data
        """
        queryset = CommissionLedger.objects.filter(
            affiliate=affiliate,
            status='paid'
        )
        
        if start_date:
            queryset = queryset.filter(paid_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(paid_at__lte=end_date)
        
        # Group by month for report
        payouts = queryset.extra(
            select={'month': "DATE_FORMAT(paid_at, '%Y-%m')"}
        ).values('month', 'payout_method').annotate(
            total_amount=Sum('amount_earned'),
            commission_count=Count('id'),
            total_fees=Sum('payout_fee')
        ).order_by('-month')
        
        report_data = []
        for payout in payouts:
            report_data.append({
                'period': payout['month'],
                'total_amount': float(payout['total_amount']),
                'commission_count': payout['commission_count'],
                'payout_method': payout['payout_method'],
                'total_fees': float(payout['total_fees'] or 0),
                'net_amount': float(payout['total_amount'] - (payout['total_fees'] or 0))
            })
        
        return report_data