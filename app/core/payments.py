"""
Square payment service for processing credit purchases.

Uses the new Square Python SDK (not the legacy squareup module).
See: https://developer.squareup.com/docs/sdks/python/quick-start
"""
import logging
import uuid
from typing import Optional
from dataclasses import dataclass

from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class PaymentResult:
    """Result of a payment attempt."""
    success: bool
    payment_id: Optional[str] = None
    error_message: Optional[str] = None
    receipt_url: Optional[str] = None


class SquarePaymentService:
    """
    Service for processing payments via Square.
    
    Uses the Square Web Payments SDK flow:
    1. Client generates payment token via Web Payments SDK
    2. Server receives token and calls CreatePayment API
    """
    
    def __init__(self):
        from square import Square
        from square.environment import SquareEnvironment
        
        self.access_token = getattr(settings, 'SQUARE_ACCESS_TOKEN', None)
        self.location_id = getattr(settings, 'SQUARE_LOCATION_ID', None)
        self.environment = getattr(settings, 'SQUARE_ENVIRONMENT', 'sandbox')
        
        if not self.access_token:
            logger.warning("Square access token not configured")
            self.client = None
            return
        
        # Initialize Square client with new SDK pattern
        env = SquareEnvironment.SANDBOX if self.environment == 'sandbox' else SquareEnvironment.PRODUCTION
        self.client = Square(
            token=self.access_token,
            environment=env
        )
        
        logger.info(f"Square payment service initialized (environment: {self.environment})")
    
    @property
    def is_configured(self) -> bool:
        """Check if Square is properly configured."""
        return all([self.client, self.access_token, self.location_id])
    
    def create_payment(
        self,
        source_id: str,
        amount_cents: int,
        currency: str = "USD",
        idempotency_key: Optional[str] = None,
        note: Optional[str] = None,
    ) -> PaymentResult:
        """
        Create a payment using a token from the Web Payments SDK.
        
        Args:
            source_id: Payment token from Web Payments SDK card.tokenize()
            amount_cents: Amount to charge in cents
            currency: Currency code (default: USD)
            idempotency_key: Unique key to prevent duplicate charges
            note: Optional note for the payment
            
        Returns:
            PaymentResult with success status and details
        """
        if not self.is_configured:
            return PaymentResult(
                success=False,
                error_message="Square payments not configured"
            )
        
        if not idempotency_key:
            idempotency_key = str(uuid.uuid4())
        
        try:
            from square.core.api_error import ApiError
            
            # Create payment using new SDK pattern
            response = self.client.payments.create(
                idempotency_key=idempotency_key,
                source_id=source_id,
                amount_money={
                    "amount": amount_cents,
                    "currency": currency
                },
                location_id=self.location_id,
                note=note
            )
            
            payment = response.payment
            logger.info(f"Payment successful: {payment.id}")
            
            return PaymentResult(
                success=True,
                payment_id=payment.id,
                receipt_url=payment.receipt_url
            )
            
        except ApiError as e:
            error_msg = str(e.message) if hasattr(e, 'message') else str(e)
            logger.error(f"Square payment failed: {error_msg}")
            
            # Extract more detailed error if available
            if hasattr(e, 'errors') and e.errors:
                error_details = [err.detail for err in e.errors if hasattr(err, 'detail')]
                if error_details:
                    error_msg = "; ".join(error_details)
            
            return PaymentResult(
                success=False,
                error_message=error_msg
            )
        except Exception as e:
            logger.exception(f"Unexpected error during payment: {e}")
            return PaymentResult(
                success=False,
                error_message="An unexpected error occurred during payment processing"
            )
    
    def get_location(self):
        """Get the configured Square location details."""
        if not self.is_configured:
            return None
        
        try:
            response = self.client.locations.get(location_id=self.location_id)
            return response.location
        except Exception as e:
            logger.error(f"Failed to get location: {e}")
            return None


# Global service instance
payment_service = SquarePaymentService()
