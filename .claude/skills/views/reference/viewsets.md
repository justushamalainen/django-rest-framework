# ViewSets

ViewSets combine related views into a single class and work with routers for automatic URL configuration. The most powerful DRF pattern for building RESTful APIs.

## Overview

**ViewSets** provide actions (list, create, retrieve, update, destroy) instead of HTTP methods (get, post, put, delete). Actions are mapped to HTTP methods via routers or explicit binding.

**Key difference from views:**
- **Views:** Define `get()`, `post()`, etc.
- **ViewSets:** Define `list()`, `create()`, `retrieve()`, `update()`, `destroy()`

**Source:** `rest_framework/viewsets.py` (256 lines)

## ViewSet Hierarchy

```
ViewSet                      # Base class (no built-in actions)
  └─ GenericViewSet          # Adds queryset/serializer helpers
       ├─ ReadOnlyModelViewSet    # list() + retrieve()
       └─ ModelViewSet             # Full CRUD (all 5 actions)
```

## 1. ViewSet (Base Class)

Empty ViewSet with no actions. Use for completely custom viewsets.

```python
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response

class CustomViewSet(ViewSet):
    """
    A simple ViewSet with custom actions.
    """
    def list(self, request):
        """GET /items/"""
        return Response({'items': []})

    def create(self, request):
        """POST /items/"""
        return Response({'created': True})

    def retrieve(self, request, pk=None):
        """GET /items/{pk}/"""
        return Response({'id': pk})

    def update(self, request, pk=None):
        """PUT /items/{pk}/"""
        return Response({'updated': pk})

    def partial_update(self, request, pk=None):
        """PATCH /items/{pk}/"""
        return Response({'patched': pk})

    def destroy(self, request, pk=None):
        """DELETE /items/{pk}/"""
        return Response(status=204)

# urls.py (manual binding)
from django.urls import path
from .views import CustomViewSet

item_list = CustomViewSet.as_view({'get': 'list', 'post': 'create'})
item_detail = CustomViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

urlpatterns = [
    path('items/', item_list, name='item-list'),
    path('items/<int:pk>/', item_detail, name='item-detail'),
]
```

**Use ViewSet when:** You need complete custom control without queryset/serializer helpers.

---

## 2. GenericViewSet

Adds `get_queryset()`, `get_serializer()`, and other helpers. Combine with mixins for CRUD operations.

```python
from rest_framework.viewsets import GenericViewSet
from rest_framework import mixins
from .models import Article
from .serializers import ArticleSerializer

class ArticleViewSet(mixins.ListModelMixin,
                     mixins.CreateModelMixin,
                     GenericViewSet):
    """
    Custom ViewSet with only list and create actions.
    """
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

# Automatic URL routing with router
from rest_framework.routers import DefaultRouter
router = DefaultRouter()
router.register(r'articles', ArticleViewSet)
urlpatterns = router.urls
```

**Use GenericViewSet when:** You want to compose custom combinations of CRUD operations.

---

## 3. ReadOnlyModelViewSet

Pre-built ViewSet with `list()` and `retrieve()` only. Perfect for read-only APIs.

```python
from rest_framework.viewsets import ReadOnlyModelViewSet
from .models import Article
from .serializers import ArticleSerializer

class ArticleViewSet(ReadOnlyModelViewSet):
    """
    Read-only API endpoint for articles.
    Provides: list() and retrieve()
    """
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'content']

# Router automatically creates:
# GET    /articles/          → list()
# GET    /articles/{pk}/     → retrieve()
```

**Equivalent to:**
```python
class ArticleViewSet(mixins.ListModelMixin,
                     mixins.RetrieveModelMixin,
                     GenericViewSet):
    pass
```

**Use ReadOnlyModelViewSet when:** Your API is read-only (no create/update/delete).

---

## 4. ModelViewSet (Most Common)

Full CRUD ViewSet. Provides all 5 actions out of the box.

```python
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .models import Article
from .serializers import ArticleSerializer

class ArticleViewSet(ModelViewSet):
    """
    Full CRUD API endpoint for articles.
    Provides: list(), create(), retrieve(), update(), partial_update(), destroy()
    """
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content']
    ordering_fields = ['created_at', 'title']

    def perform_create(self, serializer):
        """Override to set author"""
        serializer.save(author=self.request.user)

# Router creates:
# GET    /articles/          → list()
# POST   /articles/          → create()
# GET    /articles/{pk}/     → retrieve()
# PUT    /articles/{pk}/     → update()
# PATCH  /articles/{pk}/     → partial_update()
# DELETE /articles/{pk}/     → destroy()
```

**Equivalent to:**
```python
class ArticleViewSet(mixins.CreateModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin,
                     mixins.DestroyModelMixin,
                     mixins.ListModelMixin,
                     GenericViewSet):
    pass
```

**Use ModelViewSet when:** You need full CRUD operations on a model.

---

## @action Decorator: Custom Endpoints

Add custom actions beyond CRUD with the `@action` decorator.

### Basic @action Usage

```python
from rest_framework.decorators import action
from rest_framework.response import Response

class ArticleViewSet(ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        GET /articles/recent/
        List action (operates on collection)
        """
        recent_articles = Article.objects.order_by('-created_at')[:10]
        serializer = self.get_serializer(recent_articles, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """
        POST /articles/{pk}/publish/
        Detail action (operates on single object)
        """
        article = self.get_object()
        article.published = True
        article.published_at = timezone.now()
        article.save()
        return Response({'status': 'published'})

    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        """
        GET  /articles/{pk}/comments/  → List comments
        POST /articles/{pk}/comments/  → Add comment
        """
        article = self.get_object()

        if request.method == 'GET':
            comments = article.comments.all()
            serializer = CommentSerializer(comments, many=True)
            return Response(serializer.data)

        elif request.method == 'POST':
            serializer = CommentSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(article=article, author=request.user)
                return Response(serializer.data, status=201)
            return Response(serializer.errors, status=400)
```

### @action Parameters

```python
@action(
    detail=True,              # REQUIRED: True = detail, False = list
    methods=['get'],          # HTTP methods (default: ['get'])
    url_path='custom-path',   # URL segment (default: function name)
    url_name='custom-name',   # Reverse URL name (default: function name with dashes)
    permission_classes=[...], # Override viewset permissions
    serializer_class=...,     # Override viewset serializer
    # Any other view attribute can be overridden
)
def my_action(self, request, pk=None):
    pass
```

### @action Examples

#### 1. Collection Action (detail=False)

```python
@action(detail=False, methods=['get'])
def stats(self, request):
    """GET /articles/stats/"""
    return Response({
        'total': Article.objects.count(),
        'published': Article.objects.filter(published=True).count(),
        'draft': Article.objects.filter(published=False).count(),
    })
```

#### 2. Detail Action (detail=True)

```python
@action(detail=True, methods=['post'])
def archive(self, request, pk=None):
    """POST /articles/{pk}/archive/"""
    article = self.get_object()
    article.archived = True
    article.save()
    return Response({'status': 'archived'})
```

#### 3. Multiple HTTP Methods

```python
@action(detail=True, methods=['get', 'put', 'delete'])
def featured(self, request, pk=None):
    """
    GET    /articles/{pk}/featured/  → Check if featured
    PUT    /articles/{pk}/featured/  → Mark as featured
    DELETE /articles/{pk}/featured/  → Unmark as featured
    """
    article = self.get_object()

    if request.method == 'GET':
        return Response({'featured': article.featured})

    elif request.method == 'PUT':
        article.featured = True
        article.save()
        return Response({'status': 'marked as featured'})

    elif request.method == 'DELETE':
        article.featured = False
        article.save()
        return Response({'status': 'unmarked'})
```

#### 4. Custom URL Path

```python
@action(detail=False, url_path='my-articles')
def user_articles(self, request):
    """GET /articles/my-articles/"""
    articles = Article.objects.filter(author=request.user)
    serializer = self.get_serializer(articles, many=True)
    return Response(serializer.data)
```

#### 5. Override Permissions

```python
from rest_framework.permissions import IsAuthenticated, AllowAny

class ArticleViewSet(ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=False, permission_classes=[AllowAny])
    def public_feed(self, request):
        """GET /articles/public_feed/ - No auth required"""
        articles = Article.objects.filter(public=True)[:20]
        serializer = self.get_serializer(articles, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        """POST /articles/{pk}/favorite/ - Auth required"""
        article = self.get_object()
        request.user.favorites.add(article)
        return Response({'status': 'favorited'})
```

#### 6. Override Serializer

```python
@action(detail=True, serializer_class=ArticleSummarySerializer)
def summary(self, request, pk=None):
    """GET /articles/{pk}/summary/ - Uses different serializer"""
    article = self.get_object()
    serializer = self.get_serializer(article)
    return Response(serializer.data)
```

### Advanced @action: MethodMapper

Map different methods to different functions:

```python
class ArticleViewSet(ModelViewSet):
    @action(detail=False, methods=['get', 'post'])
    def drafts(self, request):
        """GET /articles/drafts/ - List drafts"""
        if request.method == 'GET':
            drafts = Article.objects.filter(published=False)
            serializer = self.get_serializer(drafts, many=True)
            return Response(serializer.data)
        # POST handled by another method

    @drafts.mapping.post
    def create_draft(self, request):
        """POST /articles/drafts/ - Create draft"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(published=False, author=request.user)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    @drafts.mapping.delete
    def clear_drafts(self, request):
        """DELETE /articles/drafts/ - Delete all user's drafts"""
        Article.objects.filter(
            author=request.user,
            published=False
        ).delete()
        return Response(status=204)
```

---

## Common Customizations

### 1. Dynamic Queryset Filtering

```python
class ArticleViewSet(ModelViewSet):
    serializer_class = ArticleSerializer

    def get_queryset(self):
        """Filter by user for certain actions"""
        queryset = Article.objects.all()

        if self.action == 'list':
            # Public articles for list
            return queryset.filter(published=True)
        elif self.action in ['update', 'partial_update', 'destroy']:
            # Only own articles for modify operations
            return queryset.filter(author=self.request.user)
        return queryset
```

### 2. Action-Based Serializer Selection

```python
class ArticleViewSet(ModelViewSet):
    queryset = Article.objects.all()

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'list':
            return ArticleListSerializer  # Lighter serializer
        elif self.action == 'retrieve':
            return ArticleDetailSerializer  # Full details
        elif self.action in ['create', 'update', 'partial_update']:
            return ArticleWriteSerializer  # Write-only fields
        return ArticleSerializer  # Default
```

### 3. Action-Based Permissions

```python
from rest_framework.permissions import IsAuthenticated, AllowAny

class ArticleViewSet(ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]  # Read is public
        elif self.action == 'create':
            permission_classes = [IsAuthenticated]  # Write requires auth
        else:  # update, partial_update, destroy
            permission_classes = [IsAuthenticated]  # Owner check in perform_*
        return [permission() for permission in permission_classes]

    def perform_update(self, serializer):
        """Only owner can update"""
        if serializer.instance.author != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only edit your own articles.")
        serializer.save()

    def perform_destroy(self, instance):
        """Only owner can delete"""
        if instance.author != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only delete your own articles.")
        instance.delete()
```

### 4. Nested Routes

```python
class CommentViewSet(ModelViewSet):
    serializer_class = CommentSerializer

    def get_queryset(self):
        """Filter comments by article from URL"""
        article_pk = self.kwargs.get('article_pk')
        if article_pk:
            return Comment.objects.filter(article_id=article_pk)
        return Comment.objects.all()

    def perform_create(self, serializer):
        """Auto-set article from URL"""
        article_pk = self.kwargs.get('article_pk')
        article = get_object_or_404(Article, pk=article_pk)
        serializer.save(article=article, author=self.request.user)

# urls.py with drf-nested-routers
from rest_framework_nested import routers

router = routers.DefaultRouter()
router.register(r'articles', ArticleViewSet)

article_router = routers.NestedDefaultRouter(router, r'articles', lookup='article')
article_router.register(r'comments', CommentViewSet, basename='article-comments')

# Creates:
# GET    /articles/{article_pk}/comments/
# POST   /articles/{article_pk}/comments/
# GET    /articles/{article_pk}/comments/{pk}/
# etc.
```

---

## Complete Example: Blog API with ViewSets

```python
# models.py
from django.db import models
from django.contrib.auth.models import User

class Article(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    published = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


# serializers.py
from rest_framework import serializers

class ArticleSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source='author.username')

    class Meta:
        model = Article
        fields = ['id', 'title', 'content', 'author', 'published', 'created_at']


# views.py
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone

class ArticleViewSet(ModelViewSet):
    """
    ViewSet for Article model with full CRUD + custom actions.
    """
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content']
    ordering_fields = ['created_at', 'title']
    ordering = ['-created_at']

    def get_queryset(self):
        """Show published articles to all, own articles to author"""
        queryset = super().get_queryset()
        if not self.request.user.is_authenticated:
            return queryset.filter(published=True)
        if self.action == 'list':
            return queryset.filter(
                Q(published=True) | Q(author=self.request.user)
            )
        return queryset

    def perform_create(self, serializer):
        """Set author to current user"""
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        """Only owner can update"""
        if serializer.instance.author != self.request.user:
            raise PermissionDenied("You can only edit your own articles.")
        serializer.save()

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """GET /articles/featured/"""
        featured = self.queryset.filter(featured=True, published=True)
        serializer = self.get_serializer(featured, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def publish(self, request, pk=None):
        """POST /articles/{pk}/publish/"""
        article = self.get_object()
        if article.author != request.user:
            raise PermissionDenied("You can only publish your own articles.")

        article.published = True
        article.save()
        return Response({'status': 'published'})

    @action(detail=False, permission_classes=[IsAuthenticated])
    def my_articles(self, request):
        """GET /articles/my_articles/"""
        my_articles = self.queryset.filter(author=request.user)
        serializer = self.get_serializer(my_articles, many=True)
        return Response(serializer.data)


# urls.py
from rest_framework.routers import DefaultRouter
from .views import ArticleViewSet

router = DefaultRouter()
router.register(r'articles', ArticleViewSet)
urlpatterns = router.urls

# Generated URLs:
# GET    /articles/                  → list()
# POST   /articles/                  → create()
# GET    /articles/{pk}/             → retrieve()
# PUT    /articles/{pk}/             → update()
# PATCH  /articles/{pk}/             → partial_update()
# DELETE /articles/{pk}/             → destroy()
# GET    /articles/featured/         → featured()
# POST   /articles/{pk}/publish/     → publish()
# GET    /articles/my_articles/      → my_articles()
```

---

## Decision Guide

**Use ViewSets when:**
- ✅ Building RESTful APIs with standard CRUD operations
- ✅ Want automatic URL routing via routers
- ✅ Need multiple custom actions beyond CRUD (@action)
- ✅ Want code organized by resource, not by operation

**Use Generic Views when:**
- ❌ Only need 1-2 operations (not full CRUD)
- ❌ Want explicit URL configuration
- ❌ Prefer organizing code by operation

**Use APIView when:**
- ❌ Non-standard API structure
- ❌ Complex business logic across multiple models

---

## See Also

- **[mixins.md](mixins.md)** - Building blocks of ViewSets
- **[generic-views.md](generic-views.md)** - Individual operation views
- **Routers skill** - Automatic URL configuration for ViewSets
