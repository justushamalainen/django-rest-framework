# Test Clients Reference

Comprehensive guide to DRF's testing tools: APIRequestFactory, APIClient, force_authenticate, and test case classes.

## Table of Contents

- [APIRequestFactory](#apirequestfactory)
- [APIClient](#apiclient)
- [force_authenticate](#force_authenticate)
- [Test Case Classes](#test-case-classes)
- [URLPatternsTestCase](#urlpatternstestcase)

## APIRequestFactory

`APIRequestFactory` extends Django's `RequestFactory` with support for DRF's request/response handling and format options.

### Basic Usage

```python
from rest_framework.test import APIRequestFactory
from myapp.views import article_list

factory = APIRequestFactory()

def test_article_list():
    # Create a GET request
    request = factory.get('/api/articles/')

    # Call the view directly
    response = article_list(request)

    # Render response to access data
    response = response.render()
    assert response.status_code == 200
```

### Available Methods

All HTTP methods are supported with consistent interfaces:

```python
# GET request with query parameters
request = factory.get('/api/articles/', {'search': 'django'})
request = factory.get('/api/articles/?search=django')  # Alternative

# POST request with JSON data
request = factory.post('/api/articles/', {'title': 'Test'}, format='json')

# PUT request
request = factory.put('/api/articles/1/', {'title': 'Updated'}, format='json')

# PATCH request
request = factory.patch('/api/articles/1/', {'title': 'Patched'}, format='json')

# DELETE request
request = factory.delete('/api/articles/1/')

# OPTIONS request
request = factory.options('/api/articles/')

# HEAD request
request = factory.head('/api/articles/')

# Generic method
request = factory.generic('CUSTOM', '/api/articles/')
```

### Format Options

APIRequestFactory supports multiple data formats:

```python
# JSON format (most common)
request = factory.post('/api/', data, format='json')

# Multipart form data (for file uploads)
request = factory.post('/api/', data, format='multipart')

# URL-encoded form data
request = factory.post('/api/', data, format='urlencoded')

# JSON API format
request = factory.post('/api/', data, format='jsonapi')

# Raw data with content type
request = factory.post('/api/', data, content_type='application/xml')
```

### Custom Headers

```python
# Add custom headers (prefix with HTTP_)
request = factory.get(
    '/api/articles/',
    HTTP_AUTHORIZATION='Bearer token123',
    HTTP_X_CUSTOM_HEADER='value'
)

# Content-Type is set automatically by format
request = factory.post('/api/', data, format='json')
# Content-Type: application/json

# Override content type manually
request = factory.post(
    '/api/',
    data,
    content_type='application/vnd.api+json'
)
```

### Working with Views

```python
from rest_framework.test import APIRequestFactory
from myapp.views import ArticleViewSet

factory = APIRequestFactory()

# Test function-based view
def test_list_view():
    request = factory.get('/api/articles/')
    response = article_list(request)
    assert response.status_code == 200

# Test class-based view
def test_class_view():
    request = factory.get('/api/articles/')
    view = ArticleListView.as_view()
    response = view(request)
    assert response.status_code == 200

# Test viewset action
def test_viewset():
    request = factory.get('/api/articles/')
    view = ArticleViewSet.as_view({'get': 'list'})
    response = view(request)
    assert response.status_code == 200

# Test viewset detail action with pk
def test_viewset_detail():
    request = factory.get('/api/articles/1/')
    view = ArticleViewSet.as_view({'get': 'retrieve'})
    response = view(request, pk=1)
    assert response.status_code == 200
```

### Setting User and Authentication

```python
from django.contrib.auth.models import User
from rest_framework.test import force_authenticate

factory = APIRequestFactory()
user = User.objects.create_user('testuser')

# Set user manually
request = factory.get('/api/articles/')
request.user = user

# Use force_authenticate helper
request = factory.get('/api/articles/')
force_authenticate(request, user=user)

# Set user and token
from rest_framework.authtoken.models import Token
token = Token.objects.create(user=user)

request = factory.get('/api/articles/')
force_authenticate(request, user=user, token=token)
```

### CSRF Protection

```python
# CSRF is disabled by default
factory = APIRequestFactory()
request = factory.post('/api/', data)
# request._dont_enforce_csrf_checks = True

# Enable CSRF checks
factory = APIRequestFactory(enforce_csrf_checks=True)
request = factory.post('/api/', data)
# Will check for CSRF token
```

### File Uploads

```python
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile

# Upload a file
image = SimpleUploadedFile(
    "test.png",
    b"file_content",
    content_type="image/png"
)
request = factory.post('/api/upload/', {'image': image}, format='multipart')

# Upload from BytesIO
file_data = BytesIO(b"file content here")
file_data.name = 'test.txt'
request = factory.post('/api/upload/', {'file': file_data}, format='multipart')
```

## APIClient

`APIClient` extends `APIRequestFactory` with full request/response handling, sessions, and authentication.

### Basic Usage

```python
from rest_framework.test import APIClient

client = APIClient()

# Make requests through URL routing
response = client.get('/api/articles/')
assert response.status_code == 200

# No need to call render() - response is already processed
assert response.data is not None
```

### HTTP Methods

```python
client = APIClient()

# GET request
response = client.get('/api/articles/')
response = client.get('/api/articles/', {'page': 2})

# POST request
response = client.post('/api/articles/', {'title': 'New'}, format='json')

# PUT request
response = client.put('/api/articles/1/', {'title': 'Updated'}, format='json')

# PATCH request
response = client.patch('/api/articles/1/', {'title': 'Patched'}, format='json')

# DELETE request
response = client.delete('/api/articles/1/')

# OPTIONS request
response = client.options('/api/articles/')

# HEAD request
response = client.head('/api/articles/')
```

### Authentication Methods

#### 1. force_authenticate() - For Testing

```python
from django.contrib.auth.models import User

client = APIClient()
user = User.objects.create_user('testuser', password='testpass')

# Authenticate all subsequent requests
client.force_authenticate(user=user)
response = client.get('/api/articles/')  # Authenticated

# Clear authentication
client.force_authenticate(user=None)
response = client.get('/api/articles/')  # Unauthenticated
```

#### 2. credentials() - Set Headers

```python
# Set authorization header for all requests
client.credentials(HTTP_AUTHORIZATION='Bearer token123')
response = client.get('/api/articles/')

# Set multiple headers
client.credentials(
    HTTP_AUTHORIZATION='Bearer token123',
    HTTP_X_API_KEY='key456'
)

# Clear credentials
client.credentials()
```

#### 3. login() - Django Session Auth

```python
from django.contrib.auth.models import User

user = User.objects.create_user('testuser', password='testpass')

# Login with session authentication
client.login(username='testuser', password='testpass')
response = client.get('/api/articles/')

# Logout
client.logout()
```

### Token Authentication Example

```python
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User

user = User.objects.create_user('testuser')
token = Token.objects.create(user=user)

# Using credentials()
client = APIClient()
client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
response = client.get('/api/articles/')

# OR using force_authenticate()
client = APIClient()
client.force_authenticate(user=user, token=token)
response = client.get('/api/articles/')
```

### Session Handling

```python
client = APIClient()

# Sessions are maintained across requests
response = client.post('/api/login/', {'username': 'test', 'password': 'pass'})
# Session cookie stored

response = client.get('/api/profile/')
# Session cookie sent automatically

# Check session data
assert '_auth_user_id' in client.session
```

### Following Redirects

```python
# Don't follow redirects (default)
response = client.post('/api/articles/', data)
assert response.status_code == 302

# Follow redirects
response = client.post('/api/articles/', data, follow=True)
assert response.status_code == 200
assert len(response.redirect_chain) > 0

# Check redirect chain
for url, status_code in response.redirect_chain:
    print(f"Redirected to {url} with {status_code}")
```

### Custom Headers

```python
# Per-request headers
response = client.get(
    '/api/articles/',
    HTTP_AUTHORIZATION='Bearer token',
    HTTP_X_CUSTOM='value'
)

# Headers for all requests
client.credentials(
    HTTP_AUTHORIZATION='Bearer token',
    HTTP_X_CUSTOM='value'
)
```

## force_authenticate

Force authentication bypasses the authentication system for testing.

### Function Signature

```python
from rest_framework.test import force_authenticate

force_authenticate(request, user=None, token=None)
```

### Usage with APIRequestFactory

```python
from rest_framework.test import APIRequestFactory, force_authenticate
from django.contrib.auth.models import User

factory = APIRequestFactory()
user = User.objects.create_user('testuser')

request = factory.get('/api/articles/')
force_authenticate(request, user=user)

# Now request.user == user
view = ArticleList.as_view()
response = view(request)
```

### Usage with APIClient

```python
from rest_framework.test import APIClient
from django.contrib.auth.models import User

client = APIClient()
user = User.objects.create_user('testuser')

# Authenticate for all subsequent requests
client.force_authenticate(user=user)

response = client.get('/api/articles/')
response = client.post('/api/articles/', data)

# Unauthenticate
client.force_authenticate(user=None)
```

### With Token

```python
from rest_framework.authtoken.models import Token

user = User.objects.create_user('testuser')
token = Token.objects.create(user=user)

# Using APIRequestFactory
request = factory.get('/api/articles/')
force_authenticate(request, user=user, token=token)
# request.user == user
# request.auth == token

# Using APIClient
client.force_authenticate(user=user, token=token)
```

### Testing Permission Classes

```python
from rest_framework import permissions, views
from rest_framework.test import APIRequestFactory, force_authenticate

class MyView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({'message': 'authenticated'})

def test_authenticated_access():
    factory = APIRequestFactory()
    view = MyView.as_view()
    user = User.objects.create_user('testuser')

    # Without authentication - should fail
    request = factory.get('/api/')
    response = view(request)
    assert response.status_code == 401

    # With authentication - should succeed
    request = factory.get('/api/')
    force_authenticate(request, user=user)
    response = view(request)
    assert response.status_code == 200
```

## Test Case Classes

DRF provides test case classes that include an `APIClient` instance as `self.client`.

### APITestCase (Most Common)

```python
from rest_framework.test import APITestCase
from django.contrib.auth.models import User

class ArticleTestCase(APITestCase):
    """Test cases with database and APIClient."""

    def setUp(self):
        """Runs before each test method."""
        self.user = User.objects.create_user('testuser')
        self.article = Article.objects.create(title='Test')

    def test_list_articles(self):
        """self.client is APIClient instance."""
        response = self.client.get('/api/articles/')
        self.assertEqual(response.status_code, 200)

    def test_create_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/articles/', {'title': 'New'})
        self.assertEqual(response.status_code, 201)
```

### APISimpleTestCase (No Database)

```python
from rest_framework.test import APISimpleTestCase

class UtilityTestCase(APISimpleTestCase):
    """Tests without database access."""

    def test_serializer_validation(self):
        """Test serializer logic without saving to DB."""
        serializer = ArticleSerializer(data={'title': ''})
        self.assertFalse(serializer.is_valid())
        self.assertIn('title', serializer.errors)
```

### APITransactionTestCase (Transaction Control)

```python
from rest_framework.test import APITransactionTestCase

class TransactionTestCase(APITransactionTestCase):
    """Test transaction behavior."""

    def test_transaction_rollback(self):
        """Test atomic transaction behavior."""
        with transaction.atomic():
            Article.objects.create(title='Test')
            # Test rollback scenarios
```

### APILiveServerTestCase (Selenium Tests)

```python
from rest_framework.test import APILiveServerTestCase
from selenium import webdriver

class BrowserTestCase(APILiveServerTestCase):
    """Tests with live server and browser."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.selenium = webdriver.Chrome()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def test_browsable_api(self):
        self.selenium.get(f'{self.live_server_url}/api/')
        # Test browser interactions
```

### Test Case Comparison

| Feature | SimpleTestCase | TestCase | TransactionTestCase | LiveServerTestCase |
|---------|---------------|----------|---------------------|-------------------|
| Database | No | Yes | Yes | Yes |
| Transactions | N/A | Per-test | Per-method | Per-test |
| Speed | Fastest | Fast | Slower | Slowest |
| Use Case | No DB needed | Most tests | Transaction testing | Browser tests |

## URLPatternsTestCase

Isolate URL patterns for testing without affecting other tests.

### Basic Usage

```python
from django.urls import path
from rest_framework.test import URLPatternsTestCase, APIClient
from myapp.views import article_list

class IsolatedURLTests(URLPatternsTestCase):
    """Test with isolated URL configuration."""

    urlpatterns = [
        path('api/articles/', article_list),
    ]

    def test_article_endpoint(self):
        client = APIClient()
        response = client.get('/api/articles/')
        self.assertEqual(response.status_code, 200)
```

### With APITestCase

```python
from rest_framework.test import URLPatternsTestCase, APITestCase

class MyAPITests(URLPatternsTestCase, APITestCase):
    """Combine URLPatternsTestCase with APITestCase."""

    urlpatterns = [
        path('test/', test_view),
    ]

    def test_endpoint(self):
        response = self.client.get('/test/')
        self.assertEqual(response.status_code, 200)
```

### Use Cases

- Testing custom URL patterns without modifying project URLs
- Testing router configurations in isolation
- Creating reusable test suites with their own URL configs
- Testing URL pattern ordering and precedence

## Best Practices

1. **Use APITestCase for most tests** - It provides database access and APIClient
2. **Use APIRequestFactory for unit testing views** - When you need granular control
3. **Use force_authenticate() in tests** - Don't test authentication unless that's what you're testing
4. **Always specify format='json'** - For POST/PUT/PATCH with nested data
5. **Check both status codes and response data** - Verify complete behavior
6. **Use setUp() for common test data** - Keep tests DRY
7. **Test both authenticated and unauthenticated access** - Cover permission scenarios

## See Also

- [Testing Views](./testing-views.md) - Testing views and viewsets
- [Testing Auth & Permissions](./testing-auth-perms.md) - Authentication and permission testing
- [Pytest Patterns](./pytest-patterns.md) - Using pytest with DRF
- [Test Pattern Examples](./examples/test-patterns.py) - Working code examples
