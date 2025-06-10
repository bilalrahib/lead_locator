from django.utils.deprecation import MiddlewareMixin
from django.urls import reverse
from apps.project_core.utils.helpers import get_client_ip
from ..models import AffiliateProfile, ReferralClick
import logging

logger = logging.getLogger(__name__)


class ReferralTrackingMiddleware(MiddlewareMixin):
    """
    Middleware to track referral codes and store them in session.
    """

    def process_request(self, request):
        """Process incoming request to check for referral codes."""
        
        # Check for referral code in URL parameters
        ref_code = request.GET.get('ref')
        
        if ref_code:
            try:
                # Find affiliate with this referral code
                affiliate = AffiliateProfile.objects.get(
                    referral_code=ref_code,
                    status='approved'
                )
                
                # Store referral code in session (expires in 30 days)
                request.session['referral_code'] = ref_code
                request.session['referral_affiliate_id'] = str(affiliate.id)
                request.session.set_expiry(30 * 24 * 60 * 60)  # 30 days
                
                # Track the click
                self._track_referral_click(request, affiliate)
                
                logger.info(f"Referral tracked: {ref_code} from {get_client_ip(request)}")
                
            except AffiliateProfile.DoesNotExist:
                logger.warning(f"Invalid referral code attempted: {ref_code}")
        
        return None

    def _track_referral_click(self, request, affiliate):
        """Track referral click in database."""
        try:
            ReferralClick.objects.create(
                affiliate=affiliate,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                referrer_url=request.META.get('HTTP_REFERER', ''),
                landing_page=request.build_absolute_uri(),
                session_key=request.session.session_key or ''
            )
        except Exception as e:
            logger.error(f"Error tracking referral click: {e}")