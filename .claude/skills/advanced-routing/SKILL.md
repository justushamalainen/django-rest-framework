# Advanced Routing

**⚠️ SPECIAL CASES ONLY** - Most DRF APIs don't need custom or nested routers.

Use this skill only when standard `DefaultRouter` + `@action` decorators are insufficient.

---

## When You DON'T Need This

**Use standard routing instead if:**
- You need a few extra endpoints → Use `@action` decorator
- You want custom endpoint names → Override `basename` in router
- You need filtering by parent → Use query parameters (`/books/?author=1`)
- You have simple CRUD operations → Use `ModelViewSet` + `DefaultRouter`

**90% of DRF APIs work fine with:**
```python
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'books', BookViewSet)
router.register(r'authors', AuthorViewSet)

# Custom endpoints? Use @action
class BookViewSet(viewsets.ModelViewSet):
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        ...
```

---

## When You DO Need This

### Custom Routers (reference/custom-routers.md)

**Use when you need:**
- Non-standard URL patterns across ALL ViewSets (bulk endpoints, export, etc.)
- Organization-wide URL conventions
- Legacy URL compatibility requirements
- Custom root API view with metadata

**Don't use when:**
- Only one ViewSet needs the feature → Use `@action` instead
- You can achieve it with query parameters

### Nested Routing (reference/nested-routing.md)

**Use when:**
- Parent-child relationships are fundamental (`/authors/1/books/`)
- Operations ALWAYS require parent context
- Maximum 2 levels of nesting

**Don't use when:**
- Nesting would be 3+ levels deep
- Resources can be accessed independently
- Query parameters work (`/books/?author=1`)

---

## Quick Decision

```
Do I need custom endpoints?
├── Just one ViewSet? → @action decorator (see views skill)
├── All ViewSets? → Custom Router (→ custom-routers.md)
└── Neither? → DefaultRouter is fine

Do I need parent-child URLs?
├── /parents/1/children/ style required? → Nested Router (→ nested-routing.md)
├── /children/?parent=1 acceptable? → Use filtering (see pagination-filtering skill)
└── Neither? → Flat URLs are simpler
```

---

## Reference Files

| File | Lines | Use Case |
|------|-------|----------|
| [custom-routers.md](reference/custom-routers.md) | ~900 | Custom router classes with new routes |
| [nested-routing.md](reference/nested-routing.md) | ~770 | Parent-child URL patterns |

---

## Common Patterns (Quick Reference)

### Add Route to All ViewSets

```python
from rest_framework.routers import SimpleRouter, Route

class BulkRouter(SimpleRouter):
    routes = [
        *SimpleRouter.routes,
        Route(
            url=r'^{prefix}/bulk{trailing_slash}$',
            mapping={'post': 'bulk_create', 'delete': 'bulk_destroy'},
            name='{basename}-bulk',
            detail=False,
            initkwargs={}
        ),
    ]
```

### Basic Nested Routing

```python
# Option 1: Manual (no dependencies)
urlpatterns = [
    path('authors/<int:author_pk>/books/',
         BookViewSet.as_view({'get': 'list', 'post': 'create'})),
]

# Option 2: drf-nested-routers package
from rest_framework_nested import routers
nested = routers.NestedDefaultRouter(router, r'authors', lookup='author')
nested.register(r'books', BookViewSet, basename='author-books')
```

### ViewSet for Nested Routes

```python
class BookViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        qs = Book.objects.all()
        author_pk = self.kwargs.get('author_pk')
        if author_pk:
            qs = qs.filter(author_id=author_pk)
        return qs

    def perform_create(self, serializer):
        author_pk = self.kwargs.get('author_pk')
        if author_pk:
            serializer.save(author_id=author_pk)
        else:
            serializer.save()
```

---

## Best Practices

1. **Prefer simplicity** - Start with `DefaultRouter`, add complexity only when needed
2. **Limit nesting to 2 levels** - Deeper nesting hurts usability
3. **Provide multiple access paths** - Both `/authors/1/books/` and `/books/?author=1`
4. **Document your URL structure** - Custom routing isn't obvious
5. **Test URL generation** - Print `router.urls` to verify patterns

---

## Related Skills

- **routers** - Standard routing patterns (start here)
- **views** - ViewSets and `@action` decorator
- **pagination-filtering** - Query parameter filtering alternative
