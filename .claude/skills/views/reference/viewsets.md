# ViewSets - The Recommended Approach

**ViewSets are the recommended approach for 90% of APIs.** They provide full CRUD with minimal code and automatic URL routing via routers.

## Why ViewSets?

✅ Automatic URL routing (no manual path() needed)
✅ Minimal code (3-10 lines for full CRUD)
✅ Easy to add custom actions with @action decorator
✅ Organized by resource, not by operation

## ViewSet Types

| Type | Actions | Use Case |
|------|---------|----------|
| **ModelViewSet** | Full CRUD (list, create, retrieve, update, destroy) | 90% of use cases |
| **ReadOnlyModelViewSet** | list, retrieve | Public read-only APIs |
| GenericViewSet + mixins | Custom combination | Special cases |

## ModelViewSet - Start Here

**This is what you'll use 90% of the time.** Provides full CRUD in 3-10 lines of code:

```python
from rest_framework.viewsets import ModelViewSet

class ArticleViewSet(ModelViewSet):
    """Minimal full CRUD API"""
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

# Router setup
from rest_framework.routers import DefaultRouter
router = DefaultRouter()
router.register(r'articles', ArticleViewSet)
urlpatterns = router.urls

# Automatically generates:
# GET    /articles/          → list()
# POST   /articles/          → create()
# GET    /articles/{pk}/     → retrieve()
# PUT    /articles/{pk}/     → update()
# PATCH  /articles/{pk}/     → partial_update()
# DELETE /articles/{pk}/     → destroy()
```

### Common Customizations

```python
class ArticleViewSet(ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    # Filter queryset
    def get_queryset(self):
        if self.action == 'list':
            return Article.objects.filter(published=True)
        return Article.objects.all()

    # Set author on create
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    # Check ownership on update
    def perform_update(self, serializer):
        if serializer.instance.author != self.request.user:
            raise PermissionDenied("Not your article")
        serializer.save()

    # Check ownership on delete
    def perform_destroy(self, instance):
        if instance.author != self.request.user:
            raise PermissionDenied("Not your article")
        instance.delete()
```

---

## @action Decorator - Custom Endpoints

Add custom endpoints beyond CRUD:

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
        Collection action (detail=False)
        """
        recent = Article.objects.order_by('-created_at')[:10]
        serializer = self.get_serializer(recent, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """
        POST /articles/{pk}/publish/
        Detail action (detail=True) - MUST include pk parameter!
        """
        article = self.get_object()
        article.published = True
        article.save()
        return Response({'status': 'published'})
```

### @action Parameters

```python
@action(
    detail=True,                    # True = /resource/{pk}/action/, False = /resource/action/
    methods=['get', 'post'],        # HTTP methods
    permission_classes=[...],       # Override viewset permissions
    url_path='custom-path',         # Custom URL (default: function name)
)
def my_action(self, request, pk=None):  # IMPORTANT: pk=None for detail=True
    pass
```

### More @action Examples

```python
# Override permissions for specific action
@action(detail=False, permission_classes=[AllowAny])
def public_feed(self, request):
    """Public endpoint (no auth)"""
    articles = Article.objects.filter(public=True)[:20]
    serializer = self.get_serializer(articles, many=True)
    return Response(serializer.data)

# Custom URL path
@action(detail=False, url_path='my-articles')
def user_articles(self, request):
    """GET /articles/my-articles/"""
    articles = Article.objects.filter(author=request.user)
    serializer = self.get_serializer(articles, many=True)
    return Response(serializer.data)

# Multiple HTTP methods
@action(detail=True, methods=['get', 'post', 'delete'])
def comments(self, request, pk=None):
    """Manage comments on an article"""
    article = self.get_object()
    if request.method == 'GET':
        comments = article.comments.all()
        return Response(CommentSerializer(comments, many=True).data)
    elif request.method == 'POST':
        # Create comment
        pass
    elif request.method == 'DELETE':
        # Delete comments
        pass
```

---

## Advanced Customizations

```python
class ArticleViewSet(ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    # Action-based queryset filtering
    def get_queryset(self):
        if self.action == 'list':
            return Article.objects.filter(published=True)
        return Article.objects.all()

    # Action-based serializer selection
    def get_serializer_class(self):
        if self.action == 'list':
            return ArticleListSerializer  # Lighter
        elif self.action == 'retrieve':
            return ArticleDetailSerializer  # Full details
        return ArticleSerializer

    # Action-based permissions
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]
```

---

## Complete Example

```python
# views.py
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly

class ArticleViewSet(ModelViewSet):
    """Full CRUD + custom actions"""
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        article = self.get_object()
        article.published = True
        article.save()
        return Response({'status': 'published'})

    @action(detail=False)
    def my_articles(self, request):
        articles = Article.objects.filter(author=request.user)
        serializer = self.get_serializer(articles, many=True)
        return Response(serializer.data)

# urls.py
from rest_framework.routers import DefaultRouter
router = DefaultRouter()
router.register(r'articles', ArticleViewSet)
urlpatterns = router.urls
```

---

## ReadOnlyModelViewSet

For read-only APIs (list + retrieve only):

```python
from rest_framework.viewsets import ReadOnlyModelViewSet

class ArticleViewSet(ReadOnlyModelViewSet):
    """Public read-only API"""
    queryset = Article.objects.filter(published=True)
    serializer_class = ArticleSerializer

# Provides only:
# GET /articles/     → list()
# GET /articles/{pk}/ → retrieve()
```

---

## See Also

- **[generic-views.md](generic-views.md)** - For single endpoints without routers
- **[apiview.md](apiview.md)** - For custom logic
