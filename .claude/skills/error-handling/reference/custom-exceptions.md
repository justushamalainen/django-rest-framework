# Creating Custom Exceptions

Learn how to create custom exception classes for domain-specific errors in your Django REST Framework API.

## Table of Contents

- [Why Create Custom Exceptions](#why-create-custom-exceptions)
- [Basic Custom Exception](#basic-custom-exception)
- [Exceptions with Custom Status Codes](#exceptions-with-custom-status-codes)
- [Exceptions with Dynamic Details](#exceptions-with-dynamic-details)
- [Exceptions with Additional Attributes](#exceptions-with-additional-attributes)
- [Error Code Patterns](#error-code-patterns)
- [Organizing Custom Exceptions](#organizing-custom-exceptions)
- [Testing Custom Exceptions](#testing-custom-exceptions)

## Why Create Custom Exceptions

Create custom exceptions when:

1. **Domain-specific errors** need clear, semantic naming
2. **Non-standard HTTP status codes** are required (402, 422, 503, etc.)
3. **Additional context** beyond detail/code is needed
4. **Consistent error handling** across related operations
5. **API documentation** benefits from explicit exception types

## Basic Custom Exception

The simplest custom exception inherits from `APIException`:

```python
# myapp/exceptions.py
from rest_framework import status
from rest_framework.exceptions import APIException

class ResourceConflict(APIException):
    """Raised when a resource conflict occurs."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'The request conflicts with the current state of the resource.'
    default_code = 'conflict'

# Usage
from myapp.exceptions import ResourceConflict

@api_view(['POST'])
def create_booking(request):
    slot = get_object_or_404(TimeSlot, id=request.data['slot_id'])

    if slot.is_booked:
        raise ResourceConflict('This time slot is already booked')

    # Create booking...
```

## Exceptions with Custom Status Codes

DRF includes most common status codes, but you can use any valid HTTP status:

```python
from rest_framework import status
from rest_framework.exceptions import APIException

class PaymentRequired(APIException):
    """HTTP 402 - Payment Required"""
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = 'Payment is required to access this resource.'
    default_code = 'payment_required'

class UnprocessableEntity(APIException):
    """HTTP 422 - Unprocessable Entity"""
    status_code = 422
    default_detail = 'The request was well-formed but contains semantic errors.'
    default_code = 'unprocessable_entity'

class Locked(APIException):
    """HTTP 423 - Locked"""
    status_code = 423
    default_detail = 'The resource is locked.'
    default_code = 'locked'

class FailedDependency(APIException):
    """HTTP 424 - Failed Dependency"""
    status_code = 424
    default_detail = 'The request failed due to failure of a previous request.'
    default_code = 'failed_dependency'

class ServiceUnavailable(APIException):
    """HTTP 503 - Service Unavailable"""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Service temporarily unavailable. Please try again later.'
    default_code = 'service_unavailable'

class GatewayTimeout(APIException):
    """HTTP 504 - Gateway Timeout"""
    status_code = 504
    default_detail = 'The upstream server failed to respond in time.'
    default_code = 'gateway_timeout'

# Usage examples
@api_view(['GET'])
def get_premium_content(request):
    if not request.user.is_subscribed:
        raise PaymentRequired({
            'detail': 'Active subscription required',
            'upgrade_url': '/subscriptions/plans/',
            'trial_available': True
        })
    # Return content...

@api_view(['POST'])
def process_with_external_api(request):
    try:
        result = external_service.process(request.data)
    except ExternalServiceTimeout:
        raise GatewayTimeout('External service timed out')
    except ExternalServiceDown:
        raise ServiceUnavailable('External service is temporarily down')

    return Response(result)
```

## Exceptions with Dynamic Details

Override `__init__` to customize exception details dynamically:

```python
from rest_framework.exceptions import APIException
from rest_framework import status

class RateLimitExceeded(APIException):
    """Custom rate limit exception with dynamic wait time."""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = 'Rate limit exceeded.'
    default_code = 'rate_limit_exceeded'

    def __init__(self, wait_seconds=None, limit=None, detail=None, code=None):
        if detail is None:
            detail = self.default_detail
            if wait_seconds:
                detail = f'{detail} Try again in {wait_seconds} seconds.'
            if limit:
                detail = f'{detail} Limit: {limit} requests.'

        self.wait_seconds = wait_seconds
        self.limit = limit
        super().__init__(detail, code)

# Usage
@api_view(['POST'])
def expensive_endpoint(request):
    limit_info = check_rate_limit(request.user)

    if limit_info['exceeded']:
        raise RateLimitExceeded(
            wait_seconds=limit_info['retry_after'],
            limit=limit_info['max_requests']
        )

    # Process request...
```

### Exception with Required Parameters

```python
class InsufficientFunds(APIException):
    """Raised when account balance is insufficient."""
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = 'Insufficient funds to complete this transaction.'
    default_code = 'insufficient_funds'

    def __init__(self, required_amount, available_amount, currency='USD'):
        detail = {
            'message': self.default_detail,
            'required': f'{required_amount} {currency}',
            'available': f'{available_amount} {currency}',
            'shortfall': f'{required_amount - available_amount} {currency}'
        }
        self.required_amount = required_amount
        self.available_amount = available_amount
        self.currency = currency
        super().__init__(detail, self.default_code)

# Usage
@api_view(['POST'])
def purchase_item(request):
    item = get_object_or_404(Item, id=request.data['item_id'])
    user_balance = request.user.wallet.balance

    if user_balance < item.price:
        raise InsufficientFunds(
            required_amount=item.price,
            available_amount=user_balance
        )

    # Process purchase...
```

## Exceptions with Additional Attributes

Add custom attributes for exception handlers or logging:

```python
class BusinessRuleViolation(APIException):
    """Raised when a business rule is violated."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = 'The request violates a business rule.'
    default_code = 'business_rule_violation'

    def __init__(self, rule_name, rule_description=None, detail=None, code=None):
        if detail is None:
            detail = {
                'message': self.default_detail,
                'rule': rule_name,
                'description': rule_description
            }

        self.rule_name = rule_name
        self.rule_description = rule_description
        super().__init__(detail, code)

# Usage
@api_view(['POST'])
def create_order(request):
    user = request.user
    cart_total = calculate_cart_total(request.data['items'])

    # Check business rules
    if cart_total < 10:
        raise BusinessRuleViolation(
            rule_name='minimum_order_value',
            rule_description='Order must be at least $10'
        )

    if user.orders.filter(created_today=True).count() >= 5:
        raise BusinessRuleViolation(
            rule_name='daily_order_limit',
            rule_description='Maximum 5 orders per day',
            detail={
                'message': 'Daily order limit exceeded',
                'rule': 'daily_order_limit',
                'limit': 5,
                'current': user.orders.filter(created_today=True).count(),
                'reset_time': get_next_day_start()
            }
        )

    # Create order...
```

### Exception with Metadata for Logging

```python
class ExternalServiceError(APIException):
    """Raised when an external service fails."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'An external service is temporarily unavailable.'
    default_code = 'external_service_error'

    def __init__(self, service_name, error_message=None, request_id=None, detail=None, code=None):
        if detail is None:
            detail = {
                'message': self.default_detail,
                'service': service_name
            }
            if request_id:
                detail['request_id'] = request_id

        self.service_name = service_name
        self.error_message = error_message
        self.request_id = request_id
        super().__init__(detail, code)

# Usage with custom exception handler
def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, ExternalServiceError):
        # Log with additional context
        logger.error(
            f"External service failure: {exc.service_name}",
            extra={
                'service': exc.service_name,
                'error_message': exc.error_message,
                'request_id': exc.request_id,
                'view': context['view'].__class__.__name__,
            }
        )

    return response

# In view
@api_view(['POST'])
def sync_with_crm(request):
    try:
        result = crm_service.sync_contact(request.data)
    except CRMServiceError as e:
        raise ExternalServiceError(
            service_name='CRM',
            error_message=str(e),
            request_id=e.request_id
        )

    return Response(result)
```

## Error Code Patterns

Consistent error codes help clients handle errors programmatically:

```python
# Domain-based error codes
class InventoryException(APIException):
    status_code = status.HTTP_409_CONFLICT

class OutOfStock(InventoryException):
    default_code = 'inventory.out_of_stock'
    default_detail = 'Product is out of stock.'

class InsufficientStock(InventoryException):
    default_code = 'inventory.insufficient_stock'
    default_detail = 'Insufficient stock for requested quantity.'

    def __init__(self, product, requested, available):
        detail = {
            'message': self.default_detail,
            'product_id': product.id,
            'requested': requested,
            'available': available
        }
        self.product = product
        self.requested = requested
        self.available = available
        super().__init__(detail, self.default_code)

# Hierarchical error codes
class PaymentException(APIException):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    error_category = 'payment'

class PaymentDeclined(PaymentException):
    default_code = 'payment.declined'
    default_detail = 'Payment was declined.'

class CardExpired(PaymentException):
    default_code = 'payment.card.expired'
    default_detail = 'Credit card has expired.'

class InsufficientFundsError(PaymentException):
    default_code = 'payment.insufficient_funds'
    default_detail = 'Insufficient funds.'

# Usage
@api_view(['POST'])
def process_payment(request):
    try:
        result = payment_gateway.charge(
            amount=request.data['amount'],
            card=request.data['card_token']
        )
    except CardExpiredException:
        raise CardExpired()
    except DeclinedException as e:
        raise PaymentDeclined(detail={
            'message': 'Payment declined',
            'reason': e.reason,
            'retry_allowed': e.can_retry
        })

    return Response(result)
```

## Organizing Custom Exceptions

### Project Structure

```
myproject/
├── myapp/
│   ├── exceptions.py       # App-specific exceptions
│   └── views.py
├── orders/
│   ├── exceptions.py       # Order-related exceptions
│   └── views.py
└── common/
    ├── exceptions.py       # Shared exceptions
    └── handlers.py         # Custom exception handler
```

### Shared Exceptions Module

```python
# common/exceptions.py
"""Shared exception classes used across the project."""

from rest_framework import status
from rest_framework.exceptions import APIException

class BaseProjectException(APIException):
    """Base exception for all project exceptions."""
    pass

class ResourceLocked(BaseProjectException):
    status_code = 423
    default_code = 'resource_locked'
    default_detail = 'The resource is locked by another process.'

class OperationTimeout(BaseProjectException):
    status_code = 504
    default_code = 'operation_timeout'
    default_detail = 'The operation timed out.'

class MaintenanceMode(BaseProjectException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = 'maintenance_mode'
    default_detail = 'The service is currently in maintenance mode.'

# Import in apps
from common.exceptions import ResourceLocked, MaintenanceMode
```

### Domain-Specific Exceptions

```python
# orders/exceptions.py
"""Order-related exception classes."""

from rest_framework import status
from common.exceptions import BaseProjectException

class OrderException(BaseProjectException):
    """Base exception for order-related errors."""
    pass

class OrderNotFound(OrderException):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = 'order.not_found'
    default_detail = 'Order not found.'

class OrderAlreadyCancelled(OrderException):
    status_code = status.HTTP_409_CONFLICT
    default_code = 'order.already_cancelled'
    default_detail = 'Order has already been cancelled.'

class OrderCannotBeCancelled(OrderException):
    status_code = status.HTTP_409_CONFLICT
    default_code = 'order.cannot_cancel'
    default_detail = 'Order cannot be cancelled at this stage.'

    def __init__(self, order_status, reason=None):
        detail = {
            'message': self.default_detail,
            'order_status': order_status
        }
        if reason:
            detail['reason'] = reason

        self.order_status = order_status
        super().__init__(detail, self.default_code)
```

## Testing Custom Exceptions

### Unit Tests

```python
# tests/test_exceptions.py
from django.test import TestCase
from rest_framework import status
from myapp.exceptions import (
    InsufficientStock,
    PaymentDeclined,
    ResourceLocked
)

class CustomExceptionTests(TestCase):
    def test_insufficient_stock_exception(self):
        """Test InsufficientStock exception structure."""
        exc = InsufficientStock(
            product=self.product,
            requested=10,
            available=5
        )

        self.assertEqual(exc.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(exc.detail['requested'], 10)
        self.assertEqual(exc.detail['available'], 5)

    def test_exception_error_code(self):
        """Test custom error codes."""
        exc = PaymentDeclined()
        self.assertEqual(exc.get_codes(), 'payment.declined')

    def test_exception_full_details(self):
        """Test get_full_details() method."""
        exc = ResourceLocked('Resource is being updated')

        details = exc.get_full_details()
        self.assertEqual(details['message'], 'Resource is being updated')
        self.assertEqual(details['code'], 'resource_locked')
```

### Integration Tests

```python
# tests/test_views.py
from rest_framework.test import APITestCase
from rest_framework import status

class OrderViewTests(APITestCase):
    def test_cancel_shipped_order_returns_conflict(self):
        """Test that cancelling a shipped order returns 409."""
        order = self.create_shipped_order()

        response = self.client.post(f'/api/orders/{order.id}/cancel/')

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['code'], 'order.cannot_cancel')
        self.assertIn('order_status', response.data)

    def test_insufficient_stock_response(self):
        """Test insufficient stock error response."""
        product = self.create_product(stock=5)

        response = self.client.post('/api/orders/', {
            'items': [{'product_id': product.id, 'quantity': 10}]
        })

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['code'], 'inventory.insufficient_stock')
        self.assertEqual(response.data['requested'], 10)
        self.assertEqual(response.data['available'], 5)
```

## Best Practices

1. **Inherit from APIException** for all custom exceptions
2. **Use semantic names** that clearly indicate the error type
3. **Set appropriate status codes** based on HTTP standards
4. **Define default_code** for programmatic error handling
5. **Include helpful detail** that guides users to resolve the issue
6. **Add custom attributes** sparingly, only when needed
7. **Document exceptions** in docstrings and API docs
8. **Test exception behavior** in unit and integration tests
9. **Organize by domain** in separate modules
10. **Log exceptions** with appropriate context

## Anti-Patterns to Avoid

### Don't Create Too Many Exceptions

```python
# Bad: Too granular
class UsernameTooShort(ValidationError): pass
class UsernameHasSpaces(ValidationError): pass
class UsernameHasNumbers(ValidationError): pass

# Good: Use ValidationError with specific details
raise ValidationError({
    'username': 'Username must be 3-20 characters, no spaces or numbers'
})
```

### Don't Expose Internal Details

```python
# Bad: Exposes internal structure
raise APIException(f'Database query failed: {db_error}')

# Good: User-friendly message, log details separately
logger.exception(f'Database error: {db_error}')
raise ServiceUnavailable('Service temporarily unavailable')
```

### Don't Override Exception Handling Logic

```python
# Bad: Custom exception tries to return response
class BadException(APIException):
    def __init__(self):
        super().__init__()
        # Don't do this!
        self.response = Response({'error': 'bad'})

# Good: Let exception handler create the response
class GoodException(APIException):
    default_detail = 'An error occurred'
```

## Related Documentation

- [Built-in Exceptions](./builtin-exceptions.md)
- [Exception Handlers](./exception-handlers.md)
- [Error Responses](./error-responses.md)
- [Error Patterns](./examples/error-patterns.py)

## Source Reference

- `/home/user/django-rest-framework/rest_framework/exceptions.py` - Base exception classes
