---
version: 1.0
last_updated: 2026-01-06
difficulty: beginner-to-intermediate
keywords: views, apiview, generic-views, viewsets, routers
dependencies:
  - djangorestframework>=3.14
  - django>=3.2
prerequisites:
  - Basic understanding of Django views
  - Familiarity with HTTP methods (GET, POST, PUT, PATCH, DELETE)
  - Knowledge of serializers
source_files:
  - rest_framework/viewsets.py
  - rest_framework/generics.py
  - rest_framework/views.py
---

# Django REST Framework Views

Master DRF views to build RESTful APIs efficiently. Learn when to use ViewSets (90% of cases) versus Generic Views or APIView.

## What You'll Learn

- **Choose the right view pattern** using a simple decision tree
- **Build ViewSets** with routers for automatic URL configuration (recommended)
- **Use @action decorator** to add custom endpoints to ViewSets
- **Override perform_* hooks** for custom create/update/delete logic
- **Fall back to Generic Views or APIView** when needed for custom logic

## Quick Start: ViewSet (Recommended)

**ViewSets are the recommended approach for 90% of use cases.** They provide full CRUD with minimal code and automatic URL routing:

```python
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Article
from .serializers import ArticleSerializer

class ArticleViewSet(ModelViewSet):
    """
    Full CRUD API for articles.
    Provides: list, create, retrieve, update, partial_update, destroy
    """
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    def perform_create(self, serializer):
        # Set author from request user
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """POST /articles/{pk}/publish/ - Custom action"""
        article = self.get_object()
        article.published = True
        article.save()
        return Response({'status': 'published'})

# Automatic URL routing with router
from rest_framework.routers import DefaultRouter
router = DefaultRouter()
router.register(r'articles', ArticleViewSet)
urlpatterns = router.urls

# Generated URLs:
# GET    /articles/          → list()
# POST   /articles/          → create()
# GET    /articles/{pk}/     → retrieve()
# PUT    /articles/{pk}/     → update()
# PATCH  /articles/{pk}/     → partial_update()
# DELETE /articles/{pk}/     → destroy()
# POST   /articles/{pk}/publish/ → publish()
```

## Decision Tree: Choosing the Right View Pattern

**Start here and follow the questions:**

```
Question 1: Are you building standard CRUD operations on a model?
│
├─ YES → Use ViewSet (ModelViewSet or ReadOnlyModelViewSet)
│  ✅ Automatic URL routing with routers
│  ✅ Minimal code (3-5 lines for full CRUD)
│  ✅ Easy to add custom actions with @action decorator
│  ✅ Override perform_* hooks for custom save logic
│  → See: reference/viewsets.md
│
└─ NO → Question 2: Do you need just 1-2 operations (not full CRUD)?
   │
   ├─ YES → Use Generic Views
   │  ✅ ListCreateAPIView for collection endpoints
   │  ✅ RetrieveUpdateDestroyAPIView for detail endpoints
   │  ✅ Explicit URL patterns
   │  → See: reference/generic-views.md
   │
   └─ NO → Use APIView
      ✅ Complete custom control
      ✅ Multiple models in one endpoint
      ✅ Non-standard REST patterns
      → See: reference/apiview.md

EXAMPLES:
✅ Blog CRUD → ModelViewSet (90% of use cases)
✅ Read-only public API → ReadOnlyModelViewSet
✅ Single list endpoint → ListAPIView
✅ Complex multi-model query → APIView
```

## Common Mistakes & How to Fix Them

### Mistake 1: Using detail=True action without pk

**Wrong:**
```python
@action(detail=True, methods=['post'])
def publish(self, request):
    # Where's the article? Missing pk parameter!
    return Response({'status': 'published'})
```

**✅ Correct:**
```python
@action(detail=True, methods=['post'])
def publish(self, request, pk=None):
    article = self.get_object()  # Gets article by pk
    article.published = True
    article.save()
    return Response({'status': 'published'})
```

---

### Mistake 2: Overriding create() instead of perform_create()

**Wrong:**
```python
def create(self, request):
    # Reimplementing all DRF logic just to set author!
    serializer = self.get_serializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(author=request.user)
    return Response(serializer.data, status=201)
```

**✅ Correct:**
```python
def perform_create(self, serializer):
    # Just customize the save step
    serializer.save(author=self.request.user)
```

**Rule:** Override `perform_create/perform_update/perform_destroy` for simple customization.

---

### Mistake 3: Not returning Response objects

**Wrong:**
```python
def get(self, request):
    return Article.objects.all()  # Not a Response!
```

**✅ Correct:**
```python
def get(self, request):
    articles = Article.objects.all()
    serializer = ArticleSerializer(articles, many=True)
    return Response(serializer.data)
```

## View Types Quick Reference

| View Type | Use Case | Code | When to Use |
|-----------|----------|------|-------------|
| **ModelViewSet** | Full CRUD + router | 3-10 lines | 90% of use cases |
| **ReadOnlyModelViewSet** | Read-only API | 3 lines | Public APIs |
| **ListCreateAPIView** | List + Create | 3-5 lines | Single endpoint, no router |
| **RetrieveUpdateDestroyAPIView** | Detail CRUD | 3-5 lines | Single detail endpoint |
| **APIView** | Custom logic | 20-50+ lines | Complex non-REST patterns |

## ModelViewSet Quick Reference

```python
class ArticleViewSet(ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    # Common overrides:
    def get_queryset(self):
        return Article.objects.filter(author=self.request.user)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post'])
    def custom_action(self, request, pk=None):
        obj = self.get_object()
        # Your logic here
        return Response({'status': 'ok'})
```

## Reference Files

- **[reference/viewsets.md](reference/viewsets.md)** - Complete ViewSet guide (ModelViewSet, @action decorator)
- **[reference/generic-views.md](reference/generic-views.md)** - Generic views for single endpoints
- **[reference/apiview.md](reference/apiview.md)** - APIView for custom logic

## Next Steps

1. **Routers skill** - Automatic URL configuration for ViewSets
2. **Permissions skill** - Controlling access to views
3. **Authentication skill** - Identifying users
