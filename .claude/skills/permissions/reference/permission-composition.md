# Permission Composition (AND, OR)

DRF allows composing permissions using Python operators: `&` (AND) and `|` (OR).

## Quick Reference

```python
from rest_framework.permissions import IsAuthenticated, IsAdminUser

# AND: Both must pass
permission_classes = [IsAuthenticated & IsAdminUser]
# Equivalent to:
permission_classes = [IsAuthenticated, IsAdminUser]

# OR: Either can pass
permission_classes = [IsAuthenticated | IsAdminUser]

# Complex: (Admin OR Owner) AND Authenticated
permission_classes = [(IsAdminUser | IsOwner) & IsAuthenticated]
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
```

---

## Operator Precedence

Python's operator precedence applies (AND has higher precedence than OR):

### Examples

```python
# Expression: A | B & C
# Evaluates as: A | (B & C)
IsAdminUser | IsAuthenticated & HasSubscription
# = IsAdminUser | (IsAuthenticated & HasSubscription)
```

### Use Parentheses for Clarity

**Always use parentheses** for complex expressions:

```python
# AMBIGUOUS (relies on precedence rules)
permission_classes = [IsAdminUser | IsAuthenticated & HasSubscription]

# CLEAR (explicit grouping)
permission_classes = [IsAdminUser | (IsAuthenticated & HasSubscription)]
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

---

## Common Patterns

### Multiple Permissions List vs Composition

```python
# These are DIFFERENT:

# Option A: List of permission instances (all must pass)
permission_classes = [IsAuthenticated, IsAdminUser]
# Both IsAuthenticated AND IsAdminUser must pass

# Option B: Single composed OR (either can pass)
permission_classes = [IsAuthenticated | IsAdminUser]  # OR
```

### Performance Tip

Order matters for OR - check cheapest permission first:

```python
# GOOD: Check cheapest permission first
permission_classes = [IsAdminUser | ExpensivePermissionCheck]

# BAD: Expensive check runs first
permission_classes = [ExpensivePermissionCheck | IsAdminUser]
```

**Reasoning:** If the first operand passes, the second is never evaluated (short-circuit).
