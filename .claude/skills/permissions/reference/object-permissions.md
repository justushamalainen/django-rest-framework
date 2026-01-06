# Object-Level Permissions

Object-level permissions allow you to control access to individual model instances, not just views.

## Table of Contents

- [Overview](#overview)
- [has_object_permission Basics](#has_object_permission-basics)
- [Django Guardian Integration](#django-guardian-integration)
- [Filtering Querysets by Permissions](#filtering-querysets-by-permissions)
- [Common Patterns](#common-patterns)
- [Performance Optimization](#performance-optimization)
- [Troubleshooting](#troubleshooting)

---

## Overview

### View-Level vs Object-Level

**View-Level (`has_permission`):**
- Checks if user can access the view at all
- Called for ALL actions (list, create, retrieve, update, destroy)
- No access to individual objects

**Object-Level (`has_object_permission`):**
- Checks if user can access a SPECIFIC object
- Called ONLY for detail views (retrieve, update, partial_update, destroy)
- NOT called for list or create actions
- Receives the object as a parameter

### When Object Permissions are Checked

| Action | View-Level | Object-Level |
|--------|------------|--------------|
| list   | ✅ Checked | ❌ NOT checked |
| create | ✅ Checked | ❌ NOT checked |
| retrieve | ✅ Checked | ✅ Checked |
| update | ✅ Checked | ✅ Checked |
| partial_update | ✅ Checked | ✅ Checked |
| destroy | ✅ Checked | ✅ Checked |

---

## has_object_permission Basics

### Simple Owner Check

```python
from rest_framework import permissions

class IsOwner(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to view/edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Assumes the model has an 'owner' attribute
        return obj.owner == request.user
```

**Important:** This ONLY protects retrieve/update/destroy actions. List and create are unprotected!

### Complete Owner Permission

```python
class IsOwner(permissions.BasePermission):
    """
    Complete owner-based permission.
    """
    def has_permission(self, request, view):
        # View-level: User must be authenticated
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Object-level: User must be the owner
        return obj.owner == request.user
```

### Read-Only for All, Write for Owner

```python
class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Allow anyone to read, but only owners can edit.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for owner
        return obj.owner == request.user
```

### Accessing Nested Attributes

```python
class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Allow anyone to read, but only the article author can edit.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        # Article has a foreign key to author (User model)
        return obj.article.author == request.user
```

### Multiple Object Attributes

```python
class IsOwnerOrCollaborator(permissions.BasePermission):
    """
    Allow owners and collaborators to access.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        # Check if user is owner
        if obj.owner == user:
            return True

        # Check if user is in collaborators (ManyToMany field)
        return user in obj.collaborators.all()
```

---

## Django Guardian Integration

[Django Guardian](https://django-guardian.readthedocs.io/) provides per-object permissions for Django.

### Installation

```bash
pip install django-guardian
```

### Configuration

**settings.py:**
```python
INSTALLED_APPS = [
    # ...
    'guardian',
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',  # Default backend
    'guardian.backends.ObjectPermissionBackend',   # Guardian's backend
]
```

**Run migrations:**
```bash
python manage.py migrate guardian
```

### Model Setup

**models.py:**
```python
from django.db import models
from django.contrib.auth.models import User

class Document(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [
            ('view_document', 'Can view document'),
        ]
```

### Assigning Permissions

```python
from guardian.shortcuts import assign_perm, remove_perm
from myapp.models import Document

# Create document
document = Document.objects.create(title='Secret Doc', owner=user1)

# Grant permissions to specific user
assign_perm('myapp.view_document', user2, document)
assign_perm('myapp.change_document', user2, document)

# Remove permissions
remove_perm('myapp.view_document', user2, document)

# Assign to group
from django.contrib.auth.models import Group
editors = Group.objects.get(name='Editors')
assign_perm('myapp.change_document', editors, document)
```

### Using DjangoObjectPermissions

```python
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.viewsets import ModelViewSet
from guardian.shortcuts import assign_perm

class DocumentViewSet(ModelViewSet):
    permission_classes = [DjangoObjectPermissions]
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer

    def perform_create(self, serializer):
        # Save with current user as owner
        obj = serializer.save(owner=self.request.user)

        # Automatically grant creator full permissions
        assign_perm('myapp.view_document', self.request.user, obj)
        assign_perm('myapp.change_document', self.request.user, obj)
        assign_perm('myapp.delete_document', self.request.user, obj)
```

### Custom DjangoObjectPermissions

Add view permission requirement for GET:

```python
class CustomObjectPermissions(DjangoObjectPermissions):
    """
    Require 'view' permission for GET requests.
    """
    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s'],
        'OPTIONS': [],
        'HEAD': ['%(app_label)s.view_%(model_name)s'],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }

class DocumentViewSet(ModelViewSet):
    permission_classes = [CustomObjectPermissions]
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
```

### Checking Permissions

```python
from guardian.shortcuts import get_perms, get_users_with_perms

# Get all permissions user has on object
perms = get_perms(user, document)
# Returns: ['view_document', 'change_document']

# Get all users who have any permission on object
users = get_users_with_perms(document)

# Check if user has specific permission
if user.has_perm('myapp.view_document', document):
    print("User can view document")
```

---

## Filtering Querysets by Permissions

**Problem:** Object-level permissions are NOT checked for list actions. Users can see all objects in the queryset, even if they can't access individual objects.

### Solution 1: Override get_queryset()

```python
class DocumentViewSet(ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        """
        Filter queryset to only show documents the user can access.
        """
        user = self.request.user

        if user.is_staff:
            # Admin can see everything
            return Document.objects.all()

        # Regular users only see their own documents
        return Document.objects.filter(owner=user)
```

### Solution 2: Filter by Multiple Criteria

```python
class ArticleViewSet(ModelViewSet):
    serializer_class = ArticleSerializer

    def get_queryset(self):
        user = self.request.user

        # Anonymous users: only published articles
        if not user.is_authenticated:
            return Article.objects.filter(published=True)

        # Authenticated users: published + their own drafts
        return Article.objects.filter(
            Q(published=True) | Q(author=user)
        )
```

### Solution 3: Guardian Filter

```python
from guardian.shortcuts import get_objects_for_user

class DocumentViewSet(ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [DjangoObjectPermissions]

    def get_queryset(self):
        """
        Use Guardian to filter by object permissions.
        """
        user = self.request.user

        if not user.is_authenticated:
            return Document.objects.none()

        # Get all documents user has 'view' permission on
        return get_objects_for_user(
            user,
            'myapp.view_document',
            klass=Document
        )
```

### Solution 4: Multiple Permissions

```python
from guardian.shortcuts import get_objects_for_user

class DocumentViewSet(ModelViewSet):
    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return Document.objects.none()

        # Different permissions based on action
        if self.action == 'list':
            perm = 'myapp.view_document'
        elif self.action in ['update', 'partial_update']:
            perm = 'myapp.change_document'
        elif self.action == 'destroy':
            perm = 'myapp.delete_document'
        else:
            perm = 'myapp.view_document'

        return get_objects_for_user(user, perm, klass=Document)
```

### Solution 5: Prefetch Permissions

```python
from guardian.shortcuts import get_objects_for_user

class DocumentViewSet(ModelViewSet):
    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return Document.objects.none()

        # Prefetch related permissions to avoid N+1 queries
        return get_objects_for_user(
            user,
            'myapp.view_document',
            klass=Document,
            accept_global_perms=False  # Only check object-level perms
        ).select_related('owner').prefetch_related('collaborators')
```

---

## Common Patterns

### Pattern 1: Owner-Only Access

```python
class IsOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user

class MyModelViewSet(ModelViewSet):
    permission_classes = [IsOwner]
    serializer_class = MyModelSerializer

    def get_queryset(self):
        # Filter list to only user's objects
        return MyModel.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        # Automatically set owner on creation
        serializer.save(owner=self.request.user)
```

### Pattern 2: Owner or Team Member

```python
class IsOwnerOrTeamMember(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user

        if not user.is_authenticated:
            return False

        # Owner can access
        if obj.owner == user:
            return True

        # Team members can access
        return user in obj.team.members.all()

class ProjectViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwnerOrTeamMember]

    def get_queryset(self):
        user = self.request.user
        # Show projects where user is owner or team member
        return Project.objects.filter(
            Q(owner=user) | Q(team__members=user)
        ).distinct()
```

### Pattern 3: Hierarchical Permissions

```python
class CanAccessProject(permissions.BasePermission):
    """
    Organization admin > Project owner > Project member
    """
    def has_object_permission(self, request, view, obj):
        user = request.user

        if not user.is_authenticated:
            return False

        # Organization admin has full access
        if obj.organization.admins.filter(id=user.id).exists():
            return True

        # Project owner has full access
        if obj.owner == user:
            return True

        # Project members have limited access
        if user in obj.members.all():
            # Members can read but not delete
            if request.method == 'DELETE':
                return False
            return True

        return False
```

### Pattern 4: State-Based Permissions

```python
class CanEditArticle(permissions.BasePermission):
    """
    Allow editing only if article is in draft state.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        # Can't edit published articles
        if obj.status == 'published':
            return False

        # Must be the author
        return obj.author == request.user
```

### Pattern 5: Time-Based Permissions

```python
from django.utils import timezone
from datetime import timedelta

class CanEditRecent(permissions.BasePermission):
    """
    Allow editing only within 24 hours of creation.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        # Check time window
        age = timezone.now() - obj.created_at
        if age > timedelta(hours=24):
            return False

        # Must be the creator
        return obj.created_by == request.user
```

---

## Performance Optimization

### Problem: N+1 Queries

**Bad:**
```python
class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # This causes N+1 if obj.owner is not prefetched
        return obj.owner == request.user

class MyViewSet(ModelViewSet):
    permission_classes = [IsOwner]
    queryset = MyModel.objects.all()  # No select_related!
```

**Good:**
```python
class MyViewSet(ModelViewSet):
    permission_classes = [IsOwner]

    def get_queryset(self):
        return MyModel.objects.select_related('owner')
```

### Optimization Techniques

#### 1. select_related for ForeignKey

```python
def get_queryset(self):
    return Article.objects.select_related('author', 'category')
```

#### 2. prefetch_related for ManyToMany

```python
def get_queryset(self):
    return Project.objects.prefetch_related('members', 'tags')
```

#### 3. Combined Optimization

```python
def get_queryset(self):
    return Article.objects.select_related(
        'author',
        'category'
    ).prefetch_related(
        'collaborators',
        'tags'
    )
```

#### 4. Prefetch with Filtering

```python
from django.db.models import Prefetch

def get_queryset(self):
    active_members = User.objects.filter(is_active=True)
    return Project.objects.prefetch_related(
        Prefetch('members', queryset=active_members, to_attr='active_members')
    )
```

#### 5. Guardian Optimization

```python
from guardian.shortcuts import get_objects_for_user

def get_queryset(self):
    # Guardian's get_objects_for_user is optimized
    return get_objects_for_user(
        self.request.user,
        'myapp.view_document',
        klass=Document
    ).select_related('owner').prefetch_related('collaborators')
```

### Caching Permissions

```python
from django.core.cache import cache

class HasCachedPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        cache_key = f'perm:{user.id}:{obj._meta.label}:{obj.pk}'

        # Check cache first
        result = cache.get(cache_key)
        if result is not None:
            return result

        # Compute permission
        result = self._check_permission(user, obj)

        # Cache for 5 minutes
        cache.set(cache_key, result, 300)
        return result

    def _check_permission(self, user, obj):
        # Your expensive permission logic here
        return obj.owner == user or user in obj.team.members.all()
```

---

## Troubleshooting

### Issue 1: Object Permission Not Called

**Problem:** `has_object_permission()` is not being called.

**Causes:**
1. You're testing a list action (only called for retrieve/update/destroy)
2. `has_permission()` returned False (object permission is never checked)
3. You're not using a ViewSet or using a custom view that doesn't call it

**Solution:**
```python
# For custom views, explicitly call check_object_permissions
class CustomDetailView(APIView):
    def get(self, request, pk):
        obj = get_object_or_404(MyModel, pk=pk)
        # Explicitly check object permissions
        self.check_object_permissions(request, obj)
        serializer = MySerializer(obj)
        return Response(serializer.data)
```

### Issue 2: List Shows All Objects

**Problem:** List action shows all objects, even those user can't access.

**Cause:** Object permissions are NOT checked for list actions.

**Solution:** Filter queryset in `get_queryset()`:
```python
def get_queryset(self):
    return MyModel.objects.filter(owner=self.request.user)
```

### Issue 3: 403 vs 404

**Problem:** Want to return 404 instead of 403 for objects user can't access.

**Solution:** Raise Http404 in permission check:
```python
from django.http import Http404

class IsOwnerOr404(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if obj.owner != request.user:
            raise Http404
        return True
```

### Issue 4: Permission Check Performance

**Problem:** Permission checks are slow due to database queries.

**Solutions:**
1. Use `select_related()` and `prefetch_related()`
2. Cache permission results
3. Add database indexes
4. Denormalize permission data onto user model

### Issue 5: Guardian Permissions Not Working

**Problem:** Guardian permissions always return False.

**Checklist:**
- [ ] Guardian is in INSTALLED_APPS
- [ ] ObjectPermissionBackend is in AUTHENTICATION_BACKENDS
- [ ] Migrations have been run
- [ ] Permissions have been assigned with `assign_perm()`
- [ ] Permission string format is correct: `'app_label.permission_name'`

**Debug:**
```python
from guardian.shortcuts import get_perms

# Check what permissions user has on object
perms = get_perms(user, obj)
print(f"User {user} has permissions: {perms}")
```

### Issue 6: Tests Failing

**Problem:** Permission tests are failing.

**Common Issues:**
1. Anonymous user instead of authenticated user
2. Object not saved to database (no pk)
3. Related objects not created
4. Wrong permission class being tested

**Example Test:**
```python
def test_owner_permission(self):
    user = User.objects.create(username='testuser')
    obj = MyModel.objects.create(owner=user)  # Must save to DB

    request = self.factory.get('/')
    request.user = user  # Not AnonymousUser

    permission = IsOwner()
    has_perm = permission.has_object_permission(request, None, obj)

    self.assertTrue(has_perm)
```

---

## Summary

**Key Points:**
- Object permissions are checked ONLY for retrieve/update/destroy
- Always implement `has_permission()` to protect list/create
- Filter querysets in `get_queryset()` to hide unauthorized objects
- Use `select_related()` and `prefetch_related()` to avoid N+1 queries
- Guardian provides powerful per-object permission management
- Return 404 instead of 403 to avoid information leakage
- Test both view-level and object-level permissions separately

**Best Practice Pattern:**
```python
class IsOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        # View-level check
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Object-level check
        return obj.owner == request.user

class MyViewSet(ModelViewSet):
    permission_classes = [IsOwner]
    serializer_class = MySerializer

    def get_queryset(self):
        # Filter queryset for list action
        return MyModel.objects.filter(
            owner=self.request.user
        ).select_related('owner')  # Optimize

    def perform_create(self, serializer):
        # Set owner automatically
        serializer.save(owner=self.request.user)
```
