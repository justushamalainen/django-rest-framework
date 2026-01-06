# Testing Authentication and Permissions

Comprehensive guide to testing DRF authentication schemes and permission classes.

## Table of Contents

- [Testing Authentication](#testing-authentication)
- [Testing Permissions](#testing-permissions)
- [Testing Token Authentication](#testing-token-authentication)
- [Testing Session Authentication](#testing-session-authentication)
- [Testing JWT Authentication](#testing-jwt-authentication)
- [Testing Custom Authentication](#testing-custom-authentication)
- [Testing Object-Level Permissions](#testing-object-level-permissions)
- [Testing Permission Composition](#testing-permission-composition)

## Testing Authentication

### Basic Authentication Testing

```python
# views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def protected_view(request):
    return Response({'message': 'You are authenticated'})


# tests.py
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth.models import User


class AuthenticationTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
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
        self.assertEqual(response.data['message'], 'You are authenticated')

    def test_logout_clears_authentication(self):
        """Logout should clear authentication."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Clear authentication
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
```

### Testing Multiple Authentication Classes

```python
# views.py
from rest_framework import viewsets
from rest_framework.authentication import TokenAuthentication, SessionAuthentication


class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]


# tests.py
class MultipleAuthenticationTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', password='pass')
        self.url = '/api/articles/'

    def test_token_authentication(self):
        """Should authenticate with token."""
        from rest_framework.authtoken.models import Token

        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_session_authentication(self):
        """Should authenticate with session."""
        self.client.login(username='testuser', password='pass')

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
```

## Testing Permissions

### IsAuthenticated Permission

```python
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView


class ProtectedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'message': 'Authenticated access'})


class IsAuthenticatedTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', password='pass')
        self.url = '/api/protected/'

    def test_anonymous_user_denied(self):
        """Anonymous users should be denied."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_allowed(self):
        """Authenticated users should be allowed."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
```

### IsAdminUser Permission

```python
from rest_framework.permissions import IsAdminUser


class AdminOnlyView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response({'message': 'Admin access'})


class IsAdminUserTest(APITestCase):
    def setUp(self):
        self.regular_user = User.objects.create_user('regular', password='pass')
        self.staff_user = User.objects.create_user(
            'staff',
            password='pass',
            is_staff=True
        )
        self.admin_user = User.objects.create_superuser(
            'admin',
            'admin@example.com',
            'pass'
        )
        self.url = '/api/admin-only/'

    def test_anonymous_denied(self):
        """Anonymous users should be denied."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

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
from rest_framework.permissions import IsAuthenticatedOrReadOnly


class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class IsAuthenticatedOrReadOnlyTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', password='pass')
        self.list_url = '/api/articles/'
        self.article = Article.objects.create(title='Test', content='Content')
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

### Custom Permission Classes

```python
# permissions.py
from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow authors to edit their articles.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for the author
        return obj.author == request.user


# tests.py
class IsAuthorOrReadOnlyTest(APITestCase):
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

    def test_anonymous_cannot_edit(self):
        """Anonymous users cannot edit."""
        data = {'title': 'Updated'}
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

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
```

## Testing Token Authentication

### Token Creation and Usage

```python
from rest_framework.authtoken.models import Token


class TokenAuthenticationTest(APITestCase):
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

    def test_malformed_header(self):
        """Malformed auth header should be rejected."""
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token.key)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
```

### Token Obtain View Testing

```python
# views.py (if using custom token view)
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response


class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username
        })


# tests.py
class TokenObtainTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.url = '/api/token/'

    def test_obtain_token_success(self):
        """Valid credentials should return token."""
        data = {'username': 'testuser', 'password': 'testpass123'}
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user_id', response.data)

    def test_obtain_token_invalid_credentials(self):
        """Invalid credentials should be rejected."""
        data = {'username': 'testuser', 'password': 'wrongpass'}
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_obtain_token_missing_fields(self):
        """Missing fields should be rejected."""
        data = {'username': 'testuser'}
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
```

## Testing Session Authentication

### Session-Based Authentication

```python
class SessionAuthenticationTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', password='testpass')
        self.url = '/api/protected/'

    def test_login_with_credentials(self):
        """Should authenticate with login credentials."""
        logged_in = self.client.login(username='testuser', password='testpass')
        self.assertTrue(logged_in)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout(self):
        """Should clear authentication after logout."""
        self.client.login(username='testuser', password='testpass')

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.client.logout()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_session_persistence(self):
        """Session should persist across requests."""
        self.client.login(username='testuser', password='testpass')

        # Multiple requests should remain authenticated
        for _ in range(3):
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
```

## Testing JWT Authentication

### JWT Token Testing (using djangorestframework-simplejwt)

```python
from rest_framework_simplejwt.tokens import RefreshToken


class JWTAuthenticationTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', password='testpass')
        self.url = '/api/protected/'

    def get_tokens_for_user(self, user):
        """Helper to get JWT tokens."""
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

    def test_access_token_authentication(self):
        """Valid access token should authenticate."""
        tokens = self.get_tokens_for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}'
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_token(self):
        """Invalid token should be rejected."""
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalidtoken')

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_expired_token(self):
        """Expired token should be rejected."""
        from datetime import timedelta
        from django.utils import timezone

        # Create expired token
        refresh = RefreshToken.for_user(self.user)
        refresh.set_exp(lifetime=timedelta(seconds=-1))
        access_token = str(refresh.access_token)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
```

### JWT Token Obtain and Refresh

```python
class JWTTokenObtainTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.token_obtain_url = '/api/token/'
        self.token_refresh_url = '/api/token/refresh/'

    def test_obtain_token_pair(self):
        """Should obtain access and refresh tokens."""
        data = {'username': 'testuser', 'password': 'testpass123'}
        response = self.client.post(self.token_obtain_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_refresh_token(self):
        """Should refresh access token."""
        # Get initial tokens
        data = {'username': 'testuser', 'password': 'testpass123'}
        response = self.client.post(self.token_obtain_url, data, format='json')
        refresh_token = response.data['refresh']

        # Refresh the access token
        data = {'refresh': refresh_token}
        response = self.client.post(self.token_refresh_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
```

## Testing Custom Authentication

### Custom Authentication Backend

```python
# authentication.py
from rest_framework import authentication
from rest_framework import exceptions


class CustomTokenAuthentication(authentication.BaseAuthentication):
    """Custom token authentication using X-API-Key header."""

    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY')

        if not api_key:
            return None

        try:
            user = User.objects.get(profile__api_key=api_key)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid API key')

        return (user, None)


# tests.py
class CustomAuthenticationTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', password='pass')
        self.profile = Profile.objects.create(
            user=self.user,
            api_key='test-api-key-123'
        )
        self.url = '/api/protected/'

    def test_valid_api_key(self):
        """Valid API key should authenticate."""
        self.client.credentials(HTTP_X_API_KEY='test-api-key-123')

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_api_key(self):
        """Invalid API key should be rejected."""
        self.client.credentials(HTTP_X_API_KEY='invalid-key')

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_api_key(self):
        """Missing API key should be rejected."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
```

## Testing Object-Level Permissions

### has_object_permission Testing

```python
# permissions.py
class IsOwner(permissions.BasePermission):
    """Permission to only allow owners to access object."""

    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user


# tests.py
class ObjectLevelPermissionTest(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', password='pass')
        self.other_user = User.objects.create_user('other', password='pass')
        self.article = Article.objects.create(
            title='Test',
            content='Content',
            owner=self.owner
        )
        self.url = f'/api/articles/{self.article.id}/'

    def test_owner_can_access(self):
        """Owner can access their object."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_owner_cannot_access(self):
        """Non-owner cannot access object."""
        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_access(self):
        """Anonymous user cannot access object."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
```

### Django Model Permissions

```python
from django.contrib.auth.models import Permission
from rest_framework.permissions import DjangoModelPermissions


class DjangoModelPermissionsTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', password='pass')
        self.url = '/api/articles/'

    def test_no_permissions(self):
        """User without permissions cannot create."""
        self.client.force_authenticate(user=self.user)

        data = {'title': 'Test', 'content': 'Content'}
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_with_add_permission(self):
        """User with add permission can create."""
        permission = Permission.objects.get(codename='add_article')
        self.user.user_permissions.add(permission)

        self.client.force_authenticate(user=self.user)

        data = {'title': 'Test', 'content': 'Content'}
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
```

## Testing Permission Composition

### AND Operator (&)

```python
from rest_framework.permissions import IsAuthenticated, IsAdminUser


class ComposedPermissionView(APIView):
    permission_classes = [IsAuthenticated & IsAdminUser]

    def get(self, request):
        return Response({'message': 'Authenticated admin access'})


class ANDPermissionTest(APITestCase):
    def setUp(self):
        self.regular_user = User.objects.create_user('regular', password='pass')
        self.admin_user = User.objects.create_superuser(
            'admin',
            'admin@example.com',
            'pass'
        )
        self.url = '/api/composed/'

    def test_anonymous_denied(self):
        """Anonymous users denied (fails IsAuthenticated)."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_denied(self):
        """Regular users denied (fails IsAdminUser)."""
        self.client.force_authenticate(user=self.regular_user)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_user_allowed(self):
        """Admin users allowed (passes both)."""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
```

### OR Operator (|)

```python
class IsAuthorOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.author == request.user


class ORPermissionView(APIView):
    permission_classes = [IsAuthorOrAdmin | IsAdminUser]


class ORPermissionTest(APITestCase):
    def setUp(self):
        self.author = User.objects.create_user('author', password='pass')
        self.admin = User.objects.create_superuser('admin', 'admin@test.com', 'pass')
        self.other = User.objects.create_user('other', password='pass')
        self.article = Article.objects.create(
            title='Test',
            content='Content',
            author=self.author
        )
        self.url = f'/api/articles/{self.article.id}/'

    def test_author_allowed(self):
        """Author allowed (passes IsAuthorOrAdmin)."""
        self.client.force_authenticate(user=self.author)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_allowed(self):
        """Admin allowed (passes IsAdminUser)."""
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_other_user_denied(self):
        """Other users denied (fails both)."""
        self.client.force_authenticate(user=self.other)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
```

## Best Practices

1. **Test both authentication and authorization** - Ensure users can authenticate AND have proper permissions
2. **Test all user types** - Anonymous, regular users, staff, admins
3. **Test all HTTP methods** - Permissions may differ by method
4. **Test object-level permissions** - Not just list-level
5. **Use force_authenticate in tests** - Don't rely on session state
6. **Test permission messages** - Verify error responses are helpful
7. **Test edge cases** - Expired tokens, deleted users, etc.
8. **Mock external auth providers** - Keep tests fast and reliable

## See Also

- [Test Clients Reference](./test-clients.md) - APIClient and force_authenticate
- [Testing Views](./testing-views.md) - Testing views with permissions
- [Test Pattern Examples](./examples/test-patterns.py) - Working code examples
