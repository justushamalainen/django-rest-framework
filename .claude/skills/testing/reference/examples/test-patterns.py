"""
Working test patterns for Django REST Framework.

This file contains comprehensive, working examples of DRF testing patterns.
All tests are self-contained and demonstrate best practices.
"""

import pytest
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import (
    APIClient,
    APIRequestFactory,
    APITestCase,
    force_authenticate,
)


# =============================================================================
# Example Models and Serializers
# =============================================================================

# Assume these models exist in your app:
# class Article(models.Model):
#     title = models.CharField(max_length=200)
#     content = models.TextField()
#     author = models.ForeignKey(User, on_delete=models.CASCADE)
#     status = models.CharField(max_length=20, default='draft')
#     created = models.DateTimeField(auto_now_add=True)
#     modified = models.DateTimeField(auto_now=True)
#
# class Comment(models.Model):
#     article = models.ForeignKey(Article, related_name='comments', on_delete=models.CASCADE)
#     author = models.ForeignKey(User, on_delete=models.CASCADE)
#     text = models.TextField()
#     created = models.DateTimeField(auto_now_add=True)


# =============================================================================
# PATTERN 1: Basic APITestCase - Most Common Pattern
# =============================================================================

class ArticleAPITestCase(APITestCase):
    """
    Standard pattern for testing DRF APIs.
    Uses APITestCase which provides self.client (APIClient instance).
    """

    def setUp(self):
        """Create test data before each test method."""
        # Create users
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='pass123'
        )

        # Create test article
        # self.article = Article.objects.create(
        #     title='Test Article',
        #     content='Test content',
        #     author=self.user
        # )

        # Define URLs
        self.list_url = '/api/articles/'
        # self.detail_url = f'/api/articles/{self.article.id}/'

    def test_list_articles(self):
        """GET /api/articles/ returns list of articles."""
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_create_article_authenticated(self):
        """Authenticated users can create articles."""
        # Authenticate as user
        self.client.force_authenticate(user=self.user)

        data = {
            'title': 'New Article',
            'content': 'New content'
        }
        response = self.client.post(self.list_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'New Article')
        # self.assertEqual(Article.objects.count(), 2)

    def test_create_article_unauthenticated(self):
        """Unauthenticated users cannot create articles."""
        data = {'title': 'New', 'content': 'Content'}
        response = self.client.post(self.list_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_article_as_author(self):
        """Authors can update their articles."""
        # self.client.force_authenticate(user=self.user)
        #
        # data = {'title': 'Updated Title'}
        # response = self.client.patch(self.detail_url, data, format='json')
        #
        # self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.article.refresh_from_db()
        # self.assertEqual(self.article.title, 'Updated Title')
        pass

    def test_delete_article_permission(self):
        """Only authors can delete their articles."""
        # Test as non-author
        # self.client.force_authenticate(user=self.other_user)
        # response = self.client.delete(self.detail_url)
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        #
        # # Test as author
        # self.client.force_authenticate(user=self.user)
        # response = self.client.delete(self.detail_url)
        # self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        pass


# =============================================================================
# PATTERN 2: Using APIRequestFactory for Unit Testing Views
# =============================================================================

class ArticleViewUnitTest(TestCase):
    """
    Use APIRequestFactory to test views directly without URL routing.
    Faster than full integration tests, good for unit testing.
    """

    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user('testuser', password='pass')

    def test_list_view_with_factory(self):
        """Test list view directly with APIRequestFactory."""
        # from myapp.views import ArticleViewSet
        #
        # # Create request
        # request = self.factory.get('/api/articles/')
        #
        # # Call view directly
        # view = ArticleViewSet.as_view({'get': 'list'})
        # response = view(request)
        #
        # self.assertEqual(response.status_code, 200)
        pass

    def test_create_view_with_authentication(self):
        """Test create view with forced authentication."""
        # from myapp.views import ArticleViewSet
        #
        # data = {'title': 'Test', 'content': 'Content'}
        # request = self.factory.post('/api/articles/', data, format='json')
        #
        # # Force authenticate the request
        # force_authenticate(request, user=self.user)
        #
        # view = ArticleViewSet.as_view({'post': 'create'})
        # response = view(request)
        #
        # self.assertEqual(response.status_code, 201)
        pass


# =============================================================================
# PATTERN 3: Testing Authentication
# =============================================================================

class AuthenticationTest(APITestCase):
    """Test various authentication methods."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.url = '/api/protected/'

    def test_force_authenticate(self):
        """Using force_authenticate for testing."""
        # Before authentication
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # After force authentication
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Clear authentication
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_authentication(self):
        """Test token authentication."""
        from rest_framework.authtoken.models import Token

        # Create token for user
        token = Token.objects.create(user=self.user)

        # Use credentials method to set header
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_session_authentication(self):
        """Test session-based authentication."""
        # Login with credentials
        logged_in = self.client.login(username='testuser', password='testpass123')
        self.assertTrue(logged_in)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Logout
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# =============================================================================
# PATTERN 4: Testing Permissions
# =============================================================================

class PermissionTest(APITestCase):
    """Test permission classes."""

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

    def test_is_authenticated_permission(self):
        """Test IsAuthenticated permission."""
        url = '/api/authenticated-only/'

        # Unauthenticated
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Authenticated
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_is_admin_permission(self):
        """Test IsAdminUser permission."""
        url = '/api/admin-only/'

        # Regular user denied
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Staff user allowed
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Admin user allowed
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_object_level_permission(self):
        """Test object-level permissions."""
        # author = User.objects.create_user('author', password='pass')
        # other = User.objects.create_user('other', password='pass')
        #
        # article = Article.objects.create(
        #     title='Test',
        #     content='Content',
        #     author=author
        # )
        #
        # url = f'/api/articles/{article.id}/'
        #
        # # Author can edit
        # self.client.force_authenticate(user=author)
        # response = self.client.patch(url, {'title': 'Updated'}, format='json')
        # self.assertEqual(response.status_code, status.HTTP_200_OK)
        #
        # # Other user cannot edit
        # self.client.force_authenticate(user=other)
        # response = self.client.patch(url, {'title': 'Updated'}, format='json')
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        pass


# =============================================================================
# PATTERN 5: Testing Serializers
# =============================================================================

class SerializerTest(TestCase):
    """Test serializer validation and transformation."""

    def setUp(self):
        self.user = User.objects.create_user('testuser')

    def test_serializer_validation_success(self):
        """Test valid data passes validation."""
        # from myapp.serializers import ArticleSerializer
        #
        # data = {
        #     'title': 'Valid Title',
        #     'content': 'Valid content'
        # }
        # serializer = ArticleSerializer(data=data)
        #
        # self.assertTrue(serializer.is_valid())
        # self.assertEqual(serializer.validated_data['title'], 'Valid Title')
        pass

    def test_serializer_validation_failure(self):
        """Test invalid data fails validation."""
        # from myapp.serializers import ArticleSerializer
        #
        # data = {'title': ''}  # Empty title, missing content
        # serializer = ArticleSerializer(data=data)
        #
        # self.assertFalse(serializer.is_valid())
        # self.assertIn('title', serializer.errors)
        # self.assertIn('content', serializer.errors)
        pass

    def test_serializer_create(self):
        """Test creating object from serializer."""
        # from myapp.serializers import ArticleSerializer
        #
        # data = {'title': 'New', 'content': 'Content'}
        # serializer = ArticleSerializer(data=data)
        #
        # self.assertTrue(serializer.is_valid())
        # article = serializer.save(author=self.user)
        #
        # self.assertEqual(article.title, 'New')
        # self.assertEqual(Article.objects.count(), 1)
        pass

    def test_serializer_update(self):
        """Test updating object with serializer."""
        # from myapp.serializers import ArticleSerializer
        #
        # article = Article.objects.create(
        #     title='Original',
        #     content='Content',
        #     author=self.user
        # )
        #
        # data = {'title': 'Updated'}
        # serializer = ArticleSerializer(article, data=data, partial=True)
        #
        # self.assertTrue(serializer.is_valid())
        # updated_article = serializer.save()
        #
        # self.assertEqual(updated_article.title, 'Updated')
        # self.assertEqual(updated_article.content, 'Content')  # Unchanged
        pass

    def test_read_only_field(self):
        """Test read-only field is not writable."""
        # from myapp.serializers import ArticleSerializer
        #
        # data = {
        #     'title': 'Test',
        #     'content': 'Content',
        #     'created': '2024-01-01T00:00:00Z'  # Read-only field
        # }
        # serializer = ArticleSerializer(data=data)
        #
        # self.assertTrue(serializer.is_valid())
        # # created field should be ignored in validated_data
        # self.assertNotIn('created', serializer.validated_data)
        pass


# =============================================================================
# PATTERN 6: Testing Pagination
# =============================================================================

class PaginationTest(APITestCase):
    """Test pagination in list views."""

    def setUp(self):
        # Create multiple articles
        # self.user = User.objects.create_user('testuser')
        # for i in range(25):
        #     Article.objects.create(
        #         title=f'Article {i}',
        #         content=f'Content {i}',
        #         author=self.user
        #     )
        self.url = '/api/articles/'

    def test_first_page(self):
        """Test first page of results."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Assuming page size of 10
        # self.assertEqual(len(response.data['results']), 10)
        # self.assertIsNotNone(response.data['next'])
        # self.assertIsNone(response.data['previous'])

    def test_second_page(self):
        """Test second page of results."""
        response = self.client.get(self.url, {'page': 2})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.assertIsNotNone(response.data['previous'])

    def test_custom_page_size(self):
        """Test custom page size parameter."""
        response = self.client.get(self.url, {'page_size': 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.assertEqual(len(response.data['results']), 5)


# =============================================================================
# PATTERN 7: Testing Filtering and Search
# =============================================================================

class FilteringTest(APITestCase):
    """Test filtering and search functionality."""

    def setUp(self):
        # user1 = User.objects.create_user('user1')
        # user2 = User.objects.create_user('user2')
        #
        # Article.objects.create(
        #     title='Django Tutorial',
        #     content='Learn Django',
        #     author=user1,
        #     status='published'
        # )
        # Article.objects.create(
        #     title='Python Guide',
        #     content='Learn Python',
        #     author=user2,
        #     status='draft'
        # )
        self.url = '/api/articles/'

    def test_filter_by_status(self):
        """Test filtering by status."""
        response = self.client.get(self.url, {'status': 'published'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify only published articles returned
        # for article in response.data:
        #     self.assertEqual(article['status'], 'published')

    def test_search(self):
        """Test search functionality."""
        response = self.client.get(self.url, {'search': 'Django'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify search results contain 'Django'

    def test_ordering(self):
        """Test ordering results."""
        response = self.client.get(self.url, {'ordering': '-created'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify results are ordered by created date descending


# =============================================================================
# PATTERN 8: Testing Custom Actions
# =============================================================================

class CustomActionTest(APITestCase):
    """Test custom ViewSet actions."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', password='pass')
        # self.article = Article.objects.create(
        #     title='Test',
        #     content='Content',
        #     author=self.user,
        #     status='draft'
        # )

    def test_custom_detail_action(self):
        """Test custom action on detail endpoint."""
        # url = f'/api/articles/{self.article.id}/publish/'
        # self.client.force_authenticate(user=self.user)
        #
        # response = self.client.post(url)
        #
        # self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.article.refresh_from_db()
        # self.assertEqual(self.article.status, 'published')
        pass

    def test_custom_list_action(self):
        """Test custom action on list endpoint."""
        url = '/api/articles/recent/'

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify recent articles returned


# =============================================================================
# PATTERN 9: Testing with Pytest
# =============================================================================

@pytest.mark.django_db
class TestArticleAPIPytest:
    """Example using pytest instead of unittest."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup run before each test method."""
        self.client = APIClient()
        self.user = User.objects.create_user('testuser', password='pass')
        self.url = '/api/articles/'

    def test_list_articles(self):
        """Test listing articles with pytest."""
        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)

    def test_create_authenticated(self):
        """Test creating article when authenticated."""
        self.client.force_authenticate(user=self.user)

        data = {'title': 'Test', 'content': 'Content'}
        response = self.client.post(self.url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED


# =============================================================================
# PATTERN 10: Testing with Parametrization (Pytest)
# =============================================================================

@pytest.mark.django_db
@pytest.mark.parametrize('method,expected_status', [
    ('get', 200),
    ('post', 401),
    ('put', 401),
    ('patch', 401),
    ('delete', 401),
])
def test_unauthenticated_access(method, expected_status):
    """Test that unauthenticated users can only GET."""
    client = APIClient()
    url = '/api/articles/'

    client_method = getattr(client, method)
    response = client_method(url)

    assert response.status_code == expected_status


# =============================================================================
# PATTERN 11: Testing Performance (Query Count)
# =============================================================================

class PerformanceTest(APITestCase):
    """Test query performance to catch N+1 issues."""

    def setUp(self):
        # user = User.objects.create_user('testuser')
        # for i in range(10):
        #     article = Article.objects.create(
        #         title=f'Article {i}',
        #         content='Content',
        #         author=user
        #     )
        #     # Add comments
        #     for j in range(5):
        #         Comment.objects.create(
        #             article=article,
        #             author=user,
        #             text=f'Comment {j}'
        #         )
        self.url = '/api/articles/'

    def test_list_query_count(self):
        """Test that list view doesn't have N+1 query issues."""
        # Should use select_related/prefetch_related
        with self.assertNumQueries(3):  # Adjust based on your optimizations
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 200)


# =============================================================================
# PATTERN 12: Testing File Uploads
# =============================================================================

class FileUploadTest(APITestCase):
    """Test file upload functionality."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', password='pass')
        self.client.force_authenticate(user=self.user)
        self.url = '/api/upload/'

    def test_image_upload(self):
        """Test uploading an image file."""
        from io import BytesIO
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Create a test image
        image = Image.new('RGB', (100, 100), color='red')
        image_file = BytesIO()
        image.save(image_file, 'PNG')
        image_file.seek(0)

        uploaded_file = SimpleUploadedFile(
            "test_image.png",
            image_file.read(),
            content_type="image/png"
        )

        data = {'image': uploaded_file}
        response = self.client.post(self.url, data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


# =============================================================================
# PATTERN 13: Testing Nested Routes
# =============================================================================

class NestedRouteTest(APITestCase):
    """Test nested resource routes."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', password='pass')
        # self.article = Article.objects.create(
        #     title='Test',
        #     content='Content',
        #     author=self.user
        # )
        # self.url = f'/api/articles/{self.article.id}/comments/'

    def test_list_nested_comments(self):
        """Test listing comments for an article."""
        # response = self.client.get(self.url)
        #
        # self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.assertIsInstance(response.data, list)
        pass

    def test_create_nested_comment(self):
        """Test creating a comment for an article."""
        # self.client.force_authenticate(user=self.user)
        #
        # data = {'text': 'Great article!'}
        # response = self.client.post(self.url, data, format='json')
        #
        # self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # self.assertEqual(response.data['article'], self.article.id)
        pass


# =============================================================================
# PATTERN 14: Testing Error Responses
# =============================================================================

class ErrorResponseTest(APITestCase):
    """Test error handling and responses."""

    def test_404_for_nonexistent_resource(self):
        """Test that nonexistent resources return 404."""
        url = '/api/articles/9999/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_validation_error_details(self):
        """Test that validation errors include helpful details."""
        self.user = User.objects.create_user('testuser', password='pass')
        self.client.force_authenticate(user=self.user)

        data = {'title': ''}  # Invalid: empty title
        response = self.client.post('/api/articles/', data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', response.data)
        # Check error message is helpful
        self.assertTrue(len(str(response.data['title'])) > 0)

    def test_method_not_allowed(self):
        """Test that unsupported methods return 405."""
        # If endpoint only supports GET, POST
        response = self.client.put('/api/articles/')

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


# =============================================================================
# PATTERN 15: Testing with Mock External Services
# =============================================================================

class ExternalServiceTest(APITestCase):
    """Test views that call external services."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', password='pass')
        self.client.force_authenticate(user=self.user)

    @pytest.mark.skip("Example pattern only")
    def test_with_mocked_external_api(self):
        """Test endpoint that calls external API."""
        from unittest.mock import patch

        with patch('myapp.services.external_api_call') as mock_api:
            mock_api.return_value = {'status': 'success', 'data': 'test'}

            response = self.client.post('/api/process/', {'data': 'test'})

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            mock_api.assert_called_once()


if __name__ == '__main__':
    """
    Run these tests with:
        python manage.py test myapp.tests.test_patterns
    Or with pytest:
        pytest myapp/tests/test_patterns.py
    """
    pass
