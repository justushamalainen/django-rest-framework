# Built-in Permission Classes

DRF provides several built-in permission classes for common access control scenarios.

## Table of Contents

- [AllowAny](#allowany)
- [IsAuthenticated](#isauthenticated)
- [IsAdminUser](#isadminuser)
- [IsAuthenticatedOrReadOnly](#isauthenticatedorreadonly)
- [DjangoModelPermissions](#djangomodelpermissions)
- [DjangoModelPermissionsOrAnonReadOnly](#djangomodelpermissionsornreadonlyanon)
- [DjangoObjectPermissions](#djangoobjectpermissions)
- [Comparison Table](#comparison-table)

---

## AllowAny

**Purpose:** Explicitly allow unrestricted access.

### Implementation

```python
class AllowAny(BasePermission):
    """
    Allow any access.
    This isn't strictly required, since you could use an empty
    permission_classes list, but it's useful because it makes the intention
    more explicit.
    """
    def has_permission(self, request, view):
        return True
```

### Usage

```python
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ModelViewSet

class PublicArticleViewSet(ModelViewSet):
    permission_classes = [AllowAny]
    queryset = Article.objects.filter(published=True)
    serializer_class = ArticleSerializer
```

### When to Use

- Public API endpoints that anyone can access
- Making permission requirements explicit in code
- Overriding default permission classes for specific actions

### Notes

- This is the default behavior if `permission_classes` is empty
- Use it for clarity and explicit intent
- Still subject to throttling and other middleware

---

## IsAuthenticated

**Purpose:** Allow access only to authenticated users.

### Implementation

```python
class IsAuthenticated(BasePermission):
    """
    Allows access only to authenticated users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)
```

### Usage

```python
from rest_framework.permissions import IsAuthenticated

class ProfileViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = UserProfile.objects.all()
    serializer_class = ProfileSerializer
```

### When to Use

- User-specific data (profiles, orders, private content)
- Any endpoint that requires knowing who the user is
- Most authenticated APIs use this as a base permission

### Response

- **Authenticated:** 200 OK (if other checks pass)
- **Anonymous:** 403 Forbidden with detail: "Authentication credentials were not provided."

### Notes

- Checks `request.user.is_authenticated` property
- Works with any authentication backend (Token, Session, JWT, etc.)
- Does NOT check for specific user attributes (like is_staff)

---

## IsAdminUser

**Purpose:** Allow access only to admin users (staff members).

### Implementation

```python
class IsAdminUser(BasePermission):
    """
    Allows access only to admin users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)
```

### Usage

```python
from rest_framework.permissions import IsAdminUser

class AdminReportViewSet(ModelViewSet):
    permission_classes = [IsAdminUser]
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
```

### When to Use

- Admin-only endpoints (reports, system configuration, user management)
- Endpoints that modify system-wide settings
- Dangerous operations that should be restricted to staff

### Response

- **Admin user (is_staff=True):** 200 OK
- **Regular user or anonymous:** 403 Forbidden

### Notes

- Checks `request.user.is_staff`, NOT `is_superuser`
- Anonymous users also get 403 (not 401)
- Implicitly requires authentication (is_staff assumes authenticated user)

---

## IsAuthenticatedOrReadOnly

**Purpose:** Allow authenticated users full access, everyone else read-only.

### Implementation

```python
SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')

class IsAuthenticatedOrReadOnly(BasePermission):
    """
    The request is authenticated as a user, or is a read-only request.
    """
    def has_permission(self, request, view):
        return bool(
            request.method in SAFE_METHODS or
            request.user and
            request.user.is_authenticated
        )
```

### Usage

```python
from rest_framework.permissions import IsAuthenticatedOrReadOnly

class BlogPostViewSet(ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializer
```

### When to Use

- Public content that anyone can view but only authenticated users can modify
- Blog posts, articles, comments (public read, auth write)
- Community content platforms

### Behavior

| Method | Anonymous | Authenticated |
|--------|-----------|---------------|
| GET    | ✅ Allowed | ✅ Allowed |
| POST   | ❌ Forbidden | ✅ Allowed |
| PUT    | ❌ Forbidden | ✅ Allowed |
| PATCH  | ❌ Forbidden | ✅ Allowed |
| DELETE | ❌ Forbidden | ✅ Allowed |

### Notes

- "Safe methods" are GET, HEAD, OPTIONS (read-only operations)
- Often combined with object-level permissions for owner-only edits
- Does NOT restrict which authenticated users can write

---

## DjangoModelPermissions

**Purpose:** Tie API access to Django's built-in permission system.

### Implementation

```python
class DjangoModelPermissions(BasePermission):
    """
    The request is authenticated using `django.contrib.auth` permissions.

    It ensures that the user is authenticated, and has the appropriate
    `add`/`change`/`delete` permissions on the model.
    """
    perms_map = {
        'GET': [],
        'OPTIONS': [],
        'HEAD': [],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }

    authenticated_users_only = True
```

### Usage

```python
from rest_framework.permissions import DjangoModelPermissions

class ArticleViewSet(ModelViewSet):
    permission_classes = [DjangoModelPermissions]
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
```

### Permission Mapping

| HTTP Method | Required Permission |
|-------------|-------------------|
| GET, HEAD, OPTIONS | None (but must be authenticated) |
| POST | `app_label.add_model_name` |
| PUT, PATCH | `app_label.change_model_name` |
| DELETE | `app_label.delete_model_name` |

### When to Use

- Leveraging existing Django permission system
- Fine-grained permission management through Django admin
- Integration with Django's permission groups
- Delegating permission management to non-developers

### Customizing Permission Map

```python
class CustomDjangoModelPermissions(DjangoModelPermissions):
    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s'],  # Add view permission
        'OPTIONS': [],
        'HEAD': [],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }
```

### Requirements

- View must have `.queryset` attribute or `.get_queryset()` method
- User must be authenticated (`authenticated_users_only = True`)
- Permissions must be assigned via Django admin or code

### Notes

- By default, GET does NOT require view permission (only authentication)
- Override `perms_map` to add view permission for GET requests
- Works with Django's `User.user_permissions` and `Group.permissions`

---

## DjangoModelPermissionsOrAnonReadOnly

**Purpose:** DjangoModelPermissions but allow anonymous users read access.

### Implementation

```python
class DjangoModelPermissionsOrAnonReadOnly(DjangoModelPermissions):
    """
    Similar to DjangoModelPermissions, except that anonymous users are
    allowed read-only access.
    """
    authenticated_users_only = False
```

### Usage

```python
from rest_framework.permissions import DjangoModelPermissionsOrAnonReadOnly

class ArticleViewSet(ModelViewSet):
    permission_classes = [DjangoModelPermissionsOrAnonReadOnly]
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
```

### Behavior Difference

| Action | Anonymous | Authenticated (no perms) | Authenticated (with perms) |
|--------|-----------|-------------------------|---------------------------|
| GET    | ✅ Allowed | ✅ Allowed | ✅ Allowed |
| POST   | ❌ Forbidden | ❌ Forbidden | ✅ Allowed (if has add permission) |
| PUT/PATCH | ❌ Forbidden | ❌ Forbidden | ✅ Allowed (if has change permission) |
| DELETE | ❌ Forbidden | ❌ Forbidden | ✅ Allowed (if has delete permission) |

### When to Use

- Public APIs with read-only access for everyone
- Write operations require specific Django permissions
- Community platforms with user-generated content

---

## DjangoObjectPermissions

**Purpose:** Object-level permissions using Django's permission backends (like django-guardian).

### Implementation

```python
class DjangoObjectPermissions(DjangoModelPermissions):
    """
    The request is authenticated using Django's object-level permissions.
    It requires an object-permissions-enabled backend, such as Django Guardian.
    """
    perms_map = {
        'GET': [],
        'OPTIONS': [],
        'HEAD': [],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }

    def has_object_permission(self, request, view, obj):
        # Check if user has object-level permissions
        queryset = self._queryset(view)
        model_cls = queryset.model
        user = request.user

        perms = self.get_required_object_permissions(request.method, model_cls)

        if not user.has_perms(perms, obj):
            # Return 404 instead of 403 for objects user can't read
            if request.method in SAFE_METHODS:
                raise Http404

            read_perms = self.get_required_object_permissions('GET', model_cls)
            if not user.has_perms(read_perms, obj):
                raise Http404

            return False

        return True
```

### Requirements

**Install django-guardian:**

```bash
pip install django-guardian
```

**Configure settings.py:**

```python
INSTALLED_APPS = [
    # ...
    'guardian',
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',  # Default
    'guardian.backends.ObjectPermissionBackend',   # Object permissions
]
```

### Usage

```python
from rest_framework.permissions import DjangoObjectPermissions
from guardian.shortcuts import assign_perm

class DocumentViewSet(ModelViewSet):
    permission_classes = [DjangoObjectPermissions]
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer

    def perform_create(self, serializer):
        obj = serializer.save(owner=self.request.user)
        # Grant creator full permissions
        assign_perm('myapp.change_document', self.request.user, obj)
        assign_perm('myapp.delete_document', self.request.user, obj)
```

### When to Use

- Per-object access control (not all users can access all objects)
- Shared documents with different access levels
- Multi-tenant applications
- Fine-grained access control requirements

### Customizing GET Permissions

```python
class CustomObjectPermissions(DjangoObjectPermissions):
    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s'],  # Require view permission
        'OPTIONS': [],
        'HEAD': ['%(app_label)s.view_%(model_name)s'],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }
```

### 404 vs 403 Behavior

DjangoObjectPermissions returns **404 Not Found** instead of 403 Forbidden when:
- User doesn't have read permissions on the object
- This prevents leaking information about object existence

Returns **403 Forbidden** when:
- User can read the object but can't perform the requested operation

### Notes

- Requires object-permission backend (e.g., django-guardian)
- Only applies to retrieve/update/destroy actions (not list/create)
- Use `get_queryset()` to filter visible objects for list action
- See [object-permissions.md](object-permissions.md) for detailed guide

---

## Comparison Table

| Permission Class | Anonymous | Auth Required | Model Perms | Object Perms | Use Case |
|-----------------|-----------|---------------|-------------|--------------|----------|
| AllowAny | ✅ Full | No | No | No | Public APIs |
| IsAuthenticated | ❌ Forbidden | Yes | No | No | User-specific data |
| IsAdminUser | ❌ Forbidden | Yes (staff) | No | No | Admin-only endpoints |
| IsAuthenticatedOrReadOnly | ✅ Read-only | Yes (for write) | No | No | Public read, auth write |
| DjangoModelPermissions | ❌ Forbidden | Yes | Yes | No | Django permission integration |
| DjangoModelPermissionsOrAnonReadOnly | ✅ Read-only | Yes (for write) | Yes | No | Public read + Django perms |
| DjangoObjectPermissions | ❌ Forbidden | Yes | Yes | Yes | Per-object access control |

---

## Default Permission Policy

Set project-wide default permissions in settings.py:

```python
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ]
}
```

Override in views:

```python
class PublicViewSet(ModelViewSet):
    permission_classes = []  # Override default to allow anyone
    # or
    permission_classes = [AllowAny]  # Explicit override
```

---

## Combining Built-in Permissions

```python
# Multiple permissions (all must pass)
permission_classes = [IsAuthenticated, IsAdminUser]

# Composition with operators
permission_classes = [IsAuthenticated | IsAdminUser]  # Either can access

# Complex logic
from rest_framework.permissions import IsAdminUser, IsAuthenticated

class CanAccessReports(BasePermission):
    def has_permission(self, request, view):
        return request.user.department == 'finance'

# Admin OR (authenticated AND finance department)
permission_classes = [IsAdminUser | (IsAuthenticated & CanAccessReports)]
```
