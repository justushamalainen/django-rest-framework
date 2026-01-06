---
version: 1.0
last_updated: 2026-01-06
difficulty: beginner-to-intermediate
keywords: views, apiview, generic-views, viewsets, mixins, function-based-views, decorators
dependencies:
  - djangorestframework>=3.14
  - django>=3.2
prerequisites:
  - Basic understanding of Django views
  - Familiarity with HTTP methods (GET, POST, PUT, PATCH, DELETE)
  - Knowledge of serializers (see serializers skill)
source_files:
  - rest_framework/views.py
  - rest_framework/generics.py
  - rest_framework/viewsets.py
  - rest_framework/mixins.py
  - rest_framework/decorators.py
---

# Django REST Framework Views

Master DRF's view layer: from low-level APIView to powerful ViewSets. Learn when to use each pattern and how to build efficient, maintainable APIs.

## What You'll Learn

After completing this skill, you will be able to:

- **Choose the right view pattern** for your use case using a decision tree
- **Build API endpoints** with APIView for maximum control
- **Use Generic Views** to reduce boilerplate for CRUD operations
- **Leverage ViewSets** with routers for automatic URL configuration
- **Compose mixins** to create custom behavior combinations
- **Write function-based views** with the @api_view decorator
- **Apply policy decorators** in the correct order (critical!)
- **Use @action decorators** to add custom endpoints to ViewSets
- **Override perform_* hooks** for custom create/update/delete logic
- **Understand the request/response cycle** in DRF views

## Before You Start

You should understand:
- Django models and querysets
- DRF serializers (create/update/validate)
- HTTP methods and REST conventions
- Basic Python class inheritance

## Quick Start: Your First APIView

The most basic DRF view - full control, but you write everything:

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Article
from .serializers import ArticleSerializer

class ArticleListView(APIView):
    """
    List all articles or create a new article.
    """
    def get(self, request):
        """GET /api/articles/"""
        articles = Article.objects.all()
        serializer = ArticleSerializer(articles, many=True)
        return Response(serializer.data)

    def post(self, request):
        """POST /api/articles/"""
        serializer = ArticleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ArticleDetailView(APIView):
    """
    Retrieve, update or delete an article.
    """
    def get_object(self, pk):
        try:
            return Article.objects.get(pk=pk)
        except Article.DoesNotExist:
            raise Http404

    def get(self, request, pk):
        """GET /api/articles/{pk}/"""
        article = self.get_object(pk)
        serializer = ArticleSerializer(article)
        return Response(serializer.data)

    def put(self, request, pk):
        """PUT /api/articles/{pk}/"""
        article = self.get_object(pk)
        serializer = ArticleSerializer(article, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """DELETE /api/articles/{pk}/"""
        article = self.get_object(pk)
        article.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
```

**URL configuration:**
```python
from django.urls import path
from .views import ArticleListView, ArticleDetailView

urlpatterns = [
    path('articles/', ArticleListView.as_view()),
    path('articles/<int:pk>/', ArticleDetailView.as_view()),
]
```

## Decision Tree: Choosing the Right View Pattern

Use this tree to pick the right view type for your needs:

```
START: What are you building?

├─ Question 1: Do you need complete custom control?
│  └─ YES → Use APIView
│     - Custom business logic
│     - Multiple models in one endpoint
│     - Non-standard HTTP behavior
│     - See: reference/apiview.md
│
├─ Question 2: Is this a simple CRUD operation on ONE model?
│  │
│  ├─ YES → Question 3: Do you need custom behavior?
│  │  │
│  │  ├─ NO → Use Generic Views (ListAPIView, CreateAPIView, etc.)
│  │  │  - Standard list/create/retrieve/update/delete
│  │  │  - Minimal code, maximum readability
│  │  │  - See: reference/generic-views.md
│  │  │
│  │  └─ YES → Question 4: How much customization?
│  │     │
│  │     ├─ MINOR (override 1-2 methods) → Use Generic Views
│  │     │  - Override get_queryset(), get_serializer_class()
│  │     │  - Override perform_create(), perform_update()
│  │     │
│  │     └─ MAJOR (custom logic per method) → Use APIView + GenericAPIView
│  │        - Inherit from GenericAPIView for helpers
│  │        - Manually implement each HTTP method
│  │
│  └─ NO → Question 5: Are you exposing a collection with standard CRUD?
│     │
│     ├─ YES → Use ViewSets with Router
│     │  - Automatic URL routing
│     │  - ModelViewSet for full CRUD
│     │  - ReadOnlyModelViewSet for read-only
│     │  - Add custom actions with @action decorator
│     │  - See: reference/viewsets.md
│     │
│     └─ NO → Question 6: Is this a function-based approach?
│        │
│        ├─ YES → Use @api_view decorator
│        │  - Simple, straightforward
│        │  - Good for one-off endpoints
│        │  - See: reference/decorators-fbv.md
│        │
│        └─ NO → Back to APIView for full control

EXAMPLES:
- Blog CRUD → ModelViewSet (automatic URLs)
- Public article list → ListAPIView (read-only, one operation)
- User profile with multiple related data → APIView (custom logic)
- Simple status endpoint → @api_view(['GET'])
- Reports combining multiple models → APIView
```

## Common Mistakes & How to Fix Them

### Mistake 1: Evaluating queryset at class level

**Wrong:**
```python
class ArticleListView(ListAPIView):
    queryset = Article.objects.all()  # Evaluated once at startup!
    serializer_class = ArticleSerializer
```

**Why it fails:** The queryset is evaluated once when the module loads. New objects won't appear, caching issues arise.

**✅ Correct:**
```python
class ArticleListView(ListAPIView):
    queryset = Article.objects.all()  # OK - DRF calls .all() internally
    # OR override get_queryset():
    def get_queryset(self):
        return Article.objects.all()  # Evaluated per request
```

**Note:** For class-level querysets, DRF automatically calls `.all()` on each request. But for custom filtering, always override `get_queryset()`.

---

### Mistake 2: Wrong decorator order for function-based views

**Wrong:**
```python
@permission_classes([IsAuthenticated])  # Applied first!
@api_view(['GET'])
def my_view(request):
    return Response({'message': 'Hello'})
```

**Why it fails:** Policy decorators (@permission_classes, @authentication_classes, etc.) MUST come AFTER @api_view. Wrong order → decorators don't work!

**✅ Correct:**
```python
@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Applied after @api_view
def my_view(request):
    return Response({'message': 'Hello'})
```

**Rule:** @api_view ALWAYS comes first (top), policy decorators come after (below).

---

### Mistake 3: Forgetting to call super() in dispatch/get_queryset

**Wrong:**
```python
class ArticleViewSet(ModelViewSet):
    def get_queryset(self):
        # No super() call
        return Article.objects.filter(author=self.request.user)
```

**Why it fails:** May work initially but breaks filtering, pagination, or other features that rely on parent behavior.

**✅ Correct:**
```python
class ArticleViewSet(ModelViewSet):
    queryset = Article.objects.all()

    def get_queryset(self):
        # Let parent handle base logic
        queryset = super().get_queryset()
        # Then customize
        return queryset.filter(author=self.request.user)
```

---

### Mistake 4: Using detail=True action without pk in URL

**Wrong:**
```python
class ArticleViewSet(ModelViewSet):
    @action(detail=True, methods=['post'])
    def publish(self, request):
        # Where's the article? Need pk!
        return Response({'status': 'published'})
```

**Why it fails:** `detail=True` means "operates on a single object", but you need to retrieve it!

**✅ Correct:**
```python
class ArticleViewSet(ModelViewSet):
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        article = self.get_object()  # Gets the article by pk
        article.published = True
        article.save()
        return Response({'status': 'published'})
```

---

### Mistake 5: Not returning Response objects

**Wrong:**
```python
class ArticleView(APIView):
    def get(self, request):
        articles = Article.objects.all()
        return articles  # Not a Response!
```

**Why it fails:** DRF expects Response objects. Returning raw data breaks rendering, content negotiation.

**✅ Correct:**
```python
class ArticleView(APIView):
    def get(self, request):
        articles = Article.objects.all()
        serializer = ArticleSerializer(articles, many=True)
        return Response(serializer.data)  # Always return Response
```

---

### Mistake 6: Overriding create/update instead of perform_create/perform_update

**Wrong (but works):**
```python
class ArticleViewSet(ModelViewSet):
    def create(self, request):
        # Reimplementing all the logic!
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(author=request.user)  # Just needed this!
        return Response(serializer.data, status=201)
```

**Why it's suboptimal:** You're reimplementing all of DRF's create logic just to add `author=request.user`.

**✅ Correct:**
```python
class ArticleViewSet(ModelViewSet):
    def perform_create(self, serializer):
        # Just customize the save step
        serializer.save(author=self.request.user)
```

**Rule:** Override `perform_*` methods for simple customization. Override `create/update/destroy` only for major changes.

## View Types Overview

| View Type | Use Case | LOC Required | Flexibility |
|-----------|----------|--------------|-------------|
| **APIView** | Custom logic, non-standard APIs | High (50-100+) | Maximum |
| **Generic Views** | Single CRUD operation | Low (3-5) | Medium |
| **ViewSets** | Full CRUD + custom actions | Low (5-15) | High |
| **@api_view** | Simple function-based endpoint | Minimal (10-20) | Medium |
| **Mixins** | Compose custom behavior | Medium (20-40) | High |

## Reference Files

Dive deeper into each view type:

1. **[reference/apiview.md](reference/apiview.md)** - Base APIView class, request/response cycle, policy classes
2. **[reference/generic-views.md](reference/generic-views.md)** - All 9 generic views with examples
3. **[reference/viewsets.md](reference/viewsets.md)** - ViewSets, ModelViewSet, @action decorator patterns
4. **[reference/mixins.md](reference/mixins.md)** - All 5 mixins and perform_* hooks
5. **[reference/decorators-fbv.md](reference/decorators-fbv.md)** - Function-based views and policy decorators
6. **[reference/examples/view-patterns.py](reference/examples/view-patterns.py)** - Working code for all patterns

## Next Steps

After mastering views:
1. **Routers** - Automatic URL routing for ViewSets
2. **Permissions** - Controlling access to views
3. **Authentication** - Identifying users in views
4. **Testing** - Writing tests for your views

## Troubleshooting

**Q: "get_object() returned None" error?**
A: Check your `lookup_field` matches your URL pattern. Default is `pk`.

**Q: Custom action not appearing in router URLs?**
A: Ensure @action decorator has `detail=True` or `detail=False` set.

**Q: Serializer validation errors not showing?**
A: Are you calling `serializer.is_valid(raise_exception=True)`?

**Q: Pagination not working on ViewSet?**
A: Check `DEFAULT_PAGINATION_CLASS` in settings and that you're returning from `.list()`.

**Q: Permission denied on safe method?**
A: Check `has_permission()` vs `has_object_permission()` - they're both called!

## Additional Resources

- **DRF Source:** `/rest_framework/views.py`, `generics.py`, `viewsets.py`
- **Official Docs:** https://www.django-rest-framework.org/api-guide/views/
- **Tutorial:** Complete DRF tutorial parts 1-3 for hands-on practice
