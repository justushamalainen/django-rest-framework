# Creating Custom Permission Classes

Custom permissions allow you to implement complex business logic for access control.

## Table of Contents

- [BasePermission Interface](#basepermission-interface)
- [has_permission vs has_object_permission](#has_permission-vs-has_object_permission)
- [Creating Custom Permissions](#creating-custom-permissions)
- [Accessing Request Context](#accessing-request-context)
- [Custom Error Messages](#custom-error-messages)
- [Reusable Permission Patterns](#reusable-permission-patterns)
- [Testing Custom Permissions](#testing-custom-permissions)

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
- Global access restrictions (e.g., "must be in beta program")
- Rate limiting prerequisites
- Checking if user can access the view at all

**Parameters:**
- `request`: Django Request object with `.user`, `.method`, `.data`, etc.
- `view`: DRF View instance with attributes like `.action`, `.basename`, `.queryset`

**Important:** Does NOT have access to individual objects.

### has_object_permission(self, request, view, obj)

**When Called:** After object retrieval, ONLY for single-object actions (retrieve, update, partial_update, destroy).

**NOT Called For:** list, create actions (no object exists yet).

**Purpose:** Object-level permission checks.

**Use For:**
- Owner checks (`obj.owner == request.user`)
- Object-specific permissions
- Field-level access based on object state
- Per-object access control

**Parameters:**
- `request`: Django Request object
- `view`: DRF View instance
- `obj`: The specific model instance being accessed

**Important:** Only called if `has_permission()` returns `True`.

### Execution Order

```
1. has_permission(request, view)
   ├─ If False → 403 Forbidden (stop here)
   └─ If True → continue

2. [View retrieves object for detail views]

3. has_object_permission(request, view, obj)  [Only for retrieve/update/destroy]
   ├─ If False → 403 Forbidden
   └─ If True → allow access
```

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

**Usage:**
```python
class BetaFeatureViewSet(ModelViewSet):
    permission_classes = [IsBetaUser]
    queryset = Feature.objects.all()
    serializer_class = FeatureSerializer
```

### Pattern 2: Object-Level Permission

```python
class IsOwner(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to access it.
    """
    def has_object_permission(self, request, view, obj):
        # Assumes the model has an 'owner' field
        return obj.owner == request.user
```

**Important:** This ONLY protects retrieve/update/destroy. Add `has_permission()` for list/create:

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
    Allow editing if:
    - User is the author, OR
    - User is a moderator, OR
    - User is an admin
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
        if obj.author == user:
            return True

        return False
```

### Pattern 5: Conditional Logic Based on Object State

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

## Accessing Request Context

### request.user

```python
class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        # Check authentication
        if not request.user or not request.user.is_authenticated:
            return request.method in permissions.SAFE_METHODS

        # Check admin status
        return request.user.is_staff or request.method in permissions.SAFE_METHODS
```

### request.method

```python
class IsAuthenticatedForWrite(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)
```

Available methods: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD`, `OPTIONS`

Safe methods constant: `permissions.SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')`

### request.data

```python
class CanCreateWithCategory(permissions.BasePermission):
    """
    Only allow creating items in allowed categories.
    """
    def has_permission(self, request, view):
        if request.method != 'POST':
            return True

        # Check category in POST data
        category = request.data.get('category')
        return category in request.user.allowed_categories
```

### view.action (ViewSets only)

```python
class ActionBasedPermission(permissions.BasePermission):
    """
    Different permissions based on viewset action.
    """
    def has_permission(self, request, view):
        # Allow anyone to list
        if view.action == 'list':
            return True

        # Require authentication for create
        if view.action == 'create':
            return bool(request.user and request.user.is_authenticated)

        # Require admin for custom actions
        if view.action in ['approve', 'reject']:
            return bool(request.user and request.user.is_staff)

        return True
```

### view.kwargs (URL parameters)

```python
class CanAccessOrganization(permissions.BasePermission):
    """
    User must belong to the organization in the URL.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        org_id = view.kwargs.get('organization_pk')
        return request.user.organization_id == int(org_id)
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

### Method 3: Dynamic Messages

```python
class CanEditUntilPublished(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        if obj.is_published:
            raise PermissionDenied(
                f'This article was published on {obj.published_date} and can no longer be edited.'
            )

        return obj.author == request.user
```

---

## Reusable Permission Patterns

### Pattern: Owner or Staff

```python
class IsOwnerOrStaff(permissions.BasePermission):
    """
    Reusable permission for owner-or-staff access.
    Works with any model that has an 'owner' field.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        # Staff can access anything
        if user.is_staff:
            return True

        # Check ownership (works if obj has 'owner' attribute)
        return obj.owner == user
```

### Pattern: Team Member

```python
class IsTeamMember(permissions.BasePermission):
    """
    Check if user is a member of the object's team.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        # Assumes obj has 'team' with 'members' relationship
        return user in obj.team.members.all()
```

### Pattern: Department Access

```python
class HasDepartmentAccess(permissions.BasePermission):
    """
    User must belong to the same department as the object.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        return user.department == obj.department
```

### Pattern: Time-Based Access

```python
from django.utils import timezone

class IsWithinEditWindow(permissions.BasePermission):
    """
    Allow editing only within 1 hour of creation.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        # Check if within edit window
        time_since_creation = timezone.now() - obj.created_at
        if time_since_creation.total_seconds() > 3600:  # 1 hour
            return False

        # Must also be the owner
        return obj.owner == request.user
```

### Pattern: IP Whitelist

```python
class IsFromAllowedIP(permissions.BasePermission):
    """
    Allow access only from whitelisted IP addresses.
    """
    allowed_ips = ['192.168.1.1', '10.0.0.1']

    def has_permission(self, request, view):
        ip_addr = request.META.get('REMOTE_ADDR')
        return ip_addr in self.allowed_ips
```

---

## Testing Custom Permissions

### Unit Test Example

```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from myapp.permissions import IsOwner
from myapp.models import Article

User = get_user_model()

class IsOwnerPermissionTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = IsOwner()
        self.user1 = User.objects.create_user('user1', password='pass')
        self.user2 = User.objects.create_user('user2', password='pass')
        self.article = Article.objects.create(
            title='Test',
            owner=self.user1
        )

    def test_owner_has_permission(self):
        """Owner should have permission"""
        request = self.factory.get('/')
        request.user = self.user1

        has_perm = self.permission.has_object_permission(
            request, None, self.article
        )
        self.assertTrue(has_perm)

    def test_non_owner_denied(self):
        """Non-owner should be denied"""
        request = self.factory.get('/')
        request.user = self.user2

        has_perm = self.permission.has_object_permission(
            request, None, self.article
        )
        self.assertFalse(has_perm)

    def test_anonymous_user_denied(self):
        """Anonymous user should be denied"""
        from django.contrib.auth.models import AnonymousUser
        request = self.factory.get('/')
        request.user = AnonymousUser()

        has_perm = self.permission.has_object_permission(
            request, None, self.article
        )
        self.assertFalse(has_perm)
```

### Integration Test Example

```python
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

User = get_user_model()

class ArticlePermissionIntegrationTest(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user('user1', password='pass')
        self.user2 = User.objects.create_user('user2', password='pass')
        self.article = Article.objects.create(title='Test', owner=self.user1)

    def test_owner_can_update(self):
        """Owner should be able to update their article"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.patch(
            f'/api/articles/{self.article.pk}/',
            {'title': 'Updated'}
        )
        self.assertEqual(response.status_code, 200)

    def test_non_owner_cannot_update(self):
        """Non-owner should not be able to update article"""
        self.client.force_authenticate(user=self.user2)
        response = self.client.patch(
            f'/api/articles/{self.article.pk}/',
            {'title': 'Updated'}
        )
        self.assertEqual(response.status_code, 403)

    def test_anonymous_cannot_update(self):
        """Anonymous user should not be able to update"""
        response = self.client.patch(
            f'/api/articles/{self.article.pk}/',
            {'title': 'Updated'}
        )
        self.assertEqual(response.status_code, 403)
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

### 5. Avoid Expensive Queries

```python
# BAD - Complex query in has_permission (runs for every request)
def has_permission(self, request, view):
    return Article.objects.filter(
        owner=request.user,
        status='published'
    ).count() > 5

# GOOD - Cache on user model or use lightweight check
def has_permission(self, request, view):
    return request.user.has_published_minimum  # Cached property
```
