# Serializer Types

DRF provides several serializer classes for different use cases. Understanding when to use each is critical for efficient development.

## Overview

| Type | Use Case | Auto Fields | Auto Validation | create()/update() | Relations Default |
|------|----------|-------------|-----------------|-------------------|-------------------|
| `Serializer` | Non-model data, custom logic | No | No | Manual | N/A |
| `ModelSerializer` | Model-backed APIs (most common) | Yes | Yes | Provided | PrimaryKey |
| `HyperlinkedModelSerializer` | HATEOAS, discoverable APIs | Yes | Yes | Provided | Hyperlinked |
| `ListSerializer` | Batch operations | N/A | Yes | Manual | N/A |

## Base Serializer Class

The `Serializer` class is the base for all serializers. Use it when you need complete control.

### When to Use

- Non-model data (forms, computed data, external APIs)
- Complex custom validation logic
- Data that doesn't map to a Django model
- When ModelSerializer is too "magic" for your needs

### Example: Basic Serializer

```python
from rest_framework import serializers

class LoginSerializer(serializers.Serializer):
    """Login form - not backed by a model"""
    username = serializers.CharField(max_length=100)
    password = serializers.CharField(
        max_length=128,
        write_only=True,  # Don't include in responses
        style={'input_type': 'password'}
    )
    remember_me = serializers.BooleanField(required=False, default=False)

    def validate_username(self, value):
        """Field-level validation"""
        if '@' in value:
            # Allow email as username
            return value.lower()
        return value

    def validate(self, attrs):
        """Object-level validation"""
        from django.contrib.auth import authenticate

        user = authenticate(
            username=attrs['username'],
            password=attrs['password']
        )
        if user is None:
            raise serializers.ValidationError("Invalid credentials")

        attrs['user'] = user
        return attrs

    def create(self, validated_data):
        """Custom create logic"""
        # For a login serializer, we don't create anything
        # Just return the user
        return validated_data['user']

# Usage
serializer = LoginSerializer(data={'username': 'john', 'password': 'secret'})
if serializer.is_valid():
    user = serializer.save()
```

### Example: Computed Data Serializer

```python
class StatisticsSerializer(serializers.Serializer):
    """Statistics that aren't stored in the database"""
    total_books = serializers.IntegerField(read_only=True)
    total_authors = serializers.IntegerField(read_only=True)
    average_price = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        read_only=True
    )
    most_popular_genre = serializers.CharField(read_only=True)

    # No create() or update() - this is read-only

# Usage (manual data construction)
from django.db.models import Avg
stats = {
    'total_books': Book.objects.count(),
    'total_authors': Author.objects.count(),
    'average_price': Book.objects.aggregate(Avg('price'))['price__avg'],
    'most_popular_genre': 'Fiction',
}
serializer = StatisticsSerializer(stats)
return Response(serializer.data)
```

## ModelSerializer

The workhorse of DRF. Automatically generates fields and validators from a Django model.

### When to Use

- 80-90% of your API endpoints
- Standard CRUD operations on models
- When you want Django's validation rules
- When relationships should use primary keys

### Automatic Features

1. **Auto-generated fields** - All model fields become serializer fields
2. **Auto-validation** - Model validators (unique, max_length, etc.) are applied
3. **Default create()/update()** - Basic implementations provided
4. **UniqueValidator** - Automatic uniqueness checking

### Example: Basic ModelSerializer

```python
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey('Author', on_delete=models.CASCADE)
    isbn = models.CharField(max_length=13, unique=True)
    published_date = models.DateField()
    pages = models.IntegerField()

    class Meta:
        unique_together = [['title', 'author']]

# Minimal serializer - gets everything from the model
class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = '__all__'
        # Or explicitly list fields:
        # fields = ['id', 'title', 'author', 'isbn', 'published_date', 'pages']

# Usage
book = Book.objects.get(pk=1)
serializer = BookSerializer(book)
# Automatically includes all fields:
# {'id': 1, 'title': '...', 'author': 5, 'isbn': '...', ...}
```

### Meta Options

```python
class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book

        # Option 1: Include all fields
        fields = '__all__'

        # Option 2: Explicit field list (recommended)
        fields = ['id', 'title', 'author', 'isbn', 'published_date']

        # Option 3: Exclude specific fields
        exclude = ['internal_notes', 'legacy_id']

        # Make fields read-only
        read_only_fields = ['id', 'created_at', 'updated_at']

        # Customize fields without redefining them
        extra_kwargs = {
            'isbn': {'required': True, 'allow_blank': False},
            'pages': {'min_value': 1, 'max_value': 10000},
            'title': {'help_text': 'The book title'}
        }

        # Set depth for automatic nested representation (use sparingly!)
        depth = 1  # Auto-nest one level of relationships
```

### Customizing ModelSerializer

```python
class BookSerializer(serializers.ModelSerializer):
    # Override a field
    title = serializers.CharField(
        max_length=200,
        validators=[CustomTitleValidator()]
    )

    # Add computed field
    author_name = serializers.CharField(source='author.name', read_only=True)

    # Add method field
    is_new_release = serializers.SerializerMethodField()

    # Add related field with custom representation
    reviews_count = serializers.IntegerField(source='reviews.count', read_only=True)

    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'author_name', 'is_new_release', 'reviews_count']

    def get_is_new_release(self, obj):
        """SerializerMethodField calls get_<field_name>"""
        from datetime import date, timedelta
        return obj.published_date > date.today() - timedelta(days=90)

    def validate_title(self, value):
        """Field-level validation"""
        if 'spam' in value.lower():
            raise serializers.ValidationError("Title contains spam")
        return value

    def validate(self, attrs):
        """Object-level validation"""
        if attrs['pages'] < 10 and attrs['price'] > 100:
            raise serializers.ValidationError(
                "Short books cannot be expensive"
            )
        return attrs
```

## HyperlinkedModelSerializer

Like ModelSerializer, but relationships are represented as URLs instead of primary keys.

### When to Use

- Public APIs where discoverability matters
- HATEOAS-style APIs
- When clients should navigate via hyperlinks
- When you want self-documenting APIs

### Key Differences from ModelSerializer

1. Uses `url` field instead of `id` by default
2. Relationships are `HyperlinkedRelatedField` instead of `PrimaryKeyRelatedField`
3. Requires `view_name` for relationships
4. Needs `request` in serializer context

### Example

```python
class AuthorSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Author
        fields = ['url', 'name', 'email', 'books']
        # 'url' is auto-generated using 'author-detail' view name
        # 'books' is HyperlinkedRelatedField to 'book-detail'

class BookSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Book
        fields = ['url', 'title', 'author', 'isbn']

# views.py
from rest_framework import viewsets

class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

# urls.py
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'authors', AuthorViewSet, basename='author')
router.register(r'books', BookViewSet, basename='book')

# Output example:
# {
#     "url": "http://example.com/api/books/1/",
#     "title": "Django for Beginners",
#     "author": "http://example.com/api/authors/5/",
#     "isbn": "1234567890"
# }
```

### Customizing URL Field

```python
class BookSerializer(serializers.HyperlinkedModelSerializer):
    # Use custom field name instead of 'url'
    class Meta:
        model = Book
        fields = ['self', 'title', 'author']  # 'self' instead of 'url'

    # Set custom URL field name
    url_field_name = 'self'

    # Or just override the field
    self = serializers.HyperlinkedIdentityField(view_name='book-detail')
```

### Mixing Hyperlinked and PrimaryKey

```python
class BookSerializer(serializers.HyperlinkedModelSerializer):
    # Override specific relationships to use IDs
    author_id = serializers.PrimaryKeyRelatedField(
        source='author',
        queryset=Author.objects.all()
    )

    # Keep other relationships as hyperlinks
    publisher = serializers.HyperlinkedRelatedField(
        view_name='publisher-detail',
        queryset=Publisher.objects.all()
    )

    class Meta:
        model = Book
        fields = ['url', 'title', 'author_id', 'publisher']
```

## ListSerializer

Automatically used when `many=True` is passed. Handles lists of objects.

### When to Use

- Automatically used by DRF (you rarely instantiate this directly)
- Custom bulk create/update operations
- Custom list validation

### Automatic Usage

```python
# Single object
book = Book.objects.get(pk=1)
serializer = BookSerializer(book)

# Multiple objects - ListSerializer is used automatically
books = Book.objects.all()
serializer = BookSerializer(books, many=True)  # Returns ListSerializer

# Under the hood:
# BookSerializer(many=True) → BookSerializer.many_init() → ListSerializer(child=BookSerializer())
```

### Custom ListSerializer

```python
class BookListSerializer(serializers.ListSerializer):
    """Custom list serializer for bulk operations"""

    def create(self, validated_data):
        """Bulk create with transaction"""
        from django.db import transaction

        with transaction.atomic():
            books = [Book(**item) for item in validated_data]
            return Book.objects.bulk_create(books)

    def update(self, instances, validated_data):
        """Bulk update by matching IDs"""
        from django.db import transaction

        # Map instances by ID for O(1) lookup
        book_mapping = {book.id: book for book in instances}

        with transaction.atomic():
            for item in validated_data:
                book_id = item.get('id')
                if book_id and book_id in book_mapping:
                    book = book_mapping[book_id]
                    for attr, value in item.items():
                        setattr(book, attr, value)
                    book.save()

        return instances

    def validate(self, attrs):
        """List-level validation"""
        # Check for duplicate ISBNs in the batch
        isbns = [item['isbn'] for item in attrs]
        if len(isbns) != len(set(isbns)):
            raise serializers.ValidationError("Duplicate ISBNs in batch")
        return attrs

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['id', 'title', 'isbn']
        list_serializer_class = BookListSerializer  # Use custom list serializer

# Usage
data = [
    {'title': 'Book 1', 'isbn': '1234567890123'},
    {'title': 'Book 2', 'isbn': '9876543210987'},
]
serializer = BookSerializer(data=data, many=True)
if serializer.is_valid():
    books = serializer.save()  # Bulk create
```

## Comparison Matrix

### Feature Comparison

| Feature | Serializer | ModelSerializer | HyperlinkedModelSerializer |
|---------|-----------|-----------------|---------------------------|
| Auto field generation | ❌ | ✅ | ✅ |
| Auto validation | ❌ | ✅ | ✅ |
| Default create() | ❌ | ✅ | ✅ |
| Default update() | ❌ | ✅ | ✅ |
| Auto uniqueness validators | ❌ | ✅ | ✅ |
| Relations as IDs | N/A | ✅ | ❌ (URLs) |
| Relations as URLs | N/A | ❌ (IDs) | ✅ |
| Needs request context | ❌ | ❌ | ✅ (for URLs) |
| URL routing required | ❌ | ❌ | ✅ |
| Verbosity | High | Low | Low |
| Flexibility | High | Medium | Medium |

### Performance Comparison

| Serializer Type | Instantiation Speed | Memory Usage | Query Efficiency |
|----------------|---------------------|--------------|------------------|
| Serializer | Fast | Low | Manual |
| ModelSerializer | Medium (reflection) | Medium | Good (with optimization) |
| HyperlinkedModelSerializer | Medium (reflection) | Medium | Good (with optimization) |

**Note:** Performance differences are negligible in most cases. Choose based on functionality, not performance.

## Choosing the Right Serializer

### Use `Serializer` when:
- ✅ Data doesn't come from a model
- ✅ You need complete control over fields and validation
- ✅ You're building forms or input validators
- ✅ You're working with external APIs

### Use `ModelSerializer` when:
- ✅ You have a Django model
- ✅ You want standard CRUD operations
- ✅ You're okay with PrimaryKey relationships
- ✅ 80% of your use cases

### Use `HyperlinkedModelSerializer` when:
- ✅ You're building a public API
- ✅ API discoverability is important
- ✅ You want HATEOAS
- ✅ Clients should navigate via URLs

### Use `ListSerializer` (custom) when:
- ✅ You need bulk create/update operations
- ✅ You need list-level validation
- ✅ Standard many=True behavior isn't enough

## Advanced: Combining Serializer Types

You can mix serializer types in the same API:

```python
# Input: Use basic Serializer for validation
class BookCreateInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    author_id = serializers.IntegerField()
    isbn = serializers.CharField(max_length=13)

    def validate(self, attrs):
        # Custom business logic
        return attrs

# Output: Use ModelSerializer for representation
class BookOutputSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)

    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'isbn', 'created_at']

# View
@api_view(['POST'])
def create_book(request):
    # Validate with input serializer
    input_serializer = BookCreateInputSerializer(data=request.data)
    if input_serializer.is_valid():
        # Create the book
        book = Book.objects.create(**input_serializer.validated_data)

        # Return with output serializer
        output_serializer = BookOutputSerializer(book)
        return Response(output_serializer.data, status=201)

    return Response(input_serializer.errors, status=400)
```

This pattern provides maximum flexibility: strict input validation with rich output representation.
