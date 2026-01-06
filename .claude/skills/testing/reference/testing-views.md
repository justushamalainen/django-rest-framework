# Testing Views and Viewsets

Comprehensive guide to testing DRF views, viewsets, and API endpoints.

## Table of Contents

- [Testing Function-Based Views](#testing-function-based-views)
- [Testing Class-Based Views](#testing-class-based-views)
- [Testing ViewSets](#testing-viewsets)
- [Testing Generic Views](#testing-generic-views)
- [Testing Custom Actions](#testing-custom-actions)
- [Testing Pagination](#testing-pagination)
- [Testing Filtering and Search](#testing-filtering-and-search)
- [Testing Nested Routes](#testing-nested-routes)
- [Performance Testing](#performance-testing)

## Testing Function-Based Views

### Basic Function-Based View

```python
# views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET', 'POST'])
def article_list(request):
    if request.method == 'GET':
        articles = Article.objects.all()
        serializer = ArticleSerializer(articles, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = ArticleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
```

### Testing with APITestCase

```python
# tests.py
from rest_framework.test import APITestCase
from rest_framework import status


class ArticleListViewTest(APITestCase):
    def setUp(self):
        self.url = '/api/articles/'
        self.article = Article.objects.create(
            title='Test Article',
            content='Test content'
        )

    def test_get_article_list(self):
        """GET should return list of articles."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Test Article')

    def test_post_create_article(self):
        """POST should create a new article."""
        data = {'title': 'New Article', 'content': 'New content'}
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Article.objects.count(), 2)
        self.assertEqual(response.data['title'], 'New Article')

    def test_post_invalid_data(self):
        """POST with invalid data should return 400."""
        data = {'title': ''}  # Missing content, empty title
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', response.data)
```

### Testing with APIRequestFactory

```python
from rest_framework.test import APIRequestFactory
from myapp.views import article_list


def test_article_list_get():
    """Test GET request to article list."""
    factory = APIRequestFactory()
    request = factory.get('/api/articles/')

    response = article_list(request)
    response.render()

    assert response.status_code == 200
    assert len(response.data) > 0


def test_article_list_post():
    """Test POST request to create article."""
    factory = APIRequestFactory()
    data = {'title': 'Test', 'content': 'Content'}
    request = factory.post('/api/articles/', data, format='json')

    response = article_list(request)
    response.render()

    assert response.status_code == 201
```

### Testing Permission Decorators

```python
# views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_article(request):
    serializer = ArticleSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(author=request.user)
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)


# tests.py
class CreateArticleViewTest(APITestCase):
    def setUp(self):
        self.url = '/api/articles/create/'
        self.user = User.objects.create_user('testuser', password='pass')

    def test_unauthenticated_cannot_create(self):
        """Unauthenticated users should get 401."""
        data = {'title': 'Test', 'content': 'Content'}
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_can_create(self):
        """Authenticated users can create articles."""
        self.client.force_authenticate(user=self.user)

        data = {'title': 'Test', 'content': 'Content'}
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['author'], self.user.id)
```

## Testing Class-Based Views

### Testing APIView

```python
# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class ArticleList(APIView):
    def get(self, request):
        articles = Article.objects.all()
        serializer = ArticleSerializer(articles, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ArticleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# tests.py
class ArticleListAPIViewTest(APITestCase):
    def setUp(self):
        self.url = '/api/articles/'

    def test_get_empty_list(self):
        """GET with no articles returns empty list."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_get_with_articles(self):
        """GET returns all articles."""
        Article.objects.create(title='Article 1', content='Content 1')
        Article.objects.create(title='Article 2', content='Content 2')

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
```

### Testing with APIRequestFactory

```python
from rest_framework.test import APIRequestFactory
from myapp.views import ArticleList


def test_article_list_view():
    """Test ArticleList view directly."""
    factory = APIRequestFactory()
    view = ArticleList.as_view()

    # Test GET
    request = factory.get('/api/articles/')
    response = view(request)
    response.render()

    assert response.status_code == 200

    # Test POST
    data = {'title': 'Test', 'content': 'Content'}
    request = factory.post('/api/articles/', data, format='json')
    response = view(request)
    response.render()

    assert response.status_code == 201
```

## Testing ViewSets

### Basic ViewSet Testing

```python
# views.py
from rest_framework import viewsets


class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


# tests.py
class ArticleViewSetTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', password='pass')
        self.list_url = '/api/articles/'

    def test_list_articles(self):
        """Test list action."""
        Article.objects.create(title='Article 1', content='Content')
        Article.objects.create(title='Article 2', content='Content')

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_retrieve_article(self):
        """Test retrieve action."""
        article = Article.objects.create(title='Test', content='Content')
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
        """Test update action."""
        article = Article.objects.create(
            title='Original',
            content='Content',
            author=self.user
        )
        self.client.force_authenticate(user=self.user)

        url = f'{self.list_url}{article.id}/'
        data = {'title': 'Updated', 'content': 'Updated content'}
        response = self.client.put(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        article.refresh_from_db()
        self.assertEqual(article.title, 'Updated')

    def test_partial_update_article(self):
        """Test partial_update action."""
        article = Article.objects.create(
            title='Original',
            content='Content',
            author=self.user
        )
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
        article = Article.objects.create(
            title='Test',
            content='Content',
            author=self.user
        )
        self.client.force_authenticate(user=self.user)

        url = f'{self.list_url}{article.id}/'
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Article.objects.count(), 0)
```

### Testing ViewSet with APIRequestFactory

```python
from rest_framework.test import APIRequestFactory
from myapp.views import ArticleViewSet


def test_viewset_list():
    """Test viewset list action."""
    factory = APIRequestFactory()
    request = factory.get('/api/articles/')
    view = ArticleViewSet.as_view({'get': 'list'})

    response = view(request)
    response.render()

    assert response.status_code == 200


def test_viewset_retrieve():
    """Test viewset retrieve action."""
    article = Article.objects.create(title='Test', content='Content')

    factory = APIRequestFactory()
    request = factory.get(f'/api/articles/{article.id}/')
    view = ArticleViewSet.as_view({'get': 'retrieve'})

    response = view(request, pk=article.id)
    response.render()

    assert response.status_code == 200
    assert response.data['title'] == 'Test'
```

## Testing Generic Views

### Testing List and Create Views

```python
# views.py
from rest_framework import generics


class ArticleListCreateView(generics.ListCreateAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


# tests.py
class ArticleListCreateViewTest(APITestCase):
    def setUp(self):
        self.url = '/api/articles/'
        self.user = User.objects.create_user('testuser', password='pass')

    def test_list_articles(self):
        """GET returns list of articles."""
        Article.objects.create(title='Test 1', content='Content 1')
        Article.objects.create(title='Test 2', content='Content 2')

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_create_authenticated(self):
        """POST creates article when authenticated."""
        self.client.force_authenticate(user=self.user)

        data = {'title': 'New', 'content': 'Content'}
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
```

### Testing Retrieve, Update, Destroy Views

```python
# views.py
class ArticleDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


# tests.py
class ArticleDetailViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', password='pass')
        self.article = Article.objects.create(
            title='Test',
            content='Content',
            author=self.user
        )
        self.url = f'/api/articles/{self.article.id}/'

    def test_retrieve_article(self):
        """GET returns article details."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test')

    def test_retrieve_nonexistent(self):
        """GET for nonexistent article returns 404."""
        url = '/api/articles/9999/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_article(self):
        """PUT updates article."""
        self.client.force_authenticate(user=self.user)

        data = {'title': 'Updated', 'content': 'Updated content'}
        response = self.client.put(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.article.refresh_from_db()
        self.assertEqual(self.article.title, 'Updated')

    def test_partial_update_article(self):
        """PATCH partially updates article."""
        self.client.force_authenticate(user=self.user)

        data = {'title': 'Patched'}
        response = self.client.patch(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.article.refresh_from_db()
        self.assertEqual(self.article.title, 'Patched')

    def test_delete_article(self):
        """DELETE removes article."""
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Article.objects.filter(id=self.article.id).exists())
```

## Testing Custom Actions

### Testing @action Decorator

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
        return Response({'status': 'article published'})

    @action(detail=False, methods=['get'])
    def recent(self, request):
        recent_articles = Article.objects.order_by('-created')[:5]
        serializer = self.get_serializer(recent_articles, many=True)
        return Response(serializer.data)


# tests.py
class ArticleCustomActionsTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', password='pass')
        self.article = Article.objects.create(
            title='Test',
            content='Content',
            status='draft'
        )

    def test_publish_action(self):
        """POST to publish action changes status."""
        self.client.force_authenticate(user=self.user)

        url = f'/api/articles/{self.article.id}/publish/'
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.article.refresh_from_db()
        self.assertEqual(self.article.status, 'published')

    def test_recent_action(self):
        """GET recent action returns recent articles."""
        # Create multiple articles
        for i in range(10):
            Article.objects.create(
                title=f'Article {i}',
                content='Content'
            )

        url = '/api/articles/recent/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)
```

## Testing Pagination

### Testing Paginated Lists

```python
# views.py
from rest_framework.pagination import PageNumberPagination


class ArticlePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    pagination_class = ArticlePagination


# tests.py
class ArticlePaginationTest(APITestCase):
    def setUp(self):
        # Create 25 articles
        for i in range(25):
            Article.objects.create(
                title=f'Article {i}',
                content=f'Content {i}'
            )
        self.url = '/api/articles/'

    def test_pagination_first_page(self):
        """First page returns correct number of items."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 10)
        self.assertIsNotNone(response.data['next'])
        self.assertIsNone(response.data['previous'])

    def test_pagination_second_page(self):
        """Second page returns correct items."""
        response = self.client.get(self.url, {'page': 2})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 10)
        self.assertIsNotNone(response.data['previous'])

    def test_pagination_last_page(self):
        """Last page returns remaining items."""
        response = self.client.get(self.url, {'page': 3})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)
        self.assertIsNone(response.data['next'])

    def test_custom_page_size(self):
        """Custom page size parameter works."""
        response = self.client.get(self.url, {'page_size': 5})

        self.assertEqual(len(response.data['results']), 5)

    def test_invalid_page(self):
        """Invalid page number returns 404."""
        response = self.client.get(self.url, {'page': 999})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
```

## Testing Filtering and Search

### Testing Filter Backends

```python
# views.py
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters


class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'author']
    search_fields = ['title', 'content']
    ordering_fields = ['created', 'title']


# tests.py
class ArticleFilteringTest(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user('user1')
        self.user2 = User.objects.create_user('user2')

        Article.objects.create(
            title='Django Article',
            content='About Django',
            author=self.user1,
            status='published'
        )
        Article.objects.create(
            title='Python Article',
            content='About Python',
            author=self.user2,
            status='draft'
        )
        self.url = '/api/articles/'

    def test_filter_by_status(self):
        """Filter by status returns correct articles."""
        response = self.client.get(self.url, {'status': 'published'})

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Django Article')

    def test_filter_by_author(self):
        """Filter by author returns correct articles."""
        response = self.client.get(self.url, {'author': self.user1.id})

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['author'], self.user1.id)

    def test_search(self):
        """Search returns matching articles."""
        response = self.client.get(self.url, {'search': 'Django'})

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Django Article')

    def test_ordering(self):
        """Ordering sorts results correctly."""
        response = self.client.get(self.url, {'ordering': 'title'})

        titles = [item['title'] for item in response.data]
        self.assertEqual(titles, ['Django Article', 'Python Article'])

        response = self.client.get(self.url, {'ordering': '-title'})
        titles = [item['title'] for item in response.data]
        self.assertEqual(titles, ['Python Article', 'Django Article'])
```

## Testing Nested Routes

### Testing Nested ViewSets

```python
# views.py
class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer

    def get_queryset(self):
        return Comment.objects.filter(article_id=self.kwargs['article_pk'])

    def perform_create(self, serializer):
        serializer.save(article_id=self.kwargs['article_pk'])


# urls.py (using drf-nested-routers)
from rest_framework_nested import routers

router = routers.SimpleRouter()
router.register(r'articles', ArticleViewSet)

articles_router = routers.NestedSimpleRouter(router, r'articles', lookup='article')
articles_router.register(r'comments', CommentViewSet, basename='article-comments')


# tests.py
class NestedCommentTest(APITestCase):
    def setUp(self):
        self.article = Article.objects.create(
            title='Test Article',
            content='Content'
        )
        self.url = f'/api/articles/{self.article.id}/comments/'

    def test_list_comments(self):
        """GET lists comments for specific article."""
        Comment.objects.create(article=self.article, text='Comment 1')
        Comment.objects.create(article=self.article, text='Comment 2')

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_create_comment(self):
        """POST creates comment for article."""
        data = {'text': 'New comment'}
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Comment.objects.filter(article=self.article).count(), 1)
```

## Performance Testing

### Testing Query Performance

```python
class ArticlePerformanceTest(APITestCase):
    def setUp(self):
        # Create test data with relationships
        self.user = User.objects.create_user('testuser')
        for i in range(10):
            article = Article.objects.create(
                title=f'Article {i}',
                content='Content',
                author=self.user
            )
            # Add comments
            for j in range(5):
                Comment.objects.create(
                    article=article,
                    text=f'Comment {j}'
                )

    def test_list_query_count(self):
        """Test N+1 query issues."""
        url = '/api/articles/'

        # Should use select_related/prefetch_related to minimize queries
        with self.assertNumQueries(3):  # Adjust based on your optimization
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

    def test_detail_query_count(self):
        """Test detail view query efficiency."""
        article = Article.objects.first()
        url = f'/api/articles/{article.id}/'

        with self.assertNumQueries(2):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
```

## Best Practices

1. **Test all HTTP methods** - GET, POST, PUT, PATCH, DELETE
2. **Test authentication and permissions** - Both success and failure cases
3. **Test validation** - Both valid and invalid data
4. **Test edge cases** - Empty lists, nonexistent resources, boundary conditions
5. **Use assertNumQueries** - Catch N+1 query problems
6. **Test with multiple users** - Ensure proper isolation
7. **Check database state** - Verify objects are created/updated/deleted
8. **Test pagination and filtering** - Ensure correct data is returned

## See Also

- [Test Clients Reference](./test-clients.md) - APIClient and APIRequestFactory
- [Testing Serializers](./testing-serializers.md) - Testing serializers
- [Testing Auth & Permissions](./testing-auth-perms.md) - Authentication and permissions
- [Test Pattern Examples](./examples/test-patterns.py) - Working code examples
