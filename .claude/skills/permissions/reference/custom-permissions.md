# Creating Custom Permission Classes

Custom permissions allow you to implement complex business logic for access control.

## Table of Contents

- [BasePermission Interface](#basepermission-interface)
- [has_permission vs has_object_permission](#has_permission-vs-has_object_permission)
- [Creating Custom Permissions](#creating-custom-permissions)
- [Custom Error Messages](#custom-error-messages)
- [Best Practices](#best-practices)

---

## BasePermission Interface

All permission classes inherit from `BasePermission`:

```python
from rest_framework.permissions import BasePermission

class BasePermission(metaclass=BasePermissionMetaclass):
    """
    A base class from which all permission classes should inherit.
    """

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return True

    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return True
```

**Default behavior:** Both methods return `True` (allow access).

---

## has_permission vs has_object_permission

### has_permission(self, request, view)

**When Called:** Before the view handler executes, for ALL actions (list, create, retrieve, update, destroy).

**Purpose:** View-level permission checks.

**Use For:**
- Authentication checks
- Global access restrictions
- Checking if user can access the view at all

**Parameters:**
- `request`: Django Request object with `.user`, `.method`, `.data`, etc.
- `view`: DRF View instance with attributes like `.action`, `.basename`, `.queryset`

### has_object_permission(self, request, view, obj)

**When Called:** After object retrieval, ONLY for single-object actions (retrieve, update, partial_update, destroy).

**NOT Called For:** list, create actions (no object exists yet).

**Purpose:** Object-level permission checks.

**Use For:**
- Owner checks (`obj.owner == request.user`)
- Object-specific permissions
- Per-object access control

**Parameters:**
- `request`: Django Request object
- `view`: DRF View instance
- `obj`: The specific model instance being accessed

**Important:** Only called if `has_permission()` returns `True`.

---

## Creating Custom Permissions

### Pattern 1: Simple View-Level Permission

```python
from rest_framework import permissions

class IsBetaUser(permissions.BasePermission):
    """
    Allow access only to users in the beta program.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_beta_user
        )
```

### Pattern 2: Object-Level Permission

```python
class IsOwner(permissions.BasePermission):
    """
    Only allow owners to access objects.
    """
    def has_permission(self, request, view):
        # Must be authenticated to proceed
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Owner check
        return obj.owner == request.user
```

### Pattern 3: Read/Write Permission Split

```python
class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Allow anyone to read, but only owners can edit.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for owner
        return obj.owner == request.user
```

### Pattern 4: Multiple Conditions

```python
class CanEditPost(permissions.BasePermission):
    """
    Allow editing if user is author, moderator, or admin.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user

        # Must be authenticated
        if not user or not user.is_authenticated:
            return False

        # Admin can do anything
        if user.is_staff:
            return True

        # Moderators can edit
        if hasattr(user, 'role') and user.role == 'moderator':
            return True

        # Authors can edit their own posts
        return obj.author == user
```

### Pattern 5: State-Based Permissions

```python
class CanEditDraft(permissions.BasePermission):
    """
    Allow editing only if the article is still in draft status.
    """
    def has_object_permission(self, request, view, obj):
        # Allow GET requests for any status
        if request.method in permissions.SAFE_METHODS:
            return True

        # Only allow editing drafts
        if obj.status != 'draft':
            return False

        # Must be the owner
        return obj.owner == request.user
```

---

## Custom Error Messages

### Method 1: message Attribute

```python
class IsPremiumUser(permissions.BasePermission):
    message = 'You must have a premium subscription to access this resource.'

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_premium
        )
```

**Response:**
```json
{
    "detail": "You must have a premium subscription to access this resource."
}
```

### Method 2: Raising PermissionDenied

```python
from rest_framework.exceptions import PermissionDenied

class HasSubscription(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            raise PermissionDenied('Authentication required.')

        if not request.user.subscription_active:
            raise PermissionDenied(
                'Your subscription has expired. Please renew to continue.'
            )

        return True
```

---

## Best Practices

### 1. Always Check Authentication First

```python
# GOOD
def has_permission(self, request, view):
    if not request.user or not request.user.is_authenticated:
        return False
    return request.user.is_premium

# BAD (will crash for anonymous users)
def has_permission(self, request, view):
    return request.user.is_premium  # AttributeError if AnonymousUser
```

### 2. Use Explicit Boolean Returns

```python
# GOOD
def has_permission(self, request, view):
    return bool(request.user and request.user.is_authenticated)

# BAD (implicit None return if condition not met)
def has_permission(self, request, view):
    if request.user.is_authenticated:
        return True
    # Returns None here!
```

### 3. Combine with has_permission for Complete Protection

```python
# GOOD - Protects both list and object access
class IsOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user

# BAD - Only protects object access (list is unprotected)
class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user
```

### 4. Use Safe Methods Constant

```python
from rest_framework import permissions

# GOOD
if request.method in permissions.SAFE_METHODS:
    return True

# BAD (fragile, might miss methods)
if request.method == 'GET':
    return True
```

### 5. Filter Querysets for List Actions

Object permissions are NOT checked for list actions. Always filter in `get_queryset()`:

```python
class ArticleViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    serializer_class = ArticleSerializer

    def get_queryset(self):
        # Filter to only show user's own articles
        return Article.objects.filter(owner=self.request.user)
```
