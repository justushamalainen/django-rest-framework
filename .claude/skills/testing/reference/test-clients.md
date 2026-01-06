# Test Clients Reference

Guide to choosing between APIClient and APIRequestFactory for testing DRF APIs.

## Quick Decision Guide

**Use APIClient (90% of cases):**
- Testing complete API endpoints through URL routing
- Need session and authentication handling
- Integration testing your API
- Most straightforward approach

**Use APIRequestFactory (Advanced):**
- Testing views directly without URL routing
- Unit testing view logic in isolation
- Need fine-grained control over request objects

## APIClient - The Standard Approach

APIClient simulates a complete HTTP client and is the recommended tool for most DRF testing.

### Basic Usage

```python
from rest_framework.test import APIClient, APITestCase
from django.contrib.auth.models import User


class ArticleAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()  # Already available as self.client
        self.user = User.objects.create_user('testuser', password='pass')

    def test_get_articles(self):
        """Test GET request."""
        response = self.client.get('/api/articles/')
        self.assertEqual(response.status_code, 200)

    def test_post_article(self):
        """Test POST request with JSON data."""
        data = {'title': 'Test', 'content': 'Content'}
        response = self.client.post('/api/articles/', data, format='json')
        self.assertEqual(response.status_code, 201)

    def test_patch_article(self):
        """Test PATCH request for partial update."""
        data = {'title': 'Updated'}
        response = self.client.patch('/api/articles/1/', data, format='json')
        self.assertEqual(response.status_code, 200)

    def test_delete_article(self):
        """Test DELETE request."""
        response = self.client.delete('/api/articles/1/')
        self.assertEqual(response.status_code, 204)
```

### Authentication with force_authenticate()

The most common way to authenticate in tests:

```python
def test_authenticated_request(self):
    """Test with forced authentication."""
    # Authenticate for all subsequent requests
    self.client.force_authenticate(user=self.user)

    response = self.client.get('/api/protected/')
    self.assertEqual(response.status_code, 200)

    # Clear authentication
    self.client.force_authenticate(user=None)

    response = self.client.get('/api/protected/')
    self.assertEqual(response.status_code, 401)
```

### Token Authentication Testing

```python
def test_token_authentication(self):
    """Test with token authentication header."""
    from rest_framework.authtoken.models import Token

    token = Token.objects.create(user=self.user)

    # Set authentication header for all requests
    self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    response = self.client.get('/api/protected/')
    self.assertEqual(response.status_code, 200)

    # Clear credentials
    self.client.credentials()
```

### Session Authentication Testing

```python
def test_session_authentication(self):
    """Test with Django session authentication."""
    # Login with credentials
    logged_in = self.client.login(username='testuser', password='pass')
    self.assertTrue(logged_in)

    response = self.client.get('/api/protected/')
    self.assertEqual(response.status_code, 200)

    # Logout
    self.client.logout()
```

### Custom Headers

```python
def test_custom_headers(self):
    """Test with custom headers."""
    response = self.client.get(
        '/api/articles/',
        HTTP_X_CUSTOM_HEADER='value',
        HTTP_ACCEPT_LANGUAGE='en-US'
    )
```

## APIRequestFactory - Advanced Unit Testing

Use APIRequestFactory when you need to test views directly without URL routing.

### Basic Usage

```python
from rest_framework.test import APIRequestFactory, force_authenticate
from myapp.views import ArticleViewSet


def test_viewset_directly():
    """Test viewset without URL routing."""
    factory = APIRequestFactory()
    view = ArticleViewSet.as_view({'get': 'list'})

    # Create request
    request = factory.get('/api/articles/')

    # Call view directly
    response = view(request)
    response.render()  # Must render to access data

    assert response.status_code == 200
```

### With Authentication

```python
def test_viewset_with_auth():
    """Test viewset with forced authentication."""
    factory = APIRequestFactory()
    user = User.objects.create_user('testuser')

    request = factory.post('/api/articles/', {'title': 'Test'}, format='json')
    force_authenticate(request, user=user)

    view = ArticleViewSet.as_view({'post': 'create'})
    response = view(request)
    response.render()

    assert response.status_code == 201
```

## Test Case Classes

DRF provides test case classes with APIClient built-in:

### APITestCase (Most Common)

```python
from rest_framework.test import APITestCase


class MyAPITests(APITestCase):
    """Standard test case with database and APIClient."""

    def setUp(self):
        # self.client is automatically an APIClient instance
        self.user = User.objects.create_user('testuser')

    def test_endpoint(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/articles/')
        self.assertEqual(response.status_code, 200)
```

### APISimpleTestCase (No Database)

```python
from rest_framework.test import APISimpleTestCase


class UtilityTests(APISimpleTestCase):
    """Tests without database access."""

    def test_without_db(self):
        # No database operations allowed
        response = self.client.get('/api/status/')
        self.assertEqual(response.status_code, 200)
```

## Best Practices

1. **Use APITestCase for most tests** - Provides database access and APIClient
2. **Use force_authenticate() in tests** - Don't test authentication unless that's what you're testing
3. **Always specify format='json'** - For POST/PUT/PATCH with nested data
4. **Use APIRequestFactory sparingly** - Only when you need to test views in isolation
5. **Test through URLs with APIClient** - Better integration testing
6. **Check both status codes and response data** - Verify complete behavior

## Common Patterns

```python
# Test authenticated endpoint
self.client.force_authenticate(user=self.user)
response = self.client.post('/api/articles/', data, format='json')

# Test unauthenticated access
response = self.client.get('/api/public/')

# Test with query parameters
response = self.client.get('/api/articles/', {'status': 'published'})

# Test with pagination
response = self.client.get('/api/articles/', {'page': 2})

# Verify database changes
self.assertEqual(Article.objects.count(), 5)

# Refresh object from database
article.refresh_from_db()
self.assertEqual(article.title, 'Updated')
```

## See Also

- [Testing Views](./testing-views.md) - Testing views, authentication, and permissions
- [Pytest Patterns](./pytest-patterns.md) - Using pytest fixtures and parametrization
