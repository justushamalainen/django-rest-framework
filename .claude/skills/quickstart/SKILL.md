---
version: 1.0
last_updated: 2026-01-06
difficulty: beginner
keywords: quickstart, getting-started, installation, first-api, setup
dependencies: djangorestframework>=3.14, django>=4.2
estimated_time: 5-30 minutes (path-dependent)
---

# Django REST Framework Quickstart

## What You'll Learn

By completing this quickstart, you will:

- Set up a Django project with Django REST Framework
- Create your first working REST API in under 5 minutes
- Understand the three core DRF components: Serializers, Views, and URLs
- Choose the right approach for your project (beginner vs production)
- Avoid the 10+ most common pitfalls when starting with DRF
- Know which settings are essential and which are optional

## Before You Start

### Prerequisites

**Required Knowledge:**
- Python basics (functions, classes, decorators)
- HTTP fundamentals (GET, POST, PUT, DELETE)
- Basic Django understanding (models, views, URLs)

**If you're new to Django:** Complete the [official Django tutorial parts 1-4](https://docs.djangoproject.com/en/stable/intro/tutorial01/) first. DRF builds on Django concepts.

**System Requirements:**
- Python 3.8+ installed
- pip or poetry for package management
- A text editor or IDE

### Installation

```bash
# Create a virtual environment (recommended)
python3 -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate

# Install Django and DRF
pip install django djangorestframework

# Verify installation
python -c "import rest_framework; print(rest_framework.VERSION)"
```

---

## Choose Your Path

Select the path that matches your experience level and project needs:

### PATH A: Absolute Beginner (5 minutes)
**Best for:** First-time DRF users, learning, quick demos
**Uses:** Built-in User model, minimal configuration
**Result:** Working API with zero custom code

### PATH B: Real Project (15 minutes)
**Best for:** Most applications, production-bound projects
**Uses:** Custom models, authentication, proper structure
**Result:** Production-ready foundation

### PATH C: Production API (30 minutes)
**Best for:** Enterprise apps, APIs with special requirements
**Uses:** Full configuration, pagination, throttling, versioning
**Result:** Complete production setup

---

## PATH A: Absolute Beginner (5 Minutes)

### Step 1: Create Django Project

```bash
# Create project directory
mkdir myapi && cd myapi

# Start Django project
django-admin startproject config .

# Create an app
python manage.py startapp api
```

### Step 2: Configure Settings

Edit `config/settings.py`:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',  # Add DRF
    'api',             # Add your app
]

# Essential DRF settings
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}
```

### Step 3: Create Serializers

Create `api/serializers.py`:

```python
from django.contrib.auth.models import User
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']
```

### Step 4: Create Views

Edit `api/views.py`:

```python
from django.contrib.auth.models import User
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from api.serializers import UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and editing users.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
```

### Step 5: Configure URLs

Edit `config/urls.py`:

```python
from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from api.views import UserViewSet

# Create router and register viewsets
router = routers.DefaultRouter()
router.register(r'users', UserViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),  # Login for browsable API
]
```

### Step 6: Initialize Database and Test

```bash
# Create database tables
python manage.py migrate

# Create a test user
python manage.py createsuperuser --username admin --email admin@example.com

# Start development server
python manage.py runserver
```

### Step 7: Test Your API

Open your browser to: `http://127.0.0.1:8000/api/users/`

You should see the browsable API interface. Log in with your superuser credentials.

**Test with curl:**

```bash
# Get list of users
curl -u admin:password http://127.0.0.1:8000/api/users/

# Create a new user
curl -u admin:password -X POST http://127.0.0.1:8000/api/users/ \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"testpass123"}'
```

**Congratulations!** You have a working REST API.

**Next Steps:** Learn about [serializers](../serializers/SKILL.md) and [views](../views/SKILL.md) to customize your API.

---

## PATH B: Real Project (15 Minutes)

This path creates a blog API with custom models, authentication, and proper permissions.

### Step 1: Project Setup

```bash
# Create project
mkdir blogapi && cd blogapi
django-admin startproject config .
python manage.py startapp blog
```

### Step 2: Configure Settings

See [reference/settings-reference.md](reference/settings-reference.md) for all options.

Edit `config/settings.py`:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',  # Token authentication
    'blog',
]

REST_FRAMEWORK = {
    # Authentication
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    # Permissions
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    # Pagination
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
```

### Step 3: Create Models

Edit `blog/models.py`:

```python
from django.db import models
from django.contrib.auth.models import User


class Post(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.author.username} on {self.post.title}'
```

### Step 4: Create Serializers

Create `blog/serializers.py`:

```python
from django.contrib.auth.models import User
from rest_framework import serializers
from blog.models import Post, Comment


class UserSerializer(serializers.ModelSerializer):
    posts_count = serializers.IntegerField(source='posts.count', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'posts_count']
        read_only_fields = ['id']


class CommentSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'post', 'author', 'author_username', 'content', 'created_at']
        read_only_fields = ['id', 'author', 'created_at']


class PostSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    comments_count = serializers.IntegerField(source='comments.count', read_only=True)

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'content', 'author', 'author_username',
            'created_at', 'updated_at', 'published',
            'comments', 'comments_count'
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Automatically set author to current user
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)
```

### Step 5: Create Views

Edit `blog/views.py`:

```python
from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth.models import User
from blog.models import Post, Comment
from blog.serializers import PostSerializer, CommentSerializer, UserSerializer


class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Custom permission: only author can edit/delete their content.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        # Write permissions only for author
        return obj.author == request.user


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content']
    ordering_fields = ['created_at', 'title']

    def get_queryset(self):
        """
        Optionally filter by published status.
        Non-authenticated users only see published posts.
        """
        queryset = Post.objects.all()
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(published=True)
        return queryset

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """
        Custom action to publish a post.
        """
        post = self.get_object()
        post.published = True
        post.save()
        return Response({'status': 'post published'})

    @action(detail=False, methods=['get'])
    def my_posts(self, request):
        """
        Get posts for the current user.
        """
        posts = Post.objects.filter(author=request.user)
        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]

    def perform_create(self, serializer):
        """
        Set author to current user when creating comment.
        """
        serializer.save(author=self.request.user)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only endpoint for user profiles.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
```

### Step 6: Configure URLs

Edit `config/urls.py`:

```python
from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token
from blog.views import PostViewSet, CommentViewSet, UserViewSet

router = routers.DefaultRouter()
router.register(r'posts', PostViewSet)
router.register(r'comments', CommentViewSet)
router.register(r'users', UserViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/token/', obtain_auth_token, name='api_token_auth'),
    path('api-auth/', include('rest_framework.urls')),
]
```

### Step 7: Initialize and Test

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start server
python manage.py runserver
```

### Step 8: Test Authentication

```bash
# Get auth token
curl -X POST http://127.0.0.1:8000/api/token/ \
  -d "username=admin&password=yourpassword"

# Use token to create a post
curl -X POST http://127.0.0.1:8000/api/posts/ \
  -H "Authorization: Token YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"title":"My First Post","content":"Hello World","published":true}'

# List all posts
curl http://127.0.0.1:8000/api/posts/
```

**Next Steps:** Explore [authentication](../authentication/SKILL.md) and [permissions](../permissions/SKILL.md) in depth.

---

## PATH C: Production API (30 Minutes)

For a complete production setup with all best practices, see [reference/project-setup.md](reference/project-setup.md).

**Additional features in production path:**
- Environment-based settings (development, staging, production)
- Advanced pagination with cursor pagination for large datasets
- Rate limiting with throttling
- API versioning
- CORS configuration
- Custom exception handling
- Comprehensive logging
- API documentation (Swagger/OpenAPI)
- Performance optimization (select_related, prefetch_related)

**See the complete example:** [reference/examples/basic-api.py](reference/examples/basic-api.py)

---

## Common Gotchas and Solutions

### 1. Forgot to Add 'rest_framework' to INSTALLED_APPS

**Error:** `ModuleNotFoundError: No module named 'rest_framework'`

**Solution:**
```python
# settings.py
INSTALLED_APPS = [
    # ...
    'rest_framework',  # Add this!
]
```

### 2. Forgot to Run Migrations

**Error:** `django.db.utils.OperationalError: no such table: api_post`

**Solution:**
```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Missing Trailing Slash in URLs

**Error:** 301 redirects or 404 errors

**Solution:** DRF's router adds trailing slashes by default. Always include them:
```python
# Correct
curl http://127.0.0.1:8000/api/posts/

# Wrong (will redirect)
curl http://127.0.0.1:8000/api/posts
```

Or disable in settings:
```python
APPEND_SLASH = False
```

### 4. Authentication Credentials Not Provided

**Error:** `{"detail": "Authentication credentials were not provided."}`

**Cause:** Trying to access a protected endpoint without authentication.

**Solution:** Add authentication header:
```bash
curl -H "Authorization: Token YOUR_TOKEN" http://127.0.0.1:8000/api/posts/
```

### 5. CSRF Token Missing (When Using SessionAuthentication)

**Error:** `{"detail": "CSRF Failed: CSRF token missing or incorrect."}`

**Solution:** Either:
- Use Token authentication for API clients
- Include CSRF token in requests
- Exempt API views from CSRF (not recommended for production)

### 6. Serializer Validation Errors Not Clear

**Problem:** Generic error messages don't help debugging.

**Solution:** Add custom validation:
```python
class PostSerializer(serializers.ModelSerializer):
    def validate_title(self, value):
        if len(value) < 5:
            raise serializers.ValidationError(
                "Title must be at least 5 characters long."
            )
        return value
```

### 7. N+1 Query Problem

**Problem:** API is slow because of multiple database queries.

**Solution:** Use `select_related()` and `prefetch_related()`:
```python
class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.select_related('author').prefetch_related('comments')
    # ...
```

### 8. Exposing Sensitive Data

**Problem:** Accidentally exposing passwords or sensitive fields.

**Solution:** Explicitly define fields in serializer:
```python
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']  # Don't include 'password'!
        # Or use exclude
        # exclude = ['password', 'is_staff', 'is_superuser']
```

### 9. Wrong Permission Class

**Problem:** Users can access/modify data they shouldn't.

**Solution:** Use appropriate permission classes:
```python
from rest_framework.permissions import IsAuthenticated

class PostViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]  # Require authentication
```

### 10. Circular Import Errors

**Problem:** `ImportError: cannot import name 'X' from partially initialized module`

**Cause:** Importing serializers in models or vice versa.

**Solution:** Use lazy imports or string references:
```python
# In serializers.py, use string reference
author = serializers.PrimaryKeyRelatedField(queryset='auth.User')
```

### 11. Router Not Generating URLs

**Problem:** ViewSet endpoints return 404.

**Cause:** Forgot to register viewset with router.

**Solution:**
```python
router = routers.DefaultRouter()
router.register(r'posts', PostViewSet)  # Don't forget this!
```

### 12. Pagination Not Working

**Problem:** All results returned on one page.

**Cause:** Pagination not configured.

**Solution:**
```python
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}
```

---

## Settings Reference: Essential vs Optional

### TIER 1: Essential (Must Configure)

These settings are required for any production API:

```python
REST_FRAMEWORK = {
    # Always set authentication
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],

    # Always set permissions
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],

    # Always enable pagination
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
```

### TIER 2: Recommended (Should Configure)

Configure these for better performance and UX:

```python
REST_FRAMEWORK = {
    # Throttling (rate limiting)
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day',
    },

    # Filtering
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],

    # Renderer classes (format support)
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
}
```

### TIER 3: Optional (Nice to Have)

For advanced use cases:

```python
REST_FRAMEWORK = {
    # Versioning
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',

    # Schema generation
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.openapi.AutoSchema',

    # Custom exception handler
    'EXCEPTION_HANDLER': 'myapp.utils.custom_exception_handler',

    # Date/time formatting
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
}
```

For complete settings reference, see [reference/settings-reference.md](reference/settings-reference.md).

---

## Next Steps

Now that you have a working API, explore these topics:

1. **[Serializers](../serializers/SKILL.md)** - Master data validation and transformation
2. **[Views](../views/SKILL.md)** - Learn about APIView, Generic Views, and ViewSets
3. **[Authentication](../authentication/SKILL.md)** - Implement secure authentication
4. **[Permissions](../permissions/SKILL.md)** - Control access to your API
5. **[Testing](../testing/SKILL.md)** - Write comprehensive API tests

## Troubleshooting

**API returns HTML instead of JSON:**
- Check your `Accept` header: `Accept: application/json`
- Or add `.json` to the URL: `http://127.0.0.1:8000/api/posts.json`

**Can't access API from external clients:**
- Add CORS headers (install `django-cors-headers`)
- Configure `ALLOWED_HOSTS` in settings.py

**Changes not reflected:**
- Restart the development server
- Clear browser cache
- Check if you're editing the right file

## Resources

- [Official DRF Documentation](https://www.django-rest-framework.org/)
- [DRF Tutorial Series](https://www.django-rest-framework.org/tutorial/quickstart/)
- [DRF Source Code](https://github.com/encode/django-rest-framework)
- [Django Documentation](https://docs.djangoproject.com/)
