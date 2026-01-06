# Testing Views, Authentication, and Permissions

Comprehensive guide to testing DRF views, viewsets, authentication, and permissions.

## Testing ViewSets (Most Common)

### Basic CRUD Testing

```python
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth.models import User
from myapp.models import Article


class ArticleViewSetTest(APITestCase):
    """Test ArticleViewSet with all CRUD operations."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', password='pass')
        self.list_url = '/api/articles/'

    def test_list_articles(self):
        """Test list action."""
        Article.objects.create(title='Article 1', content='Content', author=self.user)
        Article.objects.create(title='Article 2', content='Content', author=self.user)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_retrieve_article(self):
        """Test retrieve action."""
        article = Article.objects.create(title='Test', content='Content', author=self.user)
        url = f'{self.list_url}{article.id}/'

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test')

    def test_create_article(self):
        """Test create action."""
        self.client.force_authenticate(user=self.user)

        data = {'title': 'New Article', 'content': 'New content'}
        response = self.client.post(self.list_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Article.objects.count(), 1)

    def test_update_article(self):
        """Test full update action."""
        article = Article.objects.create(title='Original', content='Content', author=self.user)
        self.client.force_authenticate(user=self.user)

        url = f'{self.list_url}{article.id}/'
        data = {'title': 'Updated', 'content': 'Updated content'}
        response = self.client.put(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        article.refresh_from_db()
        self.assertEqual(article.title, 'Updated')

    def test_partial_update_article(self):
        """Test partial update action."""
        article = Article.objects.create(title='Original', content='Content', author=self.user)
        self.client.force_authenticate(user=self.user)

        url = f'{self.list_url}{article.id}/'
        data = {'title': 'Patched'}
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        article.refresh_from_db()
        self.assertEqual(article.title, 'Patched')
        self.assertEqual(article.content, 'Content')  # Unchanged

    def test_destroy_article(self):
        """Test destroy action."""
        article = Article.objects.create(title='Test', content='Content', author=self.user)
        self.client.force_authenticate(user=self.user)

        url = f'{self.list_url}{article.id}/'
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Article.objects.count(), 0)
```

## Testing Authentication

### Basic Authentication Testing

```python
class AuthenticationTest(APITestCase):
    """Test authentication requirements."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', password='testpass123')
        self.url = '/api/protected/'

    def test_unauthenticated_request(self):
        """Unauthenticated requests should be rejected."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_request(self):
        """Authenticated requests should succeed."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout_clears_authentication(self):
        """Clearing authentication should fail subsequent requests."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Clear authentication
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
```

### Token Authentication

```python
from rest_framework.authtoken.models import Token


class TokenAuthenticationTest(APITestCase):
    """Test token authentication."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', password='pass')
        self.token = Token.objects.create(user=self.user)
        self.url = '/api/protected/'

    def test_valid_token(self):
        """Valid token should authenticate request."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_token(self):
        """Invalid token should be rejected."""
        self.client.credentials(HTTP_AUTHORIZATION='Token invalidtoken123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_token(self):
        """Missing token should be rejected."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
```

## Testing Permissions

### IsAuthenticated Permission

```python
class IsAuthenticatedTest(APITestCase):
    """Test IsAuthenticated permission."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', password='pass')
        self.url = '/api/protected/'

    def test_anonymous_denied(self):
        """Anonymous users should be denied."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_allowed(self):
        """Authenticated users should be allowed."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
```

### IsAdminUser Permission

```python
class IsAdminUserTest(APITestCase):
    """Test IsAdminUser permission."""

    def setUp(self):
        self.regular_user = User.objects.create_user('regular', password='pass')
        self.staff_user = User.objects.create_user('staff', password='pass', is_staff=True)
        self.admin_user = User.objects.create_superuser('admin', 'admin@test.com', 'pass')
        self.url = '/api/admin-only/'

    def test_regular_user_denied(self):
        """Regular users should be denied."""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_user_allowed(self):
        """Staff users should be allowed."""
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_user_allowed(self):
        """Admin users should be allowed."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
```

### IsAuthenticatedOrReadOnly Permission

```python
class IsAuthenticatedOrReadOnlyTest(APITestCase):
    """Test IsAuthenticatedOrReadOnly permission."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', password='pass')
        self.list_url = '/api/articles/'
        self.article = Article.objects.create(title='Test', content='Content', author=self.user)
        self.detail_url = f'/api/articles/{self.article.id}/'

    def test_anonymous_can_read(self):
        """Anonymous users can read."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_anonymous_cannot_write(self):
        """Anonymous users cannot write."""
        data = {'title': 'New', 'content': 'Content'}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_can_write(self):
        """Authenticated users can write."""
        self.client.force_authenticate(user=self.user)
        data = {'title': 'New', 'content': 'Content'}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
```

### Custom Object-Level Permissions

```python
# permissions.py
from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):
    """Custom permission to only allow authors to edit their articles."""

    def has_object_permission(self, request, view, obj):
        # Read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for the author
        return obj.author == request.user


# tests.py
class IsAuthorOrReadOnlyTest(APITestCase):
    """Test custom IsAuthorOrReadOnly permission."""

    def setUp(self):
        self.author = User.objects.create_user('author', password='pass')
        self.other_user = User.objects.create_user('other', password='pass')
        self.article = Article.objects.create(
            title='Test',
            content='Content',
            author=self.author
        )
        self.url = f'/api/articles/{self.article.id}/'

    def test_anonymous_can_read(self):
        """Anonymous users can read."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_author_can_edit(self):
        """Author can edit their article."""
        self.client.force_authenticate(user=self.author)
        data = {'title': 'Updated'}
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_other_user_cannot_edit(self):
        """Other users cannot edit article."""
        self.client.force_authenticate(user=self.other_user)
        data = {'title': 'Updated'}
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_author_can_delete(self):
        """Author can delete their article."""
        self.client.force_authenticate(user=self.author)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_other_user_cannot_delete(self):
        """Other users cannot delete article."""
        self.client.force_authenticate(user=self.other_user)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
```

## Testing Custom Actions

```python
# views.py
from rest_framework.decorators import action
from rest_framework import viewsets


class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        article = self.get_object()
        article.status = 'published'
        article.save()
        return Response({'status': 'published'})


# tests.py
class ArticleCustomActionsTest(APITestCase):
    """Test custom actions on viewset."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', password='pass')
        self.article = Article.objects.create(
            title='Test',
            content='Content',
            status='draft',
            author=self.user
        )

    def test_publish_action(self):
        """POST to publish action changes status."""
        self.client.force_authenticate(user=self.user)
        url = f'/api/articles/{self.article.id}/publish/'
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.article.refresh_from_db()
        self.assertEqual(self.article.status, 'published')
```

## Testing Validation

```python
class ValidationTest(APITestCase):
    """Test data validation."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', password='pass')
        self.client.force_authenticate(user=self.user)
        self.url = '/api/articles/'

    def test_missing_required_field(self):
        """Should reject data with missing required fields."""
        data = {'content': 'Content'}  # Missing title
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', response.data)

    def test_empty_field(self):
        """Should reject empty fields."""
        data = {'title': '', 'content': 'Content'}
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', response.data)

    def test_valid_data(self):
        """Should accept valid data."""
        data = {'title': 'Valid Title', 'content': 'Valid content'}
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
```

## Best Practices

1. **Test all CRUD operations** - List, retrieve, create, update, delete
2. **Test authentication** - Both authenticated and unauthenticated access
3. **Test permissions** - Anonymous, regular users, staff, admins
4. **Test object-level permissions** - Users can only edit their own objects
5. **Test validation** - Both valid and invalid data
6. **Use force_authenticate()** - Don't test auth unless that's the focus
7. **Check database state** - Verify objects are created/updated/deleted correctly
8. **Test error responses** - Ensure helpful error messages are returned

## See Also

- [Test Clients Reference](./test-clients.md) - APIClient and force_authenticate
- [Pytest Patterns](./pytest-patterns.md) - Using pytest fixtures and parametrization
