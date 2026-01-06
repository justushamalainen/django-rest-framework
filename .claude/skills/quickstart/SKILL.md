---
version: 1.0
last_updated: 2026-01-06
difficulty: beginner
keywords: quickstart, getting-started, installation, first-api
dependencies: djangorestframework>=3.14, django>=4.2
estimated_time: 10 minutes
---

# Django REST Framework Quickstart

Get a working REST API in 10 minutes. This guide is beginner-friendly and copy-paste ready.

## Before You Start

### Prerequisites

**Required:**
- Python 3.8+ installed
- Basic Django knowledge (models, views, URLs)
- Basic HTTP understanding (GET, POST, PUT, DELETE)

**New to Django?** Complete [Django tutorial parts 1-4](https://docs.djangoproject.com/en/stable/intro/tutorial01/) first.

### Installation

```bash
# Create virtual environment
python3 -m venv env
source env/bin/activate  # Windows: env\Scripts\activate

# Install Django and DRF
pip install django djangorestframework

# Verify installation
python -c "import rest_framework; print(rest_framework.VERSION)"
```

---

## Quick Start: Your First API in 5 Minutes

This creates a working User API with zero custom code.

### Step 1: Create Project

```bash
mkdir myapi && cd myapi
django-admin startproject config .
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

# Add DRF settings
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}
```

### Step 3: Create Serializer

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

### Step 4: Create ViewSet

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
    path('api-auth/', include('rest_framework.urls')),
]
```

### Step 6: Initialize Database

```bash
# Create database tables
python manage.py migrate

# Create a test user
python manage.py createsuperuser --username admin --email admin@example.com

# Start server
python manage.py runserver
```

### Step 7: Test Your API

**Browser:** Visit `http://127.0.0.1:8000/api/users/` and log in with your superuser.

**curl:**

```bash
# List users
curl -u admin:password http://127.0.0.1:8000/api/users/

# Create user
curl -u admin:password -X POST http://127.0.0.1:8000/api/users/ \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com"}'
```

**Congratulations!** You have a working REST API.

---

## Adding Your Own Model

Now let's create a simple Note API with authentication.

### Step 1: Create Model

Edit `api/models.py`:

```python
from django.db import models
from django.contrib.auth.models import User


class Note(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
```

### Step 2: Create Serializer

Add to `api/serializers.py`:

```python
from api.models import Note


class NoteSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)

    class Meta:
        model = Note
        fields = ['id', 'title', 'content', 'author', 'author_username', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Auto-set author to current user
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)
```

### Step 3: Create ViewSet

Add to `api/views.py`:

```python
from rest_framework import permissions
from api.models import Note
from api.serializers import NoteSerializer


class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Only author can edit/delete their notes.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.author == request.user


class NoteViewSet(viewsets.ModelViewSet):
    queryset = Note.objects.all()
    serializer_class = NoteSerializer
    permission_classes = [permissions.IsAuthenticated, IsAuthorOrReadOnly]

    def get_queryset(self):
        # Users only see their own notes
        return Note.objects.filter(author=self.request.user)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
```

### Step 4: Add URL

Edit `config/urls.py` to add note endpoint:

```python
from api.views import UserViewSet, NoteViewSet

router = routers.DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'notes', NoteViewSet)  # Add this
```

### Step 5: Add Token Authentication

Edit `config/settings.py`:

```python
INSTALLED_APPS = [
    # ... existing apps ...
    'rest_framework',
    'rest_framework.authtoken',  # Add this
    'api',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}
```

Add token endpoint to `config/urls.py`:

```python
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/token/', obtain_auth_token),  # Add this
    path('api-auth/', include('rest_framework.urls')),
]
```

### Step 6: Run Migrations and Test

```bash
# Create and apply migrations
python manage.py makemigrations
python manage.py migrate

# Restart server
python manage.py runserver
```

### Step 7: Test with Token Authentication

```bash
# Get auth token
curl -X POST http://127.0.0.1:8000/api/token/ \
  -d "username=admin&password=yourpassword"

# Response: {"token":"9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"}

# Create a note
curl -X POST http://127.0.0.1:8000/api/notes/ \
  -H "Authorization: Token YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"title":"My First Note","content":"Hello DRF!"}'

# List your notes
curl -H "Authorization: Token YOUR_TOKEN_HERE" \
  http://127.0.0.1:8000/api/notes/
```

---

## Common Issues

### 1. Forgot to Add 'rest_framework' to INSTALLED_APPS

**Error:** `ModuleNotFoundError: No module named 'rest_framework'`

**Fix:**
```python
INSTALLED_APPS = [
    # ...
    'rest_framework',  # Add this
]
```

### 2. Forgot to Run Migrations

**Error:** `django.db.utils.OperationalError: no such table`

**Fix:**
```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Missing Trailing Slash

**Error:** 301 redirects or 404 errors

**Fix:** DRF routers add trailing slashes by default. Always include them:
```bash
# Correct
curl http://127.0.0.1:8000/api/notes/

# Wrong (will redirect)
curl http://127.0.0.1:8000/api/notes
```

### 4. Authentication Credentials Not Provided

**Error:** `{"detail": "Authentication credentials were not provided."}`

**Fix:** Add authentication header:
```bash
curl -H "Authorization: Token YOUR_TOKEN" http://127.0.0.1:8000/api/notes/
```

### 5. CSRF Token Missing

**Error:** `{"detail": "CSRF Failed: CSRF token missing or incorrect."}`

**Fix:** Use Token authentication instead of Session authentication for API clients, or include CSRF token in requests when using Session authentication.

### 6. N+1 Query Problem (Slow API)

**Problem:** Too many database queries.

**Fix:** Use `select_related()` for ForeignKey and `prefetch_related()` for ManyToMany:
```python
class NoteViewSet(viewsets.ModelViewSet):
    queryset = Note.objects.select_related('author')
    # ...
```

---

## Next Steps

Explore these skills to build on what you've learned:

- **[Serializers](../serializers/SKILL.md)** - Validation, nested data, custom fields
- **[Views](../views/SKILL.md)** - APIView, Generic Views, ViewSets, custom actions
- **[Authentication](../authentication/SKILL.md)** - JWT, OAuth, custom auth
- **[Permissions](../permissions/SKILL.md)** - Object-level permissions, custom logic
- **[Testing](../testing/SKILL.md)** - APIClient, factories, test patterns

## Resources

- [Official DRF Documentation](https://www.django-rest-framework.org/)
- [DRF Tutorial Series](https://www.django-rest-framework.org/tutorial/quickstart/)
- [Django Documentation](https://docs.djangoproject.com/)
