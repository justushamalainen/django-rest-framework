# Function-Based Views & Decorators

Use the `@api_view` decorator to write DRF views as functions instead of classes. Simpler syntax for simple endpoints.

## Overview

DRF's `@api_view` decorator converts a function into an APIView subclass, giving you all DRF features (authentication, permissions, content negotiation) in a function-based syntax.

**Source:** `rest_framework/decorators.py` (290 lines)

---

## @api_view Decorator

### Basic Usage

```python
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def hello_world(request):
    """Simple GET endpoint"""
    return Response({'message': 'Hello, World!'})

# URL
path('hello/', hello_world),
```

**Supported methods:** GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS

### Multiple HTTP Methods

```python
@api_view(['GET', 'POST'])
def article_list(request):
    """
    List articles or create new article.
    """
    if request.method == 'GET':
        articles = Article.objects.all()
        serializer = ArticleSerializer(articles, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = ArticleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

### Default Method

If no methods specified, defaults to `['GET']`:

```python
@api_view()  # Same as @api_view(['GET'])
def simple_view(request):
    return Response({'method': request.method})
```

---

## CRITICAL: Decorator Order

**Policy decorators MUST come AFTER (below) @api_view.**

### ❌ WRONG (Will Not Work!)

```python
# WRONG ORDER - Decorators won't work!
@permission_classes([IsAuthenticated])
@api_view(['GET'])
def my_view(request):
    return Response({'data': 'value'})
```

**Error:** Permission classes are applied before the view is converted to an APIView, so they have no effect.

### ✅ CORRECT

```python
# CORRECT ORDER
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_view(request):
    return Response({'data': 'value'})
```

**Rule:** `@api_view` ALWAYS comes first (top), then policy decorators below.

### Why Order Matters

```python
# Execution order (bottom to top):
# 1. Python reads bottom decorator first: @permission_classes
# 2. Then applies: @api_view
# 3. @api_view looks for attributes set by @permission_classes

# If @permission_classes is on top:
# - It runs before @api_view creates the APIView class
# - Attributes are set on the function, not the view
# - @api_view can't find them → ignored!
```

---

## Policy Decorators

### 1. @permission_classes

Control who can access the view.

```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def protected_view(request):
    """Only authenticated users can access"""
    return Response({'user': request.user.username})

@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def admin_only(request):
    """Only admin users can access"""
    return Response({'deleted': True})

@api_view(['GET'])
@permission_classes([])  # Override default permissions (allow anyone)
def public_view(request):
    return Response({'public': True})
```

### 2. @authentication_classes

Specify authentication methods.

```python
from rest_framework.decorators import api_view, authentication_classes
from rest_framework.authentication import TokenAuthentication, SessionAuthentication

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
def token_required(request):
    """Accepts only token authentication"""
    return Response({'authenticated_via': 'token'})

@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
def flexible_auth(request):
    """Accepts session OR token authentication"""
    return Response({'user': request.user.username})
```

### 3. @renderer_classes

Control response format.

```python
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer

@api_view(['GET'])
@renderer_classes([JSONRenderer])
def json_only(request):
    """Returns only JSON (no browsable API)"""
    return Response({'format': 'json'})

@api_view(['GET'])
@renderer_classes([TemplateHTMLRenderer])
def html_view(request):
    """Renders HTML template"""
    articles = Article.objects.all()
    return Response({'articles': articles}, template_name='articles.html')
```

### 4. @parser_classes

Control request body parsing.

```python
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser

@api_view(['POST'])
@parser_classes([JSONParser])
def json_only(request):
    """Accepts only JSON request bodies"""
    return Response({'received': request.data})

@api_view(['POST'])
@parser_classes([FormParser, MultiPartParser])
def file_upload(request):
    """Accepts form data and file uploads"""
    uploaded_file = request.FILES.get('file')
    return Response({'filename': uploaded_file.name if uploaded_file else None})
```

### 5. @throttle_classes

Apply rate limiting.

```python
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle

@api_view(['GET'])
@throttle_classes([UserRateThrottle])
def rate_limited(request):
    """Limited to X requests per hour (configured in settings)"""
    return Response({'message': 'Rate limited endpoint'})

@api_view(['POST'])
@throttle_classes([AnonRateThrottle])
def anonymous_limited(request):
    """Anonymous users have stricter limits"""
    return Response({'message': 'Created'})
```

### 6. @versioning_class

Specify API versioning.

```python
from rest_framework.decorators import api_view, versioning_class
from rest_framework.versioning import URLPathVersioning

@api_view(['GET'])
@versioning_class(URLPathVersioning)
def versioned_view(request):
    """Access version via request.version"""
    if request.version == '2.0':
        return Response({'version': '2.0', 'new_feature': True})
    return Response({'version': '1.0'})
```

### 7. @schema

Control schema generation for documentation.

```python
from rest_framework.decorators import api_view, schema
from rest_framework.schemas import AutoSchema

@api_view(['GET'])
@schema(None)  # Exclude from schema
def internal_view(request):
    return Response({'internal': True})

@api_view(['POST'])
@schema(AutoSchema())  # Custom schema
def documented_view(request):
    """
    Create a new item.

    Detailed description for auto-generated docs.
    """
    return Response({'created': True})
```

---

## Combining Multiple Decorators

### Example 1: Protected Endpoint

```python
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([UserRateThrottle])
def create_article(request):
    """
    Authenticated users can create articles (rate limited).
    """
    serializer = ArticleSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(author=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

### Example 2: Admin-Only JSON Endpoint

```python
@api_view(['DELETE'])
@permission_classes([IsAdminUser])
@renderer_classes([JSONRenderer])
@authentication_classes([TokenAuthentication])
def admin_delete(request, pk):
    """
    Admin-only deletion (token auth, JSON only).
    """
    article = get_object_or_404(Article, pk=pk)
    article.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
```

### Example 3: Public File Upload

```python
@api_view(['POST'])
@permission_classes([])  # Public
@parser_classes([MultiPartParser, FormParser])
@throttle_classes([AnonRateThrottle])
def public_upload(request):
    """
    Public file upload endpoint (rate limited for anon users).
    """
    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        return Response({'error': 'No file provided'}, status=400)

    # Process file...
    return Response({'filename': uploaded_file.name}, status=201)
```

---

## Complete CRUD Example: Function-Based Views

```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Article
from .serializers import ArticleSerializer

# List all articles or create new
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedOrReadOnly])
def article_list(request):
    """
    GET:  List all articles
    POST: Create new article
    """
    if request.method == 'GET':
        articles = Article.objects.filter(published=True)
        serializer = ArticleSerializer(articles, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = ArticleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Retrieve, update, or delete an article
@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticatedOrReadOnly])
def article_detail(request, pk):
    """
    GET:    Retrieve article
    PUT:    Full update
    PATCH:  Partial update
    DELETE: Delete article
    """
    article = get_object_or_404(Article, pk=pk)

    if request.method == 'GET':
        serializer = ArticleSerializer(article)
        return Response(serializer.data)

    elif request.method in ['PUT', 'PATCH']:
        # Check ownership
        if article.author != request.user:
            return Response(
                {'error': 'You can only edit your own articles'},
                status=status.HTTP_403_FORBIDDEN
            )

        partial = request.method == 'PATCH'
        serializer = ArticleSerializer(article, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        # Check ownership
        if article.author != request.user:
            return Response(
                {'error': 'You can only delete your own articles'},
                status=status.HTTP_403_FORBIDDEN
            )

        article.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Custom action endpoint
@api_view(['POST'])
@permission_classes([IsAuthenticatedOrReadOnly])
def publish_article(request, pk):
    """
    POST: Publish an article
    """
    article = get_object_or_404(Article, pk=pk)

    if article.author != request.user:
        return Response(
            {'error': 'You can only publish your own articles'},
            status=status.HTTP_403_FORBIDDEN
        )

    article.published = True
    article.published_at = timezone.now()
    article.save()

    return Response({'status': 'published'})


# URLs
from django.urls import path

urlpatterns = [
    path('articles/', article_list, name='article-list'),
    path('articles/<int:pk>/', article_detail, name='article-detail'),
    path('articles/<int:pk>/publish/', publish_article, name='article-publish'),
]
```

---

## Request and Response Objects

### Request Object

Same as class-based views:

```python
@api_view(['GET', 'POST'])
def example(request):
    # DRF Request attributes
    request.data              # Parsed request body
    request.query_params      # GET parameters (better name than request.GET)
    request.user              # Authenticated user
    request.auth              # Auth token/credentials
    request.method            # 'GET', 'POST', etc.
    request.content_type      # 'application/json', etc.

    # Django HttpRequest attributes still available
    request.META              # HTTP headers
    request.FILES             # Uploaded files
    request.GET               # Query string
    request.POST              # Form data
```

### Response Object

```python
from rest_framework.response import Response
from rest_framework import status

@api_view(['POST'])
def example(request):
    # Simple response
    return Response({'key': 'value'})

    # With status code
    return Response({'created': True}, status=status.HTTP_201_CREATED)

    # With headers
    return Response(
        {'data': 'value'},
        headers={'X-Custom-Header': 'Value'}
    )

    # Error response
    return Response(
        {'error': 'Invalid input'},
        status=status.HTTP_400_BAD_REQUEST
    )
```

---

## When to Use Function-Based Views

### Use FBV (@api_view) when:

✅ **Simple, one-off endpoints**
```python
@api_view(['GET'])
def health_check(request):
    return Response({'status': 'ok'})
```

✅ **Single HTTP method**
```python
@api_view(['POST'])
def send_notification(request):
    # Simple POST endpoint
    pass
```

✅ **Complex conditional logic**
```python
@api_view(['POST'])
def complex_workflow(request):
    if condition_a:
        # Do A
    elif condition_b:
        # Do B
    else:
        # Do C
    return Response(...)
```

✅ **Rapid prototyping**
- Faster to write
- Less boilerplate
- Easy to understand

### Use Class-Based Views when:

❌ **Standard CRUD operations** → Use Generic Views or ViewSets

❌ **Need to share logic across multiple methods** → Use class methods

❌ **Want automatic URL routing** → Use ViewSets with routers

❌ **Need inheritance/mixins** → Use class-based views

---

## Comparison: FBV vs CBV

### Same Endpoint, Two Styles

**Function-Based:**
```python
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedOrReadOnly])
def article_list(request):
    if request.method == 'GET':
        articles = Article.objects.all()
        serializer = ArticleSerializer(articles, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = ArticleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(author=request.user)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
```

**Class-Based (Generic View):**
```python
class ArticleListView(ListCreateAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
```

**Class-based is shorter and clearer for standard CRUD!**

---

## Common Patterns

### Pattern 1: Validation Helper

```python
def validate_article_ownership(article, user):
    """Helper function for ownership checks"""
    if article.author != user:
        raise PermissionDenied("You don't own this article")

@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def article_modify(request, pk):
    article = get_object_or_404(Article, pk=pk)
    validate_article_ownership(article, request.user)

    if request.method == 'PUT':
        # Update logic
        pass
    elif request.method == 'DELETE':
        article.delete()
        return Response(status=204)
```

### Pattern 2: Shared Logic

```python
def get_user_articles(user, published_only=False):
    """Helper to get articles for a user"""
    queryset = Article.objects.filter(author=user)
    if published_only:
        queryset = queryset.filter(published=True)
    return queryset

@api_view(['GET'])
def my_articles(request):
    articles = get_user_articles(request.user)
    serializer = ArticleSerializer(articles, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def my_published_articles(request):
    articles = get_user_articles(request.user, published_only=True)
    serializer = ArticleSerializer(articles, many=True)
    return Response(serializer.data)
```

### Pattern 3: Exception Handling

```python
from rest_framework.exceptions import ValidationError, NotFound

@api_view(['POST'])
def create_article(request):
    # Validate business rules
    if Article.objects.filter(
        author=request.user,
        published=False
    ).count() >= 5:
        raise ValidationError("You have too many unpublished drafts")

    serializer = ArticleSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(author=request.user)
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)
```

---

## Troubleshooting

### Problem: Policy decorators not working

**Symptom:** Permissions/authentication ignored

**Solution:** Check decorator order! `@api_view` must be first.

```python
# ❌ WRONG
@permission_classes([IsAuthenticated])
@api_view(['GET'])

# ✅ CORRECT
@api_view(['GET'])
@permission_classes([IsAuthenticated])
```

---

### Problem: "Method not allowed" error

**Symptom:** 405 Method Not Allowed

**Solution:** Add the HTTP method to @api_view list

```python
# If you get 405 on POST:
@api_view(['GET'])  # ❌ Missing POST!
def my_view(request):
    if request.method == 'POST':  # Never reached!
        pass

# Fix:
@api_view(['GET', 'POST'])  # ✅ Include all methods
def my_view(request):
    if request.method == 'POST':
        pass
```

---

## See Also

- **[apiview.md](apiview.md)** - Class-based equivalent
- **[viewsets.md](viewsets.md)** - Higher-level patterns
- **Permission skill** - Detailed permission classes
- **Authentication skill** - Authentication backends
