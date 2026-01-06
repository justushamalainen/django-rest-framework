# Pytest Patterns for DRF

Guide to using pytest with Django REST Framework, including fixtures, parametrization, and markers.

## Table of Contents

- [Setup and Configuration](#setup-and-configuration)
- [Basic Pytest Usage](#basic-pytest-usage)
- [Fixtures](#fixtures)
- [Parametrization](#parametrization)
- [Pytest Marks](#pytest-marks)
- [API Client Fixtures](#api-client-fixtures)
- [Database Fixtures](#database-fixtures)
- [Authentication Fixtures](#authentication-fixtures)
- [Advanced Patterns](#advanced-patterns)

## Setup and Configuration

### Installation

```bash
pip install pytest pytest-django
```

### pytest.ini Configuration

```ini
[pytest]
DJANGO_SETTINGS_MODULE = myproject.settings
python_files = tests.py test_*.py *_tests.py
python_classes = Test*
python_functions = test_*
addopts =
    --reuse-db
    --nomigrations
    --cov=myapp
    --cov-report=html
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

### conftest.py

Create a `conftest.py` file in your test directory:

```python
import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User


@pytest.fixture
def api_client():
    """Provide an API client instance."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """Provide an authenticated API client."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def staff_user(db):
    """Create a staff user."""
    return User.objects.create_user(
        username='staffuser',
        email='staff@example.com',
        password='staffpass123',
        is_staff=True
    )
```

## Basic Pytest Usage

### Simple Test Function

```python
import pytest
from rest_framework import status


@pytest.mark.django_db
def test_article_list(api_client):
    """Test listing articles."""
    response = api_client.get('/api/articles/')

    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.data, list)
```

### Using db Fixture

```python
@pytest.mark.django_db
def test_create_article(api_client, user):
    """Test creating an article."""
    api_client.force_authenticate(user=user)

    data = {'title': 'Test Article', 'content': 'Test content'}
    response = api_client.post('/api/articles/', data, format='json')

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['title'] == 'Test Article'
```

### Test Classes

```python
@pytest.mark.django_db
class TestArticleAPI:
    """Group related tests in a class."""

    def test_list_articles(self, api_client):
        response = api_client.get('/api/articles/')
        assert response.status_code == status.HTTP_200_OK

    def test_create_article(self, authenticated_client):
        data = {'title': 'Test', 'content': 'Content'}
        response = authenticated_client.post('/api/articles/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
```

## Fixtures

### Basic Fixture Pattern

```python
@pytest.fixture
def article(db, user):
    """Create a test article."""
    from myapp.models import Article
    return Article.objects.create(
        title='Test Article',
        content='Test content',
        author=user
    )


@pytest.mark.django_db
def test_article_detail(api_client, article):
    """Test retrieving an article."""
    response = api_client.get(f'/api/articles/{article.id}/')
    assert response.status_code == 200
    assert response.data['title'] == article.title
```

### Factory Fixtures

```python
@pytest.fixture
def article_factory(db):
    """Factory fixture for creating articles."""
    def create_article(**kwargs):
        from myapp.models import Article
        defaults = {
            'title': 'Test Article',
            'content': 'Test content',
        }
        defaults.update(kwargs)
        return Article.objects.create(**defaults)
    return create_article


def test_multiple_articles(api_client, article_factory, user):
    """Create multiple articles for testing."""
    article1 = article_factory(title='First', author=user)
    article2 = article_factory(title='Second', author=user)
    article3 = article_factory(title='Third', author=user)

    response = api_client.get('/api/articles/')
    assert len(response.data) == 3
```

### Fixture Scopes

```python
# Function scope (default) - created for each test function
@pytest.fixture
def user(db):
    return User.objects.create_user('testuser')


# Class scope - created once per test class
@pytest.fixture(scope='class')
def user_class(django_db_blocker):
    with django_db_blocker.unblock():
        return User.objects.create_user('testuser')


# Module scope - created once per module
@pytest.fixture(scope='module')
def user_module(django_db_blocker):
    with django_db_blocker.unblock():
        return User.objects.create_user('testuser')


# Session scope - created once per test session
@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """Load initial data once per session."""
    with django_db_blocker.unblock():
        # Load fixtures or create initial data
        pass
```

### Autouse Fixtures

```python
@pytest.fixture(autouse=True)
def setup_test_environment():
    """Automatically run for every test."""
    # Setup code
    yield
    # Teardown code


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test."""
    from django.core.cache import cache
    cache.clear()
```

## Parametrization

### Basic Parametrization

```python
@pytest.mark.django_db
@pytest.mark.parametrize('status_code,data', [
    (200, {'title': 'Valid Title', 'content': 'Valid content'}),
    (400, {'title': '', 'content': 'Valid content'}),  # Missing title
    (400, {'title': 'Valid', 'content': ''}),  # Missing content
])
def test_article_validation(authenticated_client, status_code, data):
    """Test various validation scenarios."""
    response = authenticated_client.post('/api/articles/', data, format='json')
    assert response.status_code == status_code
```

### Multiple Parameters

```python
@pytest.mark.django_db
@pytest.mark.parametrize('method,url,expected_status', [
    ('get', '/api/articles/', 200),
    ('post', '/api/articles/', 401),  # Unauthenticated
    ('put', '/api/articles/1/', 401),
    ('patch', '/api/articles/1/', 401),
    ('delete', '/api/articles/1/', 401),
])
def test_unauthenticated_access(api_client, method, url, expected_status):
    """Test unauthenticated access to various endpoints."""
    client_method = getattr(api_client, method)
    response = client_method(url)
    assert response.status_code == expected_status
```

### Parametrize with IDs

```python
@pytest.mark.django_db
@pytest.mark.parametrize(
    'user_type,can_delete',
    [
        ('author', True),
        ('staff', True),
        ('other_user', False),
        ('anonymous', False),
    ],
    ids=['author-can-delete', 'staff-can-delete', 'other-cannot', 'anonymous-cannot']
)
def test_delete_permissions(api_client, article, user, user_type, can_delete):
    """Test delete permissions for different user types."""
    if user_type == 'author':
        api_client.force_authenticate(user=article.author)
    elif user_type == 'staff':
        staff = User.objects.create_user('staff', is_staff=True)
        api_client.force_authenticate(user=staff)
    elif user_type == 'other_user':
        other = User.objects.create_user('other')
        api_client.force_authenticate(user=other)
    # anonymous - no authentication

    response = api_client.delete(f'/api/articles/{article.id}/')

    if can_delete:
        assert response.status_code == 204
    else:
        assert response.status_code in [401, 403]
```

### Fixture Parametrization

```python
@pytest.fixture(params=['json', 'multipart'])
def format_type(request):
    """Test with multiple content types."""
    return request.param


@pytest.mark.django_db
def test_create_with_different_formats(authenticated_client, format_type):
    """Test creating articles with different content types."""
    data = {'title': 'Test', 'content': 'Content'}
    response = authenticated_client.post(
        '/api/articles/',
        data,
        format=format_type
    )
    assert response.status_code == 201
```

## Pytest Marks

### Built-in Django Marks

```python
# Mark test as requiring database access
@pytest.mark.django_db
def test_with_database(api_client):
    response = api_client.get('/api/articles/')
    assert response.status_code == 200


# Allow database access with transaction support
@pytest.mark.django_db(transaction=True)
def test_with_transactions(api_client):
    with transaction.atomic():
        # Test transaction behavior
        pass


# Reset sequences (useful for PostgreSQL)
@pytest.mark.django_db(reset_sequences=True)
def test_with_reset_sequences(api_client):
    # Primary keys will start from 1
    pass
```

### Custom Marks

```python
# Define custom marks in pytest.ini or conftest.py
import pytest

# In conftest.py
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: marks tests as slow"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )


# Use custom marks
@pytest.mark.slow
@pytest.mark.django_db
def test_expensive_operation(api_client):
    """Test that takes a long time."""
    # Slow test code
    pass


@pytest.mark.integration
@pytest.mark.django_db
def test_full_workflow(api_client, user):
    """Test complete user workflow."""
    # Integration test code
    pass
```

### Running Specific Marks

```bash
# Run only slow tests
pytest -m slow

# Run all except slow tests
pytest -m "not slow"

# Run integration tests
pytest -m integration

# Combine marks
pytest -m "integration and not slow"
```

### Skip and Skipif

```python
@pytest.mark.skip(reason="Not implemented yet")
def test_future_feature():
    pass


@pytest.mark.skipif(
    sys.version_info < (3, 9),
    reason="Requires Python 3.9+"
)
def test_python39_feature():
    pass


# Skip entire class
@pytest.mark.skip
class TestFutureAPI:
    def test_one(self):
        pass
```

### Xfail (Expected Failure)

```python
@pytest.mark.xfail(reason="Known bug #123")
def test_known_bug():
    """Test that currently fails due to known issue."""
    assert False


@pytest.mark.xfail(strict=True)
def test_must_fail():
    """Test that MUST fail (fails if it passes)."""
    assert False
```

## API Client Fixtures

### Multiple Client Fixtures

```python
@pytest.fixture
def api_client():
    """Unauthenticated API client."""
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user):
    """Client authenticated as regular user."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def staff_client(api_client, staff_user):
    """Client authenticated as staff user."""
    api_client.force_authenticate(user=staff_user)
    return api_client


@pytest.fixture
def admin_client(api_client, db):
    """Client authenticated as superuser."""
    admin = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='admin123'
    )
    api_client.force_authenticate(user=admin)
    return api_client
```

### Token Authentication Fixture

```python
@pytest.fixture
def user_with_token(db):
    """User with authentication token."""
    from rest_framework.authtoken.models import Token

    user = User.objects.create_user(
        username='testuser',
        password='testpass'
    )
    token = Token.objects.create(user=user)
    user.token = token  # Attach token for convenience
    return user


@pytest.fixture
def token_client(api_client, user_with_token):
    """Client with token authentication."""
    api_client.credentials(
        HTTP_AUTHORIZATION=f'Token {user_with_token.token.key}'
    )
    return api_client
```

## Database Fixtures

### Model Fixtures

```python
@pytest.fixture
def category(db):
    """Create a test category."""
    from myapp.models import Category
    return Category.objects.create(name='Test Category')


@pytest.fixture
def article_with_category(db, user, category):
    """Create article with category."""
    from myapp.models import Article
    return Article.objects.create(
        title='Test Article',
        content='Content',
        author=user,
        category=category
    )


@pytest.fixture
def articles(db, user):
    """Create multiple articles."""
    from myapp.models import Article
    return [
        Article.objects.create(
            title=f'Article {i}',
            content=f'Content {i}',
            author=user
        )
        for i in range(5)
    ]
```

### Factory Boy Integration

```bash
pip install factory-boy
```

```python
import factory
from myapp.models import Article


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')


class ArticleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Article

    title = factory.Sequence(lambda n: f'Article {n}')
    content = factory.Faker('paragraph')
    author = factory.SubFactory(UserFactory)


# Use in fixtures
@pytest.fixture
def article(db):
    return ArticleFactory()


@pytest.fixture
def articles(db):
    return ArticleFactory.create_batch(10)


# Use in tests
@pytest.mark.django_db
def test_with_factory(api_client):
    article = ArticleFactory()
    response = api_client.get(f'/api/articles/{article.id}/')
    assert response.status_code == 200
```

## Authentication Fixtures

### JWT Token Fixture

```python
@pytest.fixture
def jwt_token(user):
    """Create JWT token for user."""
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


@pytest.fixture
def jwt_client(api_client, jwt_token):
    """Client with JWT authentication."""
    api_client.credentials(
        HTTP_AUTHORIZATION=f'Bearer {jwt_token["access"]}'
    )
    return api_client
```

### Session Authentication Fixture

```python
@pytest.fixture
def session_client(api_client, user):
    """Client with session authentication."""
    api_client.login(username=user.username, password='testpass123')
    return api_client
```

## Advanced Patterns

### Fixture Chains

```python
@pytest.fixture
def user(db):
    return User.objects.create_user('testuser', password='pass')


@pytest.fixture
def profile(user):
    """Profile depends on user."""
    from myapp.models import Profile
    return Profile.objects.create(user=user, bio='Test bio')


@pytest.fixture
def article(user, profile):
    """Article depends on user and profile."""
    from myapp.models import Article
    return Article.objects.create(
        title='Test',
        author=user,
        author_profile=profile
    )


@pytest.mark.django_db
def test_with_chained_fixtures(api_client, article):
    """All fixtures automatically created."""
    response = api_client.get(f'/api/articles/{article.id}/')
    assert response.status_code == 200
```

### Mocking in Pytest

```python
from unittest.mock import patch, MagicMock


@pytest.mark.django_db
@patch('myapp.services.external_api_call')
def test_with_mock(mock_api, api_client, user):
    """Test with mocked external service."""
    mock_api.return_value = {'status': 'success'}

    api_client.force_authenticate(user=user)
    response = api_client.post('/api/process/', {'data': 'test'})

    assert response.status_code == 200
    mock_api.assert_called_once()
```

### Using tmpdir for File Tests

```python
def test_file_upload(authenticated_client, tmpdir):
    """Test file upload with temporary directory."""
    # Create temporary file
    file_path = tmpdir.join("test.txt")
    file_path.write("test content")

    with open(file_path, 'rb') as f:
        response = authenticated_client.post(
            '/api/upload/',
            {'file': f},
            format='multipart'
        )

    assert response.status_code == 201
```

### Testing with Settings Override

```python
@pytest.mark.django_db
@pytest.mark.override_settings(DEBUG=True)
def test_with_debug(api_client):
    """Test with DEBUG mode enabled."""
    response = api_client.get('/api/articles/')
    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.override_settings(
    REST_FRAMEWORK={
        'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
        'PAGE_SIZE': 10
    }
)
def test_pagination(api_client):
    """Test with custom pagination settings."""
    response = api_client.get('/api/articles/')
    assert 'results' in response.data
```

## Best Practices

1. **Use conftest.py for shared fixtures** - Keep test files clean
2. **Keep fixtures simple and focused** - One purpose per fixture
3. **Use factory fixtures for variation** - When you need multiple instances with different data
4. **Mark database tests explicitly** - Use `@pytest.mark.django_db`
5. **Parametrize similar tests** - Reduce duplication
6. **Use meaningful fixture names** - `authenticated_client` not `client2`
7. **Leverage fixture scopes** - Optimize test performance
8. **Document complex fixtures** - Add docstrings explaining what they provide

## Running Tests

```bash
# Run all tests
pytest

# Run specific file
pytest tests/test_api.py

# Run specific test
pytest tests/test_api.py::test_article_list

# Run with markers
pytest -m "not slow"

# Run with coverage
pytest --cov=myapp --cov-report=html

# Run in parallel (requires pytest-xdist)
pytest -n auto

# Verbose output
pytest -v

# Show print statements
pytest -s

# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf
```

## See Also

- [Test Clients Reference](./test-clients.md) - APIClient and APIRequestFactory
- [Testing Views](./testing-views.md) - Testing views and viewsets
- [Test Pattern Examples](./examples/test-patterns.py) - Working code examples
