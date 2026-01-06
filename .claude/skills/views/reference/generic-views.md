# Generic Views

Pre-built views for common CRUD operations. Reduce boilerplate by 80-90% compared to APIView.

## Overview

Generic views combine **mixins** with **GenericAPIView** to create concrete view classes for standard operations:

| View Class | Methods | Operations | Use Case |
|------------|---------|------------|----------|
| **CreateAPIView** | POST | Create | New resource endpoint |
| **ListAPIView** | GET | List all | Collection endpoint |
| **RetrieveAPIView** | GET | Get one | Detail endpoint (read-only) |
| **UpdateAPIView** | PUT, PATCH | Update | Detail endpoint (write-only) |
| **DestroyAPIView** | DELETE | Delete | Detail endpoint (delete) |
| **ListCreateAPIView** | GET, POST | List + Create | Collection with create |
| **RetrieveUpdateAPIView** | GET, PUT, PATCH | Read + Update | Detail (no delete) |
| **RetrieveDestroyAPIView** | GET, DELETE | Read + Delete | Detail (no update) |
| **RetrieveUpdateDestroyAPIView** | GET, PUT, PATCH, DELETE | Full CRUD | Complete detail endpoint |

**Source:** `rest_framework/generics.py` (296 lines)

## Base Class: GenericAPIView

All generic views inherit from `GenericAPIView`, which provides:

```python
from rest_framework.generics import GenericAPIView

class GenericAPIView(APIView):
    # Required attributes (set these!)
    queryset = None                      # Model queryset
    serializer_class = None              # Serializer class

    # Optional attributes
    lookup_field = 'pk'                  # URL kwarg for object lookup
    lookup_url_kwarg = None              # Override URL kwarg name
    filter_backends = []                 # Filtering classes
    pagination_class = None              # Pagination class

    # Key methods
    def get_queryset(self):              # Override for custom querysets
    def get_object(self):                # Get single object by lookup_field
    def get_serializer(self, *args, **kwargs):  # Get serializer instance
    def get_serializer_class(self):      # Override for dynamic serializer
    def filter_queryset(self, queryset): # Apply filters
    def paginate_queryset(self, queryset):  # Apply pagination
```

## 1. CreateAPIView

**Purpose:** Create a new model instance.

```python
from rest_framework.generics import CreateAPIView
from .models import Article
from .serializers import ArticleSerializer

class ArticleCreateView(CreateAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    # Optional: Override to customize creation
    def perform_create(self, serializer):
        # Add custom fields not in request
        serializer.save(author=self.request.user)
```

**URL:** `path('articles/', ArticleCreateView.as_view())`

**HTTP Methods:**
- `POST /articles/` → Create new article → 201 Created

**Common Overrides:**
```python
def perform_create(self, serializer):
    """Customize save behavior"""
    serializer.save(created_by=self.request.user)

def create(self, request, *args, **kwargs):
    """Override entire create logic (rarely needed)"""
    # Full customization
    pass
```

---

## 2. ListAPIView

**Purpose:** List a collection of model instances.

```python
from rest_framework.generics import ListAPIView

class ArticleListView(ListAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content']
    ordering_fields = ['created_at', 'title']

    # Optional: Filter by request user
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(published=True)
```

**URL:** `path('articles/', ArticleListView.as_view())`

**HTTP Methods:**
- `GET /articles/` → List all articles → 200 OK

**Supports:**
- Pagination (automatic if configured)
- Filtering (via filter_backends)
- Ordering (via ordering_fields)

---

## 3. RetrieveAPIView

**Purpose:** Retrieve a single model instance (read-only).

```python
from rest_framework.generics import RetrieveAPIView

class ArticleDetailView(RetrieveAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    lookup_field = 'pk'  # Default; can use 'slug', 'uuid', etc.
```

**URL:** `path('articles/<int:pk>/', ArticleDetailView.as_view())`

**HTTP Methods:**
- `GET /articles/{pk}/` → Get article → 200 OK
- Returns 404 if not found

---

## 4. UpdateAPIView

**Purpose:** Update a model instance (write-only).

```python
from rest_framework.generics import UpdateAPIView

class ArticleUpdateView(UpdateAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    def perform_update(self, serializer):
        """Customize update behavior"""
        serializer.save(updated_by=self.request.user)
```

**URL:** `path('articles/<int:pk>/', ArticleUpdateView.as_view())`

**HTTP Methods:**
- `PUT /articles/{pk}/` → Full update → 200 OK
- `PATCH /articles/{pk}/` → Partial update → 200 OK

**Common Overrides:**
```python
def perform_update(self, serializer):
    """Called after validation, before save"""
    serializer.save(last_modified=timezone.now())

def update(self, request, *args, **kwargs):
    """Override entire update logic (rarely needed)"""
    partial = kwargs.pop('partial', False)
    instance = self.get_object()
    # Custom logic...
```

---

## 5. DestroyAPIView

**Purpose:** Delete a model instance.

```python
from rest_framework.generics import DestroyAPIView

class ArticleDeleteView(DestroyAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer  # Not used, but often required

    def perform_destroy(self, instance):
        """Customize deletion behavior"""
        # Soft delete example
        instance.deleted = True
        instance.save()
```

**URL:** `path('articles/<int:pk>/', ArticleDeleteView.as_view())`

**HTTP Methods:**
- `DELETE /articles/{pk}/` → Delete article → 204 No Content

---

## 6. ListCreateAPIView

**Purpose:** List collection OR create new instance (most common pattern).

```python
from rest_framework.generics import ListCreateAPIView

class ArticleListCreateView(ListCreateAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_queryset(self):
        # Filter list by published status
        return Article.objects.filter(published=True)
```

**URL:** `path('articles/', ArticleListCreateView.as_view())`

**HTTP Methods:**
- `GET /articles/` → List articles → 200 OK
- `POST /articles/` → Create article → 201 Created

**Perfect for:** RESTful collection endpoints.

---

## 7. RetrieveUpdateAPIView

**Purpose:** Get or update a single instance (no delete).

```python
from rest_framework.generics import RetrieveUpdateAPIView

class ArticleDetailUpdateView(RetrieveUpdateAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
```

**URL:** `path('articles/<int:pk>/', ArticleDetailUpdateView.as_view())`

**HTTP Methods:**
- `GET /articles/{pk}/` → Get article → 200 OK
- `PUT /articles/{pk}/` → Full update → 200 OK
- `PATCH /articles/{pk}/` → Partial update → 200 OK

---

## 8. RetrieveDestroyAPIView

**Purpose:** Get or delete a single instance (no update).

```python
from rest_framework.generics import RetrieveDestroyAPIView

class ArticleDetailDeleteView(RetrieveDestroyAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
```

**URL:** `path('articles/<int:pk>/', ArticleDetailDeleteView.as_view())`

**HTTP Methods:**
- `GET /articles/{pk}/` → Get article → 200 OK
- `DELETE /articles/{pk}/` → Delete article → 204 No Content

---

## 9. RetrieveUpdateDestroyAPIView

**Purpose:** Full CRUD on a single instance (most versatile).

```python
from rest_framework.generics import RetrieveUpdateDestroyAPIView

class ArticleDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        # Log deletion
        logger.info(f"Article {instance.id} deleted by {self.request.user}")
        instance.delete()
```

**URL:** `path('articles/<int:pk>/', ArticleDetailView.as_view())`

**HTTP Methods:**
- `GET /articles/{pk}/` → Get article → 200 OK
- `PUT /articles/{pk}/` → Full update → 200 OK
- `PATCH /articles/{pk}/` → Partial update → 200 OK
- `DELETE /articles/{pk}/` → Delete article → 204 No Content

---

## Common Customizations

### 1. Dynamic Queryset Filtering

```python
class UserArticleListView(ListAPIView):
    serializer_class = ArticleSerializer

    def get_queryset(self):
        """Filter by request user"""
        return Article.objects.filter(author=self.request.user)
```

### 2. Dynamic Serializer Selection

```python
class ArticleDetailView(RetrieveUpdateAPIView):
    queryset = Article.objects.all()

    def get_serializer_class(self):
        """Use different serializers for read vs write"""
        if self.request.method == 'GET':
            return ArticleDetailSerializer
        return ArticleUpdateSerializer
```

### 3. Custom Lookup Field

```python
class ArticleBySlugView(RetrieveAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    lookup_field = 'slug'  # URL kwarg name

# URL: path('articles/<slug:slug>/', ArticleBySlugView.as_view())
```

### 4. Multiple Lookup Fields

```python
class ArticleByUserAndSlugView(RetrieveAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    def get_object(self):
        """Custom lookup with multiple fields"""
        queryset = self.filter_queryset(self.get_queryset())
        filter_kwargs = {
            'author__username': self.kwargs['username'],
            'slug': self.kwargs['slug']
        }
        obj = get_object_or_404(queryset, **filter_kwargs)
        self.check_object_permissions(self.request, obj)
        return obj

# URL: path('users/<str:username>/articles/<slug:slug>/', ...)
```

### 5. Eager Loading Relations

```python
class ArticleListView(ListAPIView):
    serializer_class = ArticleSerializer

    def get_queryset(self):
        """Optimize queries with select_related/prefetch_related"""
        return Article.objects.select_related('author').prefetch_related('tags')
```

### 6. Permission-Based Filtering

```python
class ArticleListView(ListAPIView):
    serializer_class = ArticleSerializer

    def get_queryset(self):
        """Show different data based on user permissions"""
        user = self.request.user
        if user.is_staff:
            return Article.objects.all()  # Staff sees everything
        elif user.is_authenticated:
            return Article.objects.filter(
                Q(published=True) | Q(author=user)  # Own + published
            )
        return Article.objects.filter(published=True)  # Public only
```

## Complete Example: Blog API

```python
# views.py
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView
)
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .models import Article
from .serializers import ArticleSerializer, ArticleDetailSerializer

class ArticleListCreateView(ListCreateAPIView):
    """
    GET:  List all published articles (paginated)
    POST: Create new article (authenticated users only)
    """
    queryset = Article.objects.filter(published=True)
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content']
    ordering_fields = ['created_at', 'title']
    ordering = ['-created_at']  # Default ordering

    def get_queryset(self):
        """Staff can see unpublished articles"""
        queryset = super().get_queryset()
        if self.request.user.is_staff:
            return Article.objects.all()
        return queryset

    def perform_create(self, serializer):
        """Set author to request user"""
        serializer.save(author=self.request.user)


class ArticleDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET:    Retrieve article
    PUT:    Update article (owner only)
    PATCH:  Partial update (owner only)
    DELETE: Delete article (owner only)
    """
    queryset = Article.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'

    def get_serializer_class(self):
        """Detailed serializer for GET, simple for POST/PUT"""
        if self.request.method == 'GET':
            return ArticleDetailSerializer
        return ArticleSerializer

    def get_queryset(self):
        """Optimize queries"""
        return Article.objects.select_related('author').prefetch_related(
            'tags', 'comments'
        )

    def perform_update(self, serializer):
        """Only owner can update"""
        if serializer.instance.author != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only edit your own articles.")
        serializer.save(updated_at=timezone.now())

    def perform_destroy(self, instance):
        """Only owner can delete"""
        if instance.author != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only delete your own articles.")
        instance.delete()


# urls.py
from django.urls import path

urlpatterns = [
    path('articles/', ArticleListCreateView.as_view(), name='article-list'),
    path('articles/<slug:slug>/', ArticleDetailView.as_view(), name='article-detail'),
]
```

## Decision Guide

**Use Generic Views when:**
- ✅ Standard CRUD operations on a single model
- ✅ Want minimal code with maximum readability
- ✅ Need filtering, pagination, ordering out of the box
- ✅ Endpoints map clearly to HTTP methods

**Don't use Generic Views when:**
- ❌ Complex business logic that doesn't fit CRUD
- ❌ Multiple models in one endpoint
- ❌ Non-standard HTTP behavior needed
- ❌ Want automatic URL routing (use ViewSets instead)

## See Also

- **[apiview.md](apiview.md)** - Lower-level control
- **[mixins.md](mixins.md)** - Building blocks of generic views
- **[viewsets.md](viewsets.md)** - Higher-level with automatic routing
