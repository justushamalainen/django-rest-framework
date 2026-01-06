# Mixins

Composable building blocks for creating custom view behavior. Mix and match to create exactly the view you need.

## Overview

**Mixins** provide single CRUD operations that can be combined with `GenericAPIView` or `GenericViewSet` to create custom views.

**Source:** `rest_framework/mixins.py` (96 lines)

## The 5 Core Mixins

| Mixin | Action | HTTP Method | Use Case |
|-------|--------|-------------|----------|
| **CreateModelMixin** | `create()` | POST | Create new instance |
| **ListModelMixin** | `list()` | GET | List collection |
| **RetrieveModelMixin** | `retrieve()` | GET | Get single instance |
| **UpdateModelMixin** | `update()`, `partial_update()` | PUT, PATCH | Update instance |
| **DestroyModelMixin** | `destroy()` | DELETE | Delete instance |

---

## 1. CreateModelMixin

Creates a new model instance.

### Source Code Simplified

```python
class CreateModelMixin:
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)  # Hook for customization
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save()

    def get_success_headers(self, data):
        try:
            return {'Location': str(data[api_settings.URL_FIELD_NAME])}
        except (TypeError, KeyError):
            return {}
```

### Usage Example

```python
from rest_framework import mixins
from rest_framework.generics import GenericAPIView

class ArticleCreateView(mixins.CreateModelMixin, GenericAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)
```

### Customization: Override perform_create()

**Most common customization** - Set fields not in the request:

```python
class ArticleCreateView(mixins.CreateModelMixin, GenericAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    def perform_create(self, serializer):
        # Add author from request user
        serializer.save(author=self.request.user)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)
```

**Advanced:** Multiple related objects:

```python
def perform_create(self, serializer):
    # Save main object
    article = serializer.save(author=self.request.user)

    # Create related objects
    Tag.objects.create(article=article, name='auto-tagged')

    # Send notifications
    notify_followers(article.author, article)
```

**Custom validation:**

```python
def perform_create(self, serializer):
    # Check business rules
    if Article.objects.filter(
        author=self.request.user,
        published=False
    ).count() >= 5:
        raise ValidationError("You have too many unpublished drafts.")

    serializer.save(author=self.request.user)
```

### When to Override create() Instead

Only override `create()` if you need to change the response or status code:

```python
def create(self, request, *args, **kwargs):
    serializer = self.get_serializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    self.perform_create(serializer)

    # Custom response
    return Response(
        {
            'message': 'Article created successfully',
            'article': serializer.data
        },
        status=status.HTTP_201_CREATED
    )
```

---

## 2. ListModelMixin

Lists a collection of model instances.

### Source Code Simplified

```python
class ListModelMixin:
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Pagination (if configured)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        # No pagination
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
```

### Usage Example

```python
class ArticleListView(mixins.ListModelMixin, GenericAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'content']

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)
```

### Customization: Override get_queryset()

**Most common customization** - Filter based on request:

```python
class ArticleListView(mixins.ListModelMixin, GenericAPIView):
    serializer_class = ArticleSerializer

    def get_queryset(self):
        # Filter by published status
        queryset = Article.objects.filter(published=True)

        # Filter by request parameter
        author_id = self.request.query_params.get('author')
        if author_id:
            queryset = queryset.filter(author_id=author_id)

        return queryset

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)
```

**Performance optimization:**

```python
def get_queryset(self):
    return Article.objects.select_related('author').prefetch_related(
        'tags', 'comments'
    ).filter(published=True)
```

### When to Override list() Instead

Only override `list()` for custom response format:

```python
def list(self, request, *args, **kwargs):
    queryset = self.filter_queryset(self.get_queryset())
    serializer = self.get_serializer(queryset, many=True)

    # Custom response structure
    return Response({
        'count': queryset.count(),
        'results': serializer.data,
        'timestamp': timezone.now()
    })
```

---

## 3. RetrieveModelMixin

Retrieves a single model instance.

### Source Code Simplified

```python
class RetrieveModelMixin:
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
```

### Usage Example

```python
class ArticleDetailView(mixins.RetrieveModelMixin, GenericAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    lookup_field = 'pk'  # Default

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)
```

### Customization: Override get_object()

**Custom lookup:**

```python
def get_object(self):
    queryset = self.filter_queryset(self.get_queryset())

    # Multiple lookup fields
    filter_kwargs = {
        'author__username': self.kwargs['username'],
        'slug': self.kwargs['slug']
    }

    obj = get_object_or_404(queryset, **filter_kwargs)
    self.check_object_permissions(self.request, obj)
    return obj
```

**Performance optimization:**

```python
def get_object(self):
    queryset = self.get_queryset().select_related('author').prefetch_related('tags')
    obj = get_object_or_404(queryset, pk=self.kwargs['pk'])
    self.check_object_permissions(self.request, obj)
    return obj
```

**Track access:**

```python
def get_object(self):
    obj = super().get_object()

    # Log access
    ViewLog.objects.create(
        article=obj,
        user=self.request.user,
        timestamp=timezone.now()
    )

    return obj
```

---

## 4. UpdateModelMixin

Updates an existing model instance.

### Source Code Simplified

```python
class UpdateModelMixin:
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)  # Hook for customization

        # Clear prefetch cache if needed
        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save()

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
```

### Usage Example

```python
class ArticleUpdateView(mixins.UpdateModelMixin, GenericAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)
```

### Customization: Override perform_update()

**Most common customization** - Add metadata:

```python
def perform_update(self, serializer):
    # Update timestamp
    serializer.save(
        updated_at=timezone.now(),
        updated_by=self.request.user
    )
```

**Business logic:**

```python
def perform_update(self, serializer):
    instance = serializer.instance

    # Check ownership
    if instance.author != self.request.user:
        raise PermissionDenied("You can only edit your own articles.")

    # Validate business rules
    if instance.published and not serializer.validated_data.get('published'):
        raise ValidationError("Cannot unpublish an article.")

    serializer.save()
```

**Cascade updates:**

```python
def perform_update(self, serializer):
    article = serializer.save()

    # Update related objects
    if 'featured' in serializer.validated_data:
        if article.featured:
            # Unfeature other articles
            Article.objects.exclude(pk=article.pk).update(featured=False)
```

### Difference: PUT vs PATCH

```python
# PUT: Full update (all fields required)
# PATCH: Partial update (only provided fields)

def update(self, request, *args, **kwargs):
    partial = kwargs.pop('partial', False)  # False for PUT, True for PATCH
    instance = self.get_object()
    serializer = self.get_serializer(
        instance,
        data=request.data,
        partial=partial  # Allows partial validation
    )
    serializer.is_valid(raise_exception=True)
    self.perform_update(serializer)
    return Response(serializer.data)
```

---

## 5. DestroyModelMixin

Deletes a model instance.

### Source Code Simplified

```python
class DestroyModelMixin:
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)  # Hook for customization
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        instance.delete()
```

### Usage Example

```python
class ArticleDeleteView(mixins.DestroyModelMixin, GenericAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer  # Often not needed for DELETE

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)
```

### Customization: Override perform_destroy()

**Soft delete:**

```python
def perform_destroy(self, instance):
    # Soft delete instead of hard delete
    instance.deleted = True
    instance.deleted_at = timezone.now()
    instance.deleted_by = self.request.user
    instance.save()
```

**Ownership check:**

```python
def perform_destroy(self, instance):
    if instance.author != self.request.user and not self.request.user.is_staff:
        raise PermissionDenied("You can only delete your own articles.")

    instance.delete()
```

**Cascade operations:**

```python
def perform_destroy(self, instance):
    # Archive related data before deletion
    for comment in instance.comments.all():
        ArchivedComment.objects.create(
            content=comment.content,
            article_id=instance.id,
            archived_at=timezone.now()
        )

    # Delete
    instance.delete()
```

**Custom response:**

Override `destroy()` instead of `perform_destroy()`:

```python
def destroy(self, request, *args, **kwargs):
    instance = self.get_object()
    instance_id = instance.id
    self.perform_destroy(instance)

    # Custom response (not just 204)
    return Response(
        {'message': f'Article {instance_id} deleted successfully'},
        status=status.HTTP_200_OK
    )
```

---

## Composing Mixins

Create custom view classes by mixing multiple mixins:

### Example 1: List + Create

```python
from rest_framework import mixins
from rest_framework.generics import GenericAPIView

class ArticleListCreateView(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    GenericAPIView
):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)
```

**This is exactly what `ListCreateAPIView` does!**

### Example 2: Custom Combination (Retrieve + Destroy only)

```python
class ArticleReadDeleteView(
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    GenericAPIView
):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

    # No update methods!
```

### Example 3: With ViewSet

```python
from rest_framework.viewsets import GenericViewSet

class ArticleViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet  # Note: Not GenericAPIView
):
    """ViewSet with only list, create, retrieve (no update/delete)"""
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

# Router automatically maps:
# GET    /articles/       → list()
# POST   /articles/       → create()
# GET    /articles/{pk}/  → retrieve()
```

---

## perform_* Hooks Reference

All `perform_*` hooks are called AFTER validation but BEFORE returning the response.

| Hook | Mixin | Called When | Use Case |
|------|-------|-------------|----------|
| **perform_create(serializer)** | CreateModelMixin | After POST validation | Set author, send notifications |
| **perform_update(serializer)** | UpdateModelMixin | After PUT/PATCH validation | Update metadata, validate ownership |
| **perform_destroy(instance)** | DestroyModelMixin | Before DELETE | Soft delete, check ownership |

### Common Patterns

#### Pattern 1: Set Request User

```python
def perform_create(self, serializer):
    serializer.save(author=self.request.user)

def perform_update(self, serializer):
    serializer.save(updated_by=self.request.user)
```

#### Pattern 2: Ownership Validation

```python
def perform_update(self, serializer):
    if serializer.instance.author != self.request.user:
        raise PermissionDenied("Not your article")
    serializer.save()

def perform_destroy(self, instance):
    if instance.author != self.request.user:
        raise PermissionDenied("Not your article")
    instance.delete()
```

#### Pattern 3: Trigger Side Effects

```python
def perform_create(self, serializer):
    article = serializer.save(author=self.request.user)
    # Send email
    send_notification(article.author, "Article created")

def perform_destroy(self, instance):
    # Log deletion
    logger.info(f"User {self.request.user} deleted article {instance.id}")
    instance.delete()
```

---

## Complete Example: Custom ViewSet with All Mixins

```python
from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.exceptions import PermissionDenied
from .models import Article
from .serializers import ArticleSerializer

class ArticleViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet
):
    """
    Full CRUD ViewSet using mixins.
    Identical to ModelViewSet but more explicit.
    """
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        """Show published to all, all to authenticated users"""
        if self.request.user.is_authenticated:
            return Article.objects.all()
        return Article.objects.filter(published=True)

    def perform_create(self, serializer):
        """Set author on create"""
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        """Only owner can update"""
        if serializer.instance.author != self.request.user:
            raise PermissionDenied("You can only edit your own articles")
        serializer.save(updated_at=timezone.now())

    def perform_destroy(self, instance):
        """Only owner can delete"""
        if instance.author != self.request.user:
            raise PermissionDenied("You can only delete your own articles")
        instance.delete()
```

---

## When to Use Mixins

**Use mixins when:**
- ✅ You need a custom combination of CRUD operations
- ✅ Generic views don't provide the exact combination you need
- ✅ You want explicit control over which operations are available
- ✅ Building custom ViewSet classes

**Don't use mixins when:**
- ❌ A generic view already provides what you need (use `ListCreateAPIView` instead)
- ❌ You need non-standard behavior (use `APIView` instead)
- ❌ You're already using `ModelViewSet` (it includes all mixins)

---

## See Also

- **[generic-views.md](generic-views.md)** - Pre-built combinations of mixins
- **[viewsets.md](viewsets.md)** - Using mixins with ViewSets
- **[apiview.md](apiview.md)** - Base view class
