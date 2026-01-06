# Permission Composition (AND, OR, NOT)

**CRITICAL:** This is one of the most frequently asked about features in DRF permissions.

DRF allows composing permissions using Python operators: `&` (AND), `|` (OR), and `~` (NOT).

## Table of Contents

- [Quick Reference](#quick-reference)
- [How It Works](#how-it-works)
- [AND Operator (&)](#and-operator-)
- [OR Operator (|)](#or-operator-)
- [NOT Operator (~)](#not-operator-)
- [Operator Precedence](#operator-precedence)
- [Complex Compositions](#complex-compositions)
- [Edge Cases and Gotchas](#edge-cases-and-gotchas)
- [Performance Considerations](#performance-considerations)
- [Anti-patterns](#anti-patterns)
- [Real-World Examples](#real-world-examples)

---

## Quick Reference

```python
from rest_framework.permissions import IsAuthenticated, IsAdminUser

# AND: Both must pass
permission_classes = [IsAuthenticated & IsAdminUser]
# Equivalent to:
permission_classes = [IsAuthenticated, IsAdminUser]

# OR: Either can pass
permission_classes = [IsAuthenticated | IsAdminUser]

# NOT: Invert the permission
permission_classes = [~IsAuthenticated]  # Only anonymous users

# Complex: (Admin OR Owner) AND Authenticated
permission_classes = [(IsAdminUser | IsOwner) & IsAuthenticated]

# Multiple operators
permission_classes = [IsAdminUser | (IsAuthenticated & HasSubscription)]
```

---

## How It Works

### The Implementation

DRF uses Python magic methods to enable operator overloading:

```python
class OperationHolderMixin:
    def __and__(self, other):
        return OperandHolder(AND, self, other)

    def __or__(self, other):
        return OperandHolder(OR, self, other)

    def __invert__(self):
        return SingleOperandHolder(NOT, self)
```

When you write `IsAuthenticated & IsAdminUser`, Python calls:
1. `IsAuthenticated.__and__(IsAdminUser)`
2. Returns `OperandHolder(AND, IsAuthenticated, IsAdminUser)`
3. When instantiated, creates an `AND` instance that evaluates both permissions

### Operator Classes

**AND:**
```python
class AND:
    def __init__(self, op1, op2):
        self.op1 = op1
        self.op2 = op2

    def has_permission(self, request, view):
        return (
            self.op1.has_permission(request, view) and
            self.op2.has_permission(request, view)
        )

    def has_object_permission(self, request, view, obj):
        return (
            self.op1.has_object_permission(request, view, obj) and
            self.op2.has_object_permission(request, view, obj)
        )
```

**OR:**
```python
class OR:
    def __init__(self, op1, op2):
        self.op1 = op1
        self.op2 = op2

    def has_permission(self, request, view):
        return (
            self.op1.has_permission(request, view) or
            self.op2.has_permission(request, view)
        )

    def has_object_permission(self, request, view, obj):
        return (
            self.op1.has_permission(request, view)
            and self.op1.has_object_permission(request, view, obj)
        ) or (
            self.op2.has_permission(request, view)
            and self.op2.has_object_permission(request, view, obj)
        )
```

**NOT:**
```python
class NOT:
    def __init__(self, op1):
        self.op1 = op1

    def has_permission(self, request, view):
        return not self.op1.has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        return not self.op1.has_object_permission(request, view, obj)
```

---

## AND Operator (&)

**Behavior:** BOTH permissions must return True.

### Basic Usage

```python
from rest_framework.permissions import IsAuthenticated, IsAdminUser

# Using & operator
permission_classes = [IsAuthenticated & IsAdminUser]
```

### Equivalent Forms

```python
# These are functionally equivalent for AND:

# Form 1: List of permissions (implicit AND)
permission_classes = [IsAuthenticated, IsAdminUser]

# Form 2: Explicit & operator
permission_classes = [IsAuthenticated & IsAdminUser]
```

**When to use `&`:** When combining with OR operators or for explicit clarity.

### Evaluation Order

**Short-circuit evaluation:** If the first permission returns False, the second is NOT evaluated.

```python
# Example: IsAuthenticated & IsAdminUser
# 1. Evaluates IsAuthenticated.has_permission()
# 2. If False, stops and returns False (never checks IsAdminUser)
# 3. If True, evaluates IsAdminUser.has_permission()
```

### Practical Example

```python
class IsVerifiedUser(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.email_verified

class HasSubscription(BasePermission):
    def has_permission(self, request, view):
        return request.user.subscription_active

# Both conditions must be true
permission_classes = [IsVerifiedUser & HasSubscription]
```

---

## OR Operator (|)

**Behavior:** EITHER permission can return True.

### Basic Usage

```python
from rest_framework.permissions import IsAuthenticated, IsAdminUser

# Admin OR authenticated user
permission_classes = [IsAdminUser | IsAuthenticated]
```

### Why Use OR

OR is useful when you have multiple valid ways to grant access:

```python
# Example: Admin staff OR the owner can access
permission_classes = [IsAdminUser | IsOwner]
```

### Evaluation Order

**Short-circuit evaluation:** If the first permission returns True, the second is NOT evaluated.

```python
# Example: IsAdminUser | IsOwner
# 1. Evaluates IsAdminUser.has_permission()
# 2. If True, stops and returns True (never checks IsOwner)
# 3. If False, evaluates IsOwner.has_permission()
```

### CRITICAL: OR with Object Permissions

The OR operator has **special behavior** for `has_object_permission()`:

```python
def has_object_permission(self, request, view, obj):
    # Note: Checks has_permission AGAIN for each operand!
    return (
        self.op1.has_permission(request, view)
        and self.op1.has_object_permission(request, view, obj)
    ) or (
        self.op2.has_permission(request, view)
        and self.op2.has_object_permission(request, view, obj)
    )
```

**Why?** This prevents bypassing view-level checks through object-level permissions.

### Practical Example

```python
class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_staff

class IsOwner(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user

# Admin OR owner can access
permission_classes = [IsAdminUser | IsOwner]

# For retrieve/update/destroy:
# - If admin: has_permission (admin check) → True, allow access
# - If not admin: has_permission (authenticated check) → has_object_permission (owner check)
```

---

## NOT Operator (~)

**Behavior:** INVERTS the permission result.

### Basic Usage

```python
from rest_framework.permissions import IsAuthenticated

# Only anonymous users
permission_classes = [~IsAuthenticated]
```

### Use Cases

#### 1. Anonymous-Only Endpoints

```python
class SignupView(APIView):
    """Only allow anonymous users to sign up"""
    permission_classes = [~IsAuthenticated]

    def post(self, request):
        # Create new user account
        pass
```

#### 2. Non-Admin Users

```python
from rest_framework.permissions import IsAdminUser

# Regular users only (not admin)
permission_classes = [IsAuthenticated & ~IsAdminUser]
```

#### 3. Exclude Specific Roles

```python
class IsBannedUser(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_banned

# Allow anyone except banned users
permission_classes = [~IsBannedUser]
```

### Practical Example

```python
class PublicRegistrationView(CreateAPIView):
    """
    User registration endpoint - only accessible to non-authenticated users.
    Prevents authenticated users from creating additional accounts.
    """
    permission_classes = [~IsAuthenticated]
    serializer_class = UserRegistrationSerializer

    def post(self, request):
        # Handle registration
        pass
```

---

## Operator Precedence

Python's operator precedence applies:

**Precedence (highest to lowest):**
1. `~` (NOT) - Unary operator
2. `&` (AND)
3. `|` (OR)

### Examples

```python
# Expression: A | B & C
# Evaluates as: A | (B & C)
IsAdminUser | IsAuthenticated & HasSubscription
# = IsAdminUser | (IsAuthenticated & HasSubscription)

# Expression: ~A & B
# Evaluates as: (~A) & B
~IsAdminUser & IsAuthenticated
# = (~IsAdminUser) & IsAuthenticated

# Expression: A & B | C & D
# Evaluates as: (A & B) | (C & D)
IsAuthenticated & IsAdminUser | IsOwner & IsPublished
# = (IsAuthenticated & IsAdminUser) | (IsOwner & IsPublished)
```

### Use Parentheses for Clarity

**Always use parentheses** for complex expressions to ensure correct evaluation:

```python
# AMBIGUOUS (relies on precedence rules)
permission_classes = [IsAdminUser | IsAuthenticated & HasSubscription]

# CLEAR (explicit grouping)
permission_classes = [IsAdminUser | (IsAuthenticated & HasSubscription)]
```

---

## Complex Compositions

### Multiple Operators

```python
# Admin OR (Authenticated AND HasPremium AND NotBanned)
permission_classes = [
    IsAdminUser | (IsAuthenticated & HasPremium & ~IsBanned)
]
```

### Nested Compositions

```python
# (Admin OR Manager) AND (HasDepartmentAccess OR IsSuperUser)
permission_classes = [
    (IsAdminUser | IsManager) & (HasDepartmentAccess | IsSuperUser)
]
```

### Chaining Multiple Permissions

```python
# Admin OR (Owner AND Verified AND Active)
permission_classes = [
    IsAdminUser | (IsOwner & IsEmailVerified & IsAccountActive)
]
```

---

## Edge Cases and Gotchas

### Gotcha 1: OR Re-checks has_permission

```python
class IsOwner(BasePermission):
    def has_permission(self, request, view):
        print("Checking has_permission")
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        print("Checking has_object_permission")
        return obj.owner == request.user

permission_classes = [IsAdminUser | IsOwner]

# For object access, you'll see:
# "Checking has_permission" (view-level)
# "Checking has_permission" (during has_object_permission for OR)
# "Checking has_object_permission" (object-level)
```

**Why?** OR's `has_object_permission` calls `has_permission` again to prevent bypassing view-level checks.

### Gotcha 2: Multiple Permissions List vs Composition

```python
# These are DIFFERENT:

# Option A: List of permission instances (all must pass)
permission_classes = [IsAuthenticated, IsAdminUser]
# Both IsAuthenticated AND IsAdminUser must pass

# Option B: Composed permission (all must pass)
permission_classes = [IsAuthenticated & IsAdminUser]
# Both IsAuthenticated AND IsAdminUser must pass

# They're equivalent for AND, but different for OR:

# Option C: List with OR (WRONG - won't work as expected)
# permission_classes = [IsAuthenticated, IsAdminUser]  # AND, not OR!

# Option D: Single composed OR (CORRECT)
permission_classes = [IsAuthenticated | IsAdminUser]  # OR
```

### Gotcha 3: NOT with Object Permissions

```python
class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user

# NOT inverts BOTH methods
permission_classes = [~IsOwner]

# For objects:
# - Returns True if user is NOT the owner
# - Be careful: May allow unintended access!
```

### Gotcha 4: Composition with DjangoModelPermissions

```python
from rest_framework.permissions import DjangoModelPermissions

# This might not work as expected:
permission_classes = [DjangoModelPermissions | IsOwner]

# DjangoModelPermissions requires view.queryset, so combining with
# other permissions may cause issues if they don't have the same requirements
```

### Gotcha 5: Short-Circuit Evaluation Side Effects

```python
class LoggingPermission(BasePermission):
    def has_permission(self, request, view):
        logger.info(f"Permission check for {request.user}")
        return True

# With OR, second permission may not be evaluated:
permission_classes = [IsAdminUser | LoggingPermission]

# If user is admin, LoggingPermission.has_permission() is NEVER called!
```

---

## Performance Considerations

### 1. Order Matters for OR

```python
# GOOD: Check cheapest permission first
permission_classes = [IsAdminUser | ExpensivePermissionCheck]

# BAD: Expensive check runs first
permission_classes = [ExpensivePermissionCheck | IsAdminUser]
```

**Reasoning:** If the first operand passes, the second is never evaluated (short-circuit).

### 2. Avoid Redundant Checks

```python
# REDUNDANT: IsAdminUser implies is_authenticated
permission_classes = [IsAuthenticated & IsAdminUser]

# BETTER: Just check IsAdminUser
permission_classes = [IsAdminUser]
```

### 3. Database Queries in Composed Permissions

```python
# BAD: Multiple database queries
class HasActiveSubscription(BasePermission):
    def has_permission(self, request, view):
        return Subscription.objects.filter(
            user=request.user, active=True
        ).exists()

permission_classes = [IsAuthenticated & HasActiveSubscription]

# BETTER: Cache on user model
class HasActiveSubscription(BasePermission):
    def has_permission(self, request, view):
        # Assumes user.has_active_subscription is a cached property
        return request.user.has_active_subscription
```

### 4. Complex Compositions

```python
# Can become hard to debug:
permission_classes = [
    (IsAdminUser | (IsManager & HasDepartmentAccess)) &
    (IsAuthenticated | IsSpecialGuest) &
    ~IsBanned
]

# Consider creating a single custom permission class for clarity:
class ComplexAccessPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        if user.is_banned:
            return False

        if user.is_admin:
            return True

        if user.is_manager and user.has_department_access:
            return True

        return user.is_authenticated or user.is_special_guest
```

---

## Anti-patterns

### ❌ Anti-pattern 1: Overusing Composition

```python
# BAD: Hard to understand and debug
permission_classes = [
    (A | (B & C)) & (~D | E) & (F | G | H)
]

# GOOD: Custom permission with clear logic
class CombinedPermission(BasePermission):
    def has_permission(self, request, view):
        # Clear, testable logic
        if condition_a:
            return True
        if condition_b and condition_c:
            return True
        return False
```

### ❌ Anti-pattern 2: Composition with Side Effects

```python
# BAD: Logging permission that may not execute
class LogAccess(BasePermission):
    def has_permission(self, request, view):
        AccessLog.objects.create(user=request.user, view=view)
        return True

# Short-circuit may prevent logging
permission_classes = [IsAdminUser | LogAccess]

# GOOD: Use middleware or view methods for side effects
```

### ❌ Anti-pattern 3: NOT without Authentication Check

```python
# BAD: May allow anonymous users when you don't want them
class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user

permission_classes = [~IsOwner]  # Allows anonymous users!

# GOOD: Combine with authentication
permission_classes = [IsAuthenticated & ~IsOwner]
```

### ❌ Anti-pattern 4: Mixing List AND with Composition

```python
# CONFUSING: Mixing both styles
permission_classes = [
    IsAuthenticated,  # Must pass (list item)
    IsAdminUser | IsOwner  # Either must pass (composed)
]
# Evaluation: IsAuthenticated AND (IsAdminUser OR IsOwner)

# CLEAR: Use consistent style
permission_classes = [
    IsAuthenticated & (IsAdminUser | IsOwner)
]
```

### ❌ Anti-pattern 5: Assuming OR is the Same as List

```python
# WRONG: This is AND, not OR
permission_classes = [IsAdminUser, IsOwner]  # Both must pass!

# CORRECT: Use OR operator
permission_classes = [IsAdminUser | IsOwner]  # Either can pass
```

---

## Real-World Examples

### Example 1: Admin or Owner Can Edit

```python
class IsAdminOrOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or obj.owner == request.user

# Or using composition:
permission_classes = [IsAdminUser | IsOwner]
```

### Example 2: Premium Feature Access

```python
class HasPremiumAccess(BasePermission):
    def has_permission(self, request, view):
        return request.user.subscription_tier in ['premium', 'enterprise']

# Admin OR premium users can access
permission_classes = [IsAdminUser | (IsAuthenticated & HasPremiumAccess)]
```

### Example 3: Read-Only for Public, Write for Authenticated

```python
class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS

# Anyone can read, authenticated can write
permission_classes = [ReadOnly | IsAuthenticated]
```

### Example 4: Department-Based Access

```python
class IsSameDepartment(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.department == obj.department

class IsManager(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'manager'

# Manager OR same department can access
permission_classes = [IsManager | (IsAuthenticated & IsSameDepartment)]
```

### Example 5: Time-Limited Access

```python
from django.utils import timezone

class IsWithinBusinessHours(BasePermission):
    def has_permission(self, request, view):
        now = timezone.now()
        return 9 <= now.hour < 17  # 9 AM to 5 PM

# Admin can access anytime, others only during business hours
permission_classes = [IsAdminUser | (IsAuthenticated & IsWithinBusinessHours)]
```

### Example 6: Graduated Access Levels

```python
class IsPublic(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.visibility == 'public'

class IsTeamMember(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user in obj.team.members.all()

class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user

# Access hierarchy: Public < Team Member < Owner < Admin
permission_classes = [
    IsPublic | IsTeamMember | IsOwner | IsAdminUser
]
```

---

## Testing Composed Permissions

```python
from django.test import TestCase
from rest_framework.test import APIRequestFactory
from rest_framework.permissions import IsAuthenticated, IsAdminUser

class PermissionCompositionTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.admin_user = User.objects.create(username='admin', is_staff=True)
        self.regular_user = User.objects.create(username='user', is_staff=False)

    def test_and_composition(self):
        """Test that & requires both permissions"""
        permission = IsAuthenticated & IsAdminUser
        perm_instance = permission()

        # Admin user - both pass
        request = self.factory.get('/')
        request.user = self.admin_user
        self.assertTrue(perm_instance.has_permission(request, None))

        # Regular user - authenticated but not admin
        request.user = self.regular_user
        self.assertFalse(perm_instance.has_permission(request, None))

    def test_or_composition(self):
        """Test that | requires only one permission"""
        permission = IsAuthenticated | IsAdminUser
        perm_instance = permission()

        # Regular user - authenticated but not admin
        request = self.factory.get('/')
        request.user = self.regular_user
        self.assertTrue(perm_instance.has_permission(request, None))

    def test_not_composition(self):
        """Test that ~ inverts permission"""
        permission = ~IsAuthenticated
        perm_instance = permission()

        # Anonymous user
        from django.contrib.auth.models import AnonymousUser
        request = self.factory.get('/')
        request.user = AnonymousUser()
        self.assertTrue(perm_instance.has_permission(request, None))

        # Authenticated user
        request.user = self.regular_user
        self.assertFalse(perm_instance.has_permission(request, None))
```

---

## Summary

| Operator | Symbol | Behavior | Use Case |
|----------|--------|----------|----------|
| AND | `&` | Both must pass | Multiple required conditions |
| OR | `\|` | Either can pass | Alternative access paths |
| NOT | `~` | Inverts result | Excluding specific users |

**Key Points:**
- Use composition for OR and NOT logic (can't do with permission lists)
- AND can be implicit (list) or explicit (&)
- OR has special object permission handling (re-checks has_permission)
- Use parentheses for complex compositions
- Order matters for performance (short-circuit evaluation)
- Consider custom permission class for very complex logic
