---
description: Implementing permission and access control in Django REST Framework. Use when restricting API access, creating custom permission classes, implementing object-level permissions, or combining permission logic. Covers built-in permissions, custom permissions, permission composition (AND/OR/NOT operators), and object-level permissions with django-guardian integration.
---

# DRF Permissions

Implementing robust access control in Django REST Framework APIs.

## What You'll Learn

- **Built-in Permission Classes** - IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly
- **Custom Permission Classes** - Creating custom permission logic with has_permission() and has_object_permission()
- **Permission Composition** - Combining permissions using AND (&) and OR (|) operators
- **Common Patterns** - Owner-only access, role-based permissions, conditional permissions

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
└─ Custom business logic?
   ├─ View-level check → Override has_permission()
   ├─ Object-level check → Override has_object_permission()
   └─ Both → Override both methods
```

## Built-in Permission Classes

### IsAuthenticated

**Purpose:** Allow access only to authenticated users.

```python
from rest_framework.permissions import IsAuthenticated

class ProfileViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = UserProfile.objects.all()
    serializer_class = ProfileSerializer
```

**When to Use:**
- User-specific data (profiles, orders, private content)
- Any endpoint that requires knowing who the user is
- Most authenticated APIs use this as a base permission

**Response:**
- **Authenticated:** 200 OK (if other checks pass)
- **Anonymous:** 403 Forbidden

### IsAdminUser

**Purpose:** Allow access only to admin users (staff members).

```python
from rest_framework.permissions import IsAdminUser

class AdminReportViewSet(ModelViewSet):
    permission_classes = [IsAdminUser]
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
```

**When to Use:**
- Admin-only endpoints (reports, system configuration, user management)
- Endpoints that modify system-wide settings
- Dangerous operations that should be restricted to staff

**Notes:**
- Checks `request.user.is_staff`, NOT `is_superuser`
- Implicitly requires authentication

### IsAuthenticatedOrReadOnly

**Purpose:** Allow authenticated users full access, everyone else read-only.

```python
from rest_framework.permissions import IsAuthenticatedOrReadOnly

class BlogPostViewSet(ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializer
```

**Behavior:**

| Method | Anonymous | Authenticated |
|--------|-----------|---------------|
| GET    | ✅ Allowed | ✅ Allowed |
| POST   | ❌ Forbidden | ✅ Allowed |
| PUT    | ❌ Forbidden | ✅ Allowed |
| DELETE | ❌ Forbidden | ✅ Allowed |

**When to Use:**
- Public content that anyone can view but only authenticated users can modify
- Blog posts, articles, comments (public read, auth write)

## How Permissions Work

### Execution Flow

1. **View-Level Check** (`has_permission`)
   - Called BEFORE any database queries
   - Checks request, view, but NOT individual objects
   - Use for: Authentication checks, global view access

2. **Object-Level Check** (`has_object_permission`)
   - Called AFTER object retrieval (retrieve, update, destroy actions)
   - NOT called for list or create actions
   - Use for: Owner checks, object-specific permissions

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
        if self.action == 'list':
            permission_classes = [AllowAny]
        elif self.action == 'create':
            permission_classes = [IsAuthenticated]
        else:  # retrieve, update, partial_update, destroy
            permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
        return [permission() for permission in permission_classes]
```

## Permission Composition

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
# Admin OR owner can access
permission_classes = [IsAdminUser | IsOwner]
```

**See [reference/permission-composition.md](reference/permission-composition.md) for more details.**

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
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
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

### ❌ Mistake 3: Returning None Instead of Boolean

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

## Reference Files

### Custom Permissions
**[reference/custom-permissions.md](reference/custom-permissions.md)**
- Creating custom permission classes
- has_permission() vs has_object_permission()
- Accessing request, view, and obj
- Custom error messages
- Reusable permission patterns

### Permission Composition
**[reference/permission-composition.md](reference/permission-composition.md)**
- AND (&) and OR (|) operators
- Operator precedence and evaluation order
- Real-world examples
