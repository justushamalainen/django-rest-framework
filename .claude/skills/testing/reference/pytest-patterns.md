# Pytest Patterns for DRF

Guide to using pytest with Django REST Framework, including fixtures, parametrization, and markers.

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
addopts =
    --reuse-db
    --nomigrations
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
```

### conftest.py - Shared Fixtures

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
        is_staff=True
    )
```

## Basic Pytest Usage

### Simple Test Functions

```python
import pytest
from rest_framework import status


@pytest.mark.django_db
def test_article_list(api_client):
    """Test listing articles."""
    response = api_client.get('/api/articles/')

    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.data, list)


@pytest.mark.django_db
def test_create_article(authenticated_client):
    """Test creating an article."""
    data = {'title': 'Test Article', 'content': 'Test content'}
    response = authenticated_client.post('/api/articles/', data, format='json')

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

### Model Fixtures

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

Factory fixtures create multiple instances with different data:

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


@pytest.mark.django_db
def test_multiple_articles(api_client, article_factory, user):
    """Create multiple articles for testing."""
    article_factory(title='First', author=user)
    article_factory(title='Second', author=user)
    article_factory(title='Third', author=user)

    response = api_client.get('/api/articles/')
    assert len(response.data) == 3
```

### Autouse Fixtures

Automatically run for every test:

```python
@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test."""
    from django.core.cache import cache
    cache.clear()
```

## Parametrization

### Basic Parametrization

Test multiple scenarios with one test function:

```python
@pytest.mark.django_db
@pytest.mark.parametrize('status_code,data', [
    (201, {'title': 'Valid Title', 'content': 'Valid content'}),
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
@pytest.mark.parametrize('method,expected_status', [
    ('get', 200),
    ('post', 401),  # Unauthenticated
    ('put', 401),
    ('delete', 401),
])
def test_unauthenticated_access(api_client, method, expected_status):
    """Test unauthenticated access to endpoints."""
    client_method = getattr(api_client, method)
    response = client_method('/api/articles/')
    assert response.status_code == expected_status
```

### Parametrize with IDs

Use IDs to make test names more readable:

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

    response = api_client.delete(f'/api/articles/{article.id}/')

    if can_delete:
        assert response.status_code == 204
    else:
        assert response.status_code in [401, 403]
```

## Pytest Marks

### Database Access Mark

```python
# Mark test as requiring database access
@pytest.mark.django_db
def test_with_database(api_client):
    response = api_client.get('/api/articles/')
    assert response.status_code == 200
```

### Custom Marks

Define and use custom marks:

```python
# In conftest.py
def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")


# Use custom marks
@pytest.mark.slow
@pytest.mark.django_db
def test_expensive_operation(api_client):
    """Test that takes a long time."""
    pass


@pytest.mark.integration
@pytest.mark.django_db
def test_full_workflow(api_client, user):
    """Test complete user workflow."""
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
```

### Skip and Skipif

```python
import sys

@pytest.mark.skip(reason="Not implemented yet")
def test_future_feature():
    pass


@pytest.mark.skipif(
    sys.version_info < (3, 9),
    reason="Requires Python 3.9+"
)
def test_python39_feature():
    pass
```

## Authentication Fixtures

### Multiple Client Fixtures

```python
@pytest.fixture
def authenticated_client(api_client, user):
    """Client authenticated as regular user."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def staff_client(api_client):
    """Client authenticated as staff user."""
    staff_user = User.objects.create_user('staff', is_staff=True)
    api_client.force_authenticate(user=staff_user)
    return api_client


@pytest.fixture
def admin_client(api_client, db):
    """Client authenticated as superuser."""
    admin = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
    api_client.force_authenticate(user=admin)
    return api_client
```

### Token Authentication Fixture

```python
@pytest.fixture
def token_client(api_client, user):
    """Client with token authentication."""
    from rest_framework.authtoken.models import Token

    token = Token.objects.create(user=user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return api_client
```

## Best Practices

1. **Use conftest.py for shared fixtures** - Keep test files clean
2. **Keep fixtures simple and focused** - One purpose per fixture
3. **Use factory fixtures for variation** - When you need multiple instances
4. **Mark database tests explicitly** - Use `@pytest.mark.django_db`
5. **Parametrize similar tests** - Reduce duplication
6. **Use meaningful fixture names** - `authenticated_client` not `client2`
7. **Document complex fixtures** - Add docstrings

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
- [Testing Views](./testing-views.md) - Testing views, authentication, and permissions
