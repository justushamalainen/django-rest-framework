# Generic Views

Use Generic Views when you need 1-2 operations on a model (not full CRUD). For full CRUD, use ViewSets instead.

## When to Use Generic Views

✅ Single endpoint (no router needed)
✅ Explicit URL control
✅ 1-2 operations only
❌ Full CRUD (use ViewSet instead)

## Most Common Generic Views

| View | Operations | Use Case |
|------|------------|----------|
| **ListCreateAPIView** | GET, POST | Collection endpoint |
| **RetrieveUpdateDestroyAPIView** | GET, PUT, PATCH, DELETE | Detail endpoint |

## ListCreateAPIView - Collection Endpoint

**Most common pattern** for collection endpoints:

```python
from rest_framework.generics import ListCreateAPIView

class ArticleListCreateView(ListCreateAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    def get_queryset(self):
        # Filter by published status
        return Article.objects.filter(published=True)

    def perform_create(self, serializer):
        # Set author from request
        serializer.save(author=self.request.user)

# URL
path('articles/', ArticleListCreateView.as_view())

# HTTP Methods:
# GET    /articles/ → List articles
# POST   /articles/ → Create article
```

## RetrieveUpdateDestroyAPIView - Detail Endpoint

**Most common pattern** for detail endpoints:

```python
from rest_framework.generics import RetrieveUpdateDestroyAPIView

class ArticleDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    def perform_update(self, serializer):
        # Check ownership
        if serializer.instance.author != self.request.user:
            raise PermissionDenied("Not your article")
        serializer.save()

    def perform_destroy(self, instance):
        # Check ownership before delete
        if instance.author != self.request.user:
            raise PermissionDenied("Not your article")
        instance.delete()

# URL
path('articles/<int:pk>/', ArticleDetailView.as_view())

# HTTP Methods:
# GET    /articles/{pk}/ → Retrieve article
# PUT    /articles/{pk}/ → Full update
# PATCH  /articles/{pk}/ → Partial update
# DELETE /articles/{pk}/ → Delete article
```

---

## Common Customizations

```python
# Override get_queryset for filtering
def get_queryset(self):
    return Article.objects.filter(author=self.request.user)

# Override get_serializer_class for different serializers
def get_serializer_class(self):
    if self.request.method == 'GET':
        return ArticleDetailSerializer
    return ArticleSerializer

# Custom lookup field (slug instead of pk)
class ArticleBySlugView(RetrieveAPIView):
    lookup_field = 'slug'
```

## All Generic Views Reference

| View | Operations | Use When |
|------|------------|----------|
| ListAPIView | GET | List only |
| CreateAPIView | POST | Create only |
| RetrieveAPIView | GET (detail) | Read-only detail |
| UpdateAPIView | PUT, PATCH | Update only |
| DestroyAPIView | DELETE | Delete only |
| **ListCreateAPIView** | GET, POST | **Collection endpoint** |
| RetrieveUpdateAPIView | GET, PUT, PATCH | Detail (no delete) |
| RetrieveDestroyAPIView | GET, DELETE | Detail (no update) |
| **RetrieveUpdateDestroyAPIView** | GET, PUT, PATCH, DELETE | **Full detail CRUD** |

## See Also

- **[viewsets.md](viewsets.md)** - Recommended for full CRUD with routers
- **[apiview.md](apiview.md)** - For custom logic
