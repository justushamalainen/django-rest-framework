---
description: Implementing permission and access control in Django REST Framework. Use when restricting API access, creating custom permission classes, implementing object-level permissions, or combining permission logic. Covers built-in permissions, custom permissions, permission composition (AND/OR/NOT operators), and object-level permissions with django-guardian integration.
---

# DRF Permissions

Implementing robust access control in Django REST Framework APIs.

## What You'll Learn

- **Built-in Permission Classes** - IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly, DjangoModelPermissions, and when to use each
- **Custom Permission Classes** - Creating custom permission logic with has_permission() and has_object_permission()
- **Permission Composition** - Combining permissions using AND (&), OR (|), and NOT (~) operators with proper precedence handling
- **Object-Level Permissions** - Restricting access to individual objects, integration with django-guardian
- **Common Patterns** - Owner-only access, role-based permissions, conditional permissions
- **Anti-patterns** - Mistakes that compromise security or cause performance issues

## Quick Start

### Basic Authentication-Only API

```python
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

class ArticleViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
```

**Effect:** Only authenticated users can access ANY endpoint (list, create, retrieve, update, delete).

### Read-Only Public, Write Requires Auth

```python
from rest_framework.permissions import IsAuthenticatedOrReadOnly

class ArticleViewSet(ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
```

**Effect:** Anyone can GET/HEAD/OPTIONS. POST/PUT/PATCH/DELETE require authentication.

### Owner-Only Access

```python
from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners to edit.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for owner
        return obj.owner == request.user

class ArticleViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
```

## Permission Decision Tree

### Choose Your Permission Strategy

```
START: What access control do you need?

├─ Allow everyone?
│  └─ AllowAny (or omit permission_classes)
│
├─ Only authenticated users?
│  └─ IsAuthenticated
│
├─ Public read, authenticated write?
│  └─ IsAuthenticatedOrReadOnly
│
├─ Only admin users (is_staff=True)?
│  └─ IsAdminUser
│
├─ Django model permissions (add/change/delete)?
│  ├─ Authenticated users only → DjangoModelPermissions
│  └─ Allow anonymous read → DjangoModelPermissionsOrAnonReadOnly
│
├─ Object-level permissions with django-guardian?
│  └─ DjangoObjectPermissions
│
├─ Custom business logic?
│  ├─ View-level check → Override has_permission()
│  ├─ Object-level check → Override has_object_permission()
│  └─ Both → Override both methods
│
└─ Multiple permission requirements?
   ├─ ALL must pass → Use & (AND)
   ├─ ANY can pass → Use | (OR)
   └─ Negate permission → Use ~ (NOT)
```

## How Permissions Work

### Execution Flow

1. **View-Level Check** (`has_permission`)
   - Called BEFORE any database queries
   - Checks request, view, but NOT individual objects
   - Use for: Authentication checks, global view access, rate limiting prerequisites

2. **Object-Level Check** (`has_object_permission`)
   - Called AFTER object retrieval (retrieve, update, destroy actions)
   - NOT called for list or create actions
   - Use for: Owner checks, object-specific permissions, field-level access

### Multiple Permissions

When you specify multiple permission classes:

```python
permission_classes = [IsAuthenticated, IsAdminUser]
```

**ALL must pass** (implicit AND). If ANY returns False, access is denied with 403 Forbidden.

## Common Use Cases

### 1. Public Read, Owner Write

```python
class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.owner == request.user
```

### 2. Admin or Owner Can Edit

```python
class IsAdminOrOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or obj.owner == request.user
```

### 3. Different Permissions Per Action

```python
class ArticleViewSet(ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    def get_permissions(self):
        """
        Instantiate and return the list of permissions for this view.
        """
        if self.action == 'list':
            permission_classes = [AllowAny]
        elif self.action == 'create':
            permission_classes = [IsAuthenticated]
        else:  # retrieve, update, partial_update, destroy
            permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
        return [permission() for permission in permission_classes]
```

### 4. Role-Based Access

```python
class IsManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'manager'

class IsSalesOrManager(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.role in ['sales', 'manager']
```

## Permission Composition

**CRITICAL:** DRF supports composing permissions with Python operators.

### AND Operator (&)

Both permissions MUST pass:

```python
from rest_framework.permissions import IsAuthenticated, IsAdminUser

# Using & operator
permission_classes = [IsAuthenticated & IsAdminUser]

# Equivalent to:
permission_classes = [IsAuthenticated, IsAdminUser]
```

### OR Operator (|)

Either permission can pass:

```python
from rest_framework.permissions import IsAuthenticated, IsAdminUser

# Admin OR authenticated user can access
permission_classes = [IsAuthenticated | IsAdminUser]  # IsAdminUser alone would be sufficient

# Better example: Admin OR owner
permission_classes = [IsAdminUser | IsOwner]
```

### NOT Operator (~)

Inverts the permission:

```python
from rest_framework.permissions import IsAuthenticated

# Only UNauthenticated users (for public-only endpoints)
permission_classes = [~IsAuthenticated]
```

### Complex Compositions

```python
# (Admin OR Owner) AND IsAuthenticated
permission_classes = [(IsAdminUser | IsOwner) & IsAuthenticated]

# Admin OR (Authenticated AND HasSubscription)
permission_classes = [IsAdminUser | (IsAuthenticated & HasSubscription)]
```

**See [reference/permission-composition.md](reference/permission-composition.md) for precedence rules, edge cases, and anti-patterns.**

## Common Mistakes

### ❌ Mistake 1: Using has_object_permission for List/Create

```python
# WRONG: has_object_permission is NOT called for list() or create()
class BadPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user  # Won't protect list/create!

# CORRECT: Use has_permission for view-level checks
class GoodPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        # Check if user can access the view at all
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Check if user can access THIS specific object
        return obj.owner == request.user
```

### ❌ Mistake 2: Forgetting to Check Authentication

```python
# WRONG: Will crash if user is anonymous
class BadPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_staff  # AttributeError if AnonymousUser

# CORRECT: Always check authentication first
class GoodPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)
```

### ❌ Mistake 3: Expensive Queries in has_permission

```python
# WRONG: Runs complex query for EVERY request
class BadPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        # This runs BEFORE retrieving the actual object!
        return Article.objects.filter(owner=request.user).count() > 0

# CORRECT: Keep has_permission lightweight
class GoodPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Object-specific checks here
        return obj.owner == request.user
```

### ❌ Mistake 4: Returning None Instead of Boolean

```python
# WRONG: Returning None is treated as False
class BadPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.is_staff:
            return True
        # Implicitly returns None if not staff!

# CORRECT: Always explicitly return True or False
class GoodPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)
```

### ❌ Mistake 5: Confusing & with Multiple Classes

```python
# These are DIFFERENT:

# Option 1: Two separate permission instances (BOTH must pass)
permission_classes = [IsAuthenticated, IsAdminUser]

# Option 2: Single composed permission instance (BOTH must pass)
permission_classes = [IsAuthenticated & IsAdminUser]

# They work the same for AND, but composition is needed for OR/NOT
permission_classes = [IsAuthenticated | IsAdminUser]  # Correct
# permission_classes = [IsAuthenticated, IsAdminUser]  # Wrong for OR logic
```

## Reference Files

### Built-in Permissions
**[reference/builtin-permissions.md](reference/builtin-permissions.md)**
- AllowAny
- IsAuthenticated
- IsAdminUser
- IsAuthenticatedOrReadOnly
- DjangoModelPermissions
- DjangoModelPermissionsOrAnonReadOnly
- DjangoObjectPermissions

### Custom Permissions
**[reference/custom-permissions.md](reference/custom-permissions.md)**
- Creating custom permission classes
- has_permission() vs has_object_permission()
- Accessing request, view, and obj
- Custom error messages
- Reusable permission patterns

### Permission Composition (FREQUENTLY ASKED)
**[reference/permission-composition.md](reference/permission-composition.md)**
- AND (&), OR (|), NOT (~) operators
- Operator precedence and evaluation order
- Edge cases and gotchas
- Performance considerations
- Anti-patterns and security issues

### Object-Level Permissions
**[reference/object-permissions.md](reference/object-permissions.md)**
- Object-level permission checks
- Integration with django-guardian
- Per-object permission assignment
- Filtering querysets by permissions
- Performance optimization

### Working Examples
**[reference/examples/permission-patterns.py](reference/examples/permission-patterns.py)**
- Complete working code examples
- Owner-only access patterns
- Role-based permissions
- Composed permission examples
- Time-based permissions
- IP-based restrictions
