"""
DRF Error Handling Patterns - Working Code Examples

This module contains practical, working examples of error handling patterns
in Django REST Framework. Use these as reference for implementing robust
error handling in your own projects.
"""

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets, serializers
from rest_framework.decorators import api_view, action
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    Throttled,
    ValidationError,
    ErrorDetail,
    ParseError,
    MethodNotAllowed,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler, APIView
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# CUSTOM EXCEPTIONS
# =============================================================================

class PaymentRequired(APIException):
    """Raised when payment is required to access a resource."""
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = 'Payment required to access this resource.'
    default_code = 'payment_required'


class ServiceUnavailable(APIException):
    """Raised when an external service is unavailable."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Service temporarily unavailable, try again later.'
    default_code = 'service_unavailable'


class ResourceConflict(APIException):
    """Raised when there's a conflict with the current state."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'The request conflicts with the current state.'
    default_code = 'conflict'


class InsufficientStock(APIException):
    """Raised when there's insufficient stock for an order."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Insufficient stock.'
    default_code = 'insufficient_stock'

    def __init__(self, product_id, requested, available):
        detail = {
            'message': self.default_detail,
            'product_id': product_id,
            'requested': requested,
            'available': available,
        }
        self.product_id = product_id
        self.requested = requested
        self.available = available
        super().__init__(detail, self.default_code)


class BusinessRuleViolation(APIException):
    """Raised when a business rule is violated."""
    status_code = 422  # Unprocessable Entity
    default_detail = 'Request violates a business rule.'
    default_code = 'business_rule_violation'

    def __init__(self, rule_name, rule_description=None, detail=None, code=None):
        if detail is None:
            detail = {
                'message': self.default_detail,
                'rule': rule_name,
                'description': rule_description or self.default_detail,
            }

        self.rule_name = rule_name
        self.rule_description = rule_description
        super().__init__(detail, code)


class ExternalServiceError(APIException):
    """Raised when an external service fails."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'External service temporarily unavailable.'
    default_code = 'external_service_error'

    def __init__(self, service_name, error_message=None, request_id=None):
        detail = {
            'message': self.default_detail,
            'service': service_name,
        }
        if request_id:
            detail['request_id'] = request_id

        self.service_name = service_name
        self.error_message = error_message
        self.request_id = request_id
        super().__init__(detail, self.default_code)


# =============================================================================
# EXCEPTION HANDLERS
# =============================================================================

def production_exception_handler(exc, context):
    """
    Production-ready exception handler with logging and consistent formatting.
    """
    # Call DRF's default handler first
    response = exception_handler(exc, context)

    # Get request and view info
    request = context.get('request')
    view = context.get('view')

    # Build logging context
    log_context = {
        'exception_type': exc.__class__.__name__,
        'path': request.path if request else None,
        'method': request.method if request else None,
        'user_id': getattr(request.user, 'id', None) if request and hasattr(request, 'user') else None,
        'view': view.__class__.__name__ if view else None,
    }

    if response is not None:
        # Add consistent fields to all error responses
        response.data = {
            'error': {
                'code': getattr(exc, 'default_code', 'error'),
                'message': str(exc.detail) if not isinstance(exc.detail, (dict, list)) else 'An error occurred',
                'status': response.status_code,
            }
        }

        # Add details if error is structured
        if isinstance(exc.detail, (dict, list)):
            response.data['error']['details'] = exc.detail

        # Add request ID if available
        if request and hasattr(request, 'id'):
            response.data['error']['request_id'] = request.id

        # Log based on severity
        log_context['status_code'] = response.status_code
        if response.status_code >= 500:
            logger.error(f"Server error: {exc}", extra=log_context, exc_info=True)
        elif response.status_code >= 400:
            logger.warning(f"Client error: {exc}", extra=log_context)

    else:
        # Unhandled exception
        logger.exception(f"Unhandled exception: {exc}", extra=log_context)

        # Return generic error response
        response = Response(
            {
                'error': {
                    'code': 'internal_error',
                    'message': 'An unexpected error occurred',
                    'status': 500,
                    'request_id': getattr(request, 'id', None) if request else None,
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return response


def debug_exception_handler(exc, context):
    """
    Development exception handler with extra debugging information.
    """
    from django.conf import settings
    import traceback

    response = exception_handler(exc, context)

    if settings.DEBUG:
        if response is not None:
            # Add debug info
            response.data['debug'] = {
                'exception_type': exc.__class__.__name__,
                'exception_module': exc.__class__.__module__,
                'view': context['view'].__class__.__name__,
            }

            # Add full error details for validation errors
            if hasattr(exc, 'get_full_details'):
                response.data['debug']['full_details'] = exc.get_full_details()

        else:
            # Unhandled exception - show full traceback
            response = Response(
                {
                    'detail': 'Internal server error',
                    'exception': str(exc),
                    'exception_type': exc.__class__.__name__,
                    'traceback': traceback.format_exc(),
                },
                status=500
            )

    return response


# =============================================================================
# VIEW EXAMPLES
# =============================================================================

@api_view(['GET'])
def basic_error_handling(request, user_id):
    """
    Example: Basic error handling in function-based views.
    """
    # Handle Not Found
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise NotFound(f"User with id {user_id} not found")

    # Handle Permission Denied
    if not request.user.has_perm('view_user', user):
        raise PermissionDenied("You don't have permission to view this user")

    # Handle Authentication
    if not request.user.is_authenticated:
        raise NotAuthenticated("Authentication required")

    return Response({'user': user.username})


@api_view(['GET'])
def shortcut_error_handling(request, user_id):
    """
    Example: Using Django shortcuts that automatically raise exceptions.
    """
    # get_object_or_404 automatically raises Http404 (converted to NotFound)
    user = get_object_or_404(User, id=user_id)

    # You can still add custom permission checks
    if user.is_private and user != request.user:
        raise PermissionDenied({
            'detail': 'This profile is private',
            'public_url': f'/api/users/{user_id}/public/'
        })

    return Response({'user': user.username})


@api_view(['POST'])
def validation_error_handling(request):
    """
    Example: Handling validation errors with structured details.
    """
    data = request.data

    # Collect validation errors
    errors = {}

    # Email validation
    if 'email' not in data:
        errors['email'] = ErrorDetail('This field is required', code='required')
    elif not '@' in data.get('email', ''):
        errors['email'] = ErrorDetail('Enter a valid email', code='invalid')

    # Password validation
    if 'password' not in data:
        errors['password'] = ErrorDetail('This field is required', code='required')
    elif len(data.get('password', '')) < 8:
        errors['password'] = ErrorDetail(
            'Password must be at least 8 characters',
            code='min_length'
        )

    # Age validation
    age = data.get('age')
    if age is not None and age < 18:
        errors['age'] = ErrorDetail(
            'Must be at least 18 years old',
            code='min_value'
        )

    # Raise all validation errors at once
    if errors:
        raise ValidationError(errors)

    # Create user...
    return Response({'message': 'User created'}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def non_field_errors_example(request):
    """
    Example: Raising non-field validation errors.
    """
    data = request.data
    start_date = data.get('start_date')
    end_date = data.get('end_date')

    # Check date range
    if start_date and end_date and start_date > end_date:
        raise ValidationError({
            serializers.NON_FIELD_ERRORS: [
                'Start date must be before end date'
            ]
        })

    # Check dependencies
    if data.get('requires_approval') and not data.get('approver_id'):
        raise ValidationError({
            serializers.NON_FIELD_ERRORS: [
                'Approver is required when approval is needed'
            ]
        })

    return Response({'message': 'Event created'})


@api_view(['POST'])
def custom_exception_examples(request):
    """
    Example: Using custom exceptions for domain-specific errors.
    """
    user = request.user

    # Check subscription status
    if not hasattr(user, 'subscription') or not user.subscription.is_active:
        raise PaymentRequired({
            'detail': 'Active subscription required',
            'subscription_plans': '/api/subscriptions/plans/',
            'trial_available': True,
        })

    # Check business rules
    daily_posts = user.posts.filter(created_at__date=timezone.now().date()).count()
    if daily_posts >= 10:
        raise BusinessRuleViolation(
            rule_name='daily_post_limit',
            rule_description='Maximum 10 posts per day'
        )

    # Check stock availability
    product_id = request.data.get('product_id')
    quantity = request.data.get('quantity', 1)

    # Simulate stock check
    available_stock = 5  # Would come from database
    if quantity > available_stock:
        raise InsufficientStock(
            product_id=product_id,
            requested=quantity,
            available=available_stock
        )

    return Response({'message': 'Order created'})


@api_view(['POST'])
def external_service_error_example(request):
    """
    Example: Handling external service errors.
    """
    # Simulate calling an external service
    try:
        # result = payment_gateway.charge(...)
        # If service is down:
        raise ExternalServiceError(
            service_name='Payment Gateway',
            error_message='Connection timeout',
            request_id='req_abc123'
        )
    except ExternalServiceError:
        # Re-raise to return proper error response
        raise
    except Exception as e:
        # Catch unexpected errors
        logger.exception(f"Unexpected error with payment gateway: {e}")
        raise ServiceUnavailable(
            'Payment processing temporarily unavailable'
        )


@api_view(['POST'])
def atomic_transaction_with_errors(request):
    """
    Example: Handling errors in database transactions.
    """
    try:
        with transaction.atomic():
            # Create user
            user = User.objects.create_user(
                username=request.data['username'],
                email=request.data['email']
            )

            # Check if operation should fail
            if request.data.get('trigger_error'):
                # This will rollback the transaction
                raise ResourceConflict('Cannot create user at this time')

            # Create profile
            # user.profile.create(bio=request.data.get('bio'))

            return Response({'user_id': user.id}, status=status.HTTP_201_CREATED)

    except ValidationError:
        # ValidationError from serializer
        raise
    except ResourceConflict:
        # Custom business logic error
        raise
    except Exception as e:
        # Unexpected error
        logger.exception(f"Failed to create user: {e}")
        raise APIException('Failed to create user')


@api_view(['DELETE'])
def delete_with_permission_check(request, resource_id):
    """
    Example: Permission checking with helpful error messages.
    """
    resource = get_object_or_404(Resource, id=resource_id)

    # Check if user is authenticated
    if not request.user.is_authenticated:
        raise NotAuthenticated({
            'detail': 'Login required to delete resources',
            'login_url': '/api/auth/login/'
        })

    # Check if user is the owner
    if resource.owner != request.user:
        # Check if user is admin
        if not request.user.is_staff:
            raise PermissionDenied({
                'detail': 'Only the owner or admins can delete this resource',
                'owner': resource.owner.username,
                'contact_support': '/support/'
            })

    # Delete resource
    resource.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def rate_limited_endpoint(request):
    """
    Example: Handling rate limiting.
    """
    # Check custom rate limit
    user_request_count = get_user_request_count(request.user)

    if user_request_count > 100:
        # Calculate when they can retry
        wait_seconds = calculate_wait_time(request.user)

        raise Throttled(
            wait=wait_seconds,
            detail={
                'message': 'Rate limit exceeded',
                'limit': 100,
                'window': '1 hour',
                'retry_after': wait_seconds,
            }
        )

    return Response({'data': 'response'})


# =============================================================================
# CLASS-BASED VIEW EXAMPLES
# =============================================================================

class UserViewSet(viewsets.ModelViewSet):
    """
    Example: Error handling in ViewSets.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer  # Assume this exists

    def get_object(self):
        """Override to add custom not found message."""
        try:
            return super().get_object()
        except Http404:
            raise NotFound(
                f"User not found. Check available users at /api/users/"
            )

    def perform_create(self, serializer):
        """Validate business rules during creation."""
        # Check if username is blacklisted
        username = serializer.validated_data.get('username')
        if username in BLACKLISTED_USERNAMES:
            raise ValidationError({
                'username': 'This username is not allowed'
            })

        # Check domain-specific rules
        if User.objects.count() >= MAX_USERS:
            raise BusinessRuleViolation(
                rule_name='max_users_limit',
                rule_description=f'Maximum {MAX_USERS} users allowed'
            )

        serializer.save()

    def perform_destroy(self, instance):
        """Add checks before deletion."""
        # Prevent deletion of admin users
        if instance.is_superuser:
            raise PermissionDenied(
                'Cannot delete superuser accounts'
            )

        # Check if user has dependencies
        if instance.posts.exists():
            raise ResourceConflict({
                'detail': 'Cannot delete user with existing posts',
                'posts_count': instance.posts.count(),
                'suggestion': 'Delete or reassign posts first'
            })

        instance.delete()

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Custom action with error handling."""
        user = self.get_object()

        # Check permissions
        if not request.user.is_staff:
            raise PermissionDenied('Only staff can activate users')

        # Check current state
        if user.is_active:
            raise ResourceConflict({
                'detail': 'User is already active',
                'activated_at': user.date_joined.isoformat()
            })

        # Activate user
        user.is_active = True
        user.save()

        return Response({'message': 'User activated'})


class PaymentView(APIView):
    """
    Example: Complex error handling in APIView.
    """

    def post(self, request):
        """Process payment with comprehensive error handling."""
        # Validate request data
        amount = request.data.get('amount')
        card_token = request.data.get('card_token')

        errors = {}
        if not amount:
            errors['amount'] = 'This field is required'
        elif amount <= 0:
            errors['amount'] = 'Amount must be greater than 0'

        if not card_token:
            errors['card_token'] = 'This field is required'

        if errors:
            raise ValidationError(errors)

        # Check user balance
        user_balance = request.user.wallet.balance
        if user_balance < amount:
            raise PaymentRequired({
                'detail': 'Insufficient funds',
                'required': float(amount),
                'available': float(user_balance),
                'shortfall': float(amount - user_balance),
                'top_up_url': '/api/wallet/top-up/'
            })

        # Process payment
        try:
            result = payment_service.charge(
                amount=amount,
                token=card_token,
                user_id=request.user.id
            )
        except PaymentDeclinedError as e:
            raise ValidationError({
                'card_token': f'Payment declined: {e.reason}'
            })
        except PaymentGatewayTimeout:
            raise ServiceUnavailable(
                'Payment gateway timeout. Please try again.'
            )
        except PaymentGatewayError as e:
            logger.error(f"Payment gateway error: {e}", exc_info=True)
            raise ExternalServiceError(
                service_name='Payment Gateway',
                error_message=str(e)
            )

        return Response({
            'transaction_id': result.transaction_id,
            'amount': float(amount),
            'status': 'success'
        })


# =============================================================================
# SERIALIZER ERROR EXAMPLES
# =============================================================================

class UserSerializer(serializers.Serializer):
    """Example serializer with custom validation."""
    username = serializers.CharField(max_length=20)
    email = serializers.EmailField()
    age = serializers.IntegerField(required=False)
    password = serializers.CharField(write_only=True)

    def validate_username(self, value):
        """Field-level validation."""
        if len(value) < 3:
            raise ValidationError(
                ErrorDetail(
                    'Username must be at least 3 characters',
                    code='min_length'
                )
            )

        if User.objects.filter(username=value).exists():
            raise ValidationError(
                ErrorDetail(
                    'This username is already taken',
                    code='unique'
                )
            )

        return value

    def validate_email(self, value):
        """Email validation."""
        # Check if email domain is allowed
        domain = value.split('@')[1]
        if domain in BLOCKED_DOMAINS:
            raise ValidationError(
                ErrorDetail(
                    f'Email domain {domain} is not allowed',
                    code='blocked_domain'
                )
            )

        return value

    def validate(self, data):
        """Object-level validation."""
        # Check age restriction for certain usernames
        if 'age' in data and data['age'] < 13:
            raise ValidationError({
                'age': ErrorDetail(
                    'Must be at least 13 years old',
                    code='min_age'
                )
            })

        # Password strength check
        password = data.get('password', '')
        if len(password) < 8:
            raise ValidationError({
                'password': ErrorDetail(
                    'Password must be at least 8 characters',
                    code='password_too_short'
                )
            })

        return data


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_user_request_count(user):
    """Get user's request count (placeholder)."""
    return 0


def calculate_wait_time(user):
    """Calculate wait time for throttled user (placeholder)."""
    return 60


# =============================================================================
# MOCK DATA AND CONSTANTS
# =============================================================================

BLACKLISTED_USERNAMES = ['admin', 'root', 'system']
MAX_USERS = 10000
BLOCKED_DOMAINS = ['example.com', 'spam.com']


# Placeholder classes for examples
class Resource:
    """Mock Resource model."""
    pass


class UserSerializer(serializers.ModelSerializer):
    """Mock UserSerializer."""
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


# Mock external service classes
class PaymentDeclinedError(Exception):
    """Mock payment declined error."""
    def __init__(self, reason):
        self.reason = reason


class PaymentGatewayTimeout(Exception):
    """Mock payment gateway timeout."""
    pass


class PaymentGatewayError(Exception):
    """Mock payment gateway error."""
    pass


class payment_service:
    """Mock payment service."""
    @staticmethod
    def charge(amount, token, user_id):
        """Mock charge method."""
        class Result:
            transaction_id = 'txn_123'
        return Result()


# =============================================================================
# TESTING EXAMPLES
# =============================================================================

"""
# Example test cases for error handling

from rest_framework.test import APITestCase
from rest_framework import status

class ErrorHandlingTests(APITestCase):
    def test_not_found_error(self):
        response = self.client.get('/api/users/999999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('detail', response.data)

    def test_validation_error_structure(self):
        response = self.client.post('/api/users/', {
            'email': 'invalid',
            'age': -5
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertIn('age', response.data)

    def test_permission_denied(self):
        other_user = User.objects.create_user('other', 'other@example.com')
        response = self.client.delete(f'/api/users/{other_user.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_custom_exception_codes(self):
        response = self.client.post('/api/orders/', {
            'product_id': 1,
            'quantity': 1000  # More than available
        })
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['code'], 'insufficient_stock')
"""
