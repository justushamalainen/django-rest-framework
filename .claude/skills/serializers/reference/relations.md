# Relational Fields Reference

DRF provides 5 relational field types for representing relationships between models. Choosing the right one significantly impacts your API design.

## Overview

| Field Type | Representation | Read/Write | Use Case |
|------------|---------------|------------|----------|
| `PrimaryKeyRelatedField` | Integer ID | Both | Standard FK relationships |
| `StringRelatedField` | String (`__str__`) | Read-only | Simple display |
| `SlugRelatedField` | Slug value | Both | Natural keys |
| `HyperlinkedRelatedField` | URL | Both | HATEOAS, discoverable APIs |
| `HyperlinkedIdentityField` | URL (self) | Read-only | Object's own URL |

## Common Parameters

All relational fields (except StringRelatedField) accept:

```python
field = RelatedField(
    queryset=Model.objects.all(),  # For writable fields (required unless read_only)
    read_only=False,                # Make field read-only
    required=True,                  # Require in input
    allow_null=False,               # Allow None values
    many=False,                     # For to-many relationships
)
```

## PrimaryKeyRelatedField

Represents relationships using the related object's primary key (usually an integer ID).

### When to Use

- ✅ Most common choice (80% of APIs)
- ✅ Simple, efficient representation
- ✅ When clients only need the ID to fetch full details
- ✅ When you want minimal response payload

### Basic Usage

```python
from django.db import models

class Author(models.Model):
    name = models.CharField(max_length=100)

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='books')

# Serializer
class BookSerializer(serializers.ModelSerializer):
    # Explicit declaration (optional with ModelSerializer)
    author = serializers.PrimaryKeyRelatedField(
        queryset=Author.objects.all()
    )

    class Meta:
        model = Book
        fields = ['id', 'title', 'author']

# Output:
# {
#     "id": 1,
#     "title": "Django for Beginners",
#     "author": 5  # Just the ID
# }

# Input (creating a book):
# POST {"title": "New Book", "author": 5}
```

### Read-Only PrimaryKeyRelatedField

```python
class BookSerializer(serializers.ModelSerializer):
    # Read-only - just show the ID, can't write it
    author_id = serializers.PrimaryKeyRelatedField(
        source='author',
        read_only=True
    )

    # No queryset needed for read-only fields
```

### Many-to-Many Relationships

```python
class Book(models.Model):
    title = models.CharField(max_length=200)
    categories = models.ManyToManyField('Category', related_name='books')

class BookSerializer(serializers.ModelSerializer):
    # many=True for to-many relationships
    categories = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Category.objects.all()
    )

    class Meta:
        model = Book
        fields = ['id', 'title', 'categories']

# Output:
# {
#     "id": 1,
#     "title": "Django Book",
#     "categories": [1, 3, 5]  # List of IDs
# }

# Input:
# POST {"title": "New Book", "categories": [1, 3, 5]}
```

### Custom Primary Key Field

```python
class Author(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=100)

class BookSerializer(serializers.ModelSerializer):
    # Handles UUID primary keys automatically
    author = serializers.PrimaryKeyRelatedField(
        queryset=Author.objects.all()
    )
    # Output: "author": "123e4567-e89b-12d3-a456-426614174000"

    # Or customize with pk_field:
    author = serializers.PrimaryKeyRelatedField(
        queryset=Author.objects.all(),
        pk_field=serializers.UUIDField(format='hex_verbose')
    )
```

### Performance Optimization

```python
# Problem: N+1 query issue
books = Book.objects.all()
serializer = BookSerializer(books, many=True)
# Each book.author_id access could hit the database!

# Solution: Use select_related
books = Book.objects.select_related('author').all()
serializer = BookSerializer(books, many=True)
# Single query with JOIN

# For reverse FK or M2M:
authors = Author.objects.prefetch_related('books').all()
```

## StringRelatedField

Represents relationships using the related object's `__str__()` method. **Always read-only.**

### When to Use

- ✅ Simple, human-readable representation
- ✅ When you just need to display the relationship
- ✅ Quick prototyping
- ❌ Can't write (always read-only)
- ❌ Can't query or filter by

### Basic Usage

```python
class Author(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class BookSerializer(serializers.ModelSerializer):
    # Shows author's __str__() value
    author = serializers.StringRelatedField()

    class Meta:
        model = Book
        fields = ['id', 'title', 'author']

# Output:
# {
#     "id": 1,
#     "title": "Django Book",
#     "author": "Jane Smith"  # Result of author.__str__()
# }

# Note: Can't use this field for input!
```

### Many-to-Many

```python
class BookSerializer(serializers.ModelSerializer):
    categories = serializers.StringRelatedField(many=True)

# Output:
# {
#     "id": 1,
#     "title": "Django Book",
#     "categories": ["Technology", "Programming", "Web Development"]
# }
```

### Read-Only Warning

```python
# This WON'T work - StringRelatedField is always read-only
serializer = BookSerializer(data={
    'title': 'New Book',
    'author': 'Jane Smith'  # ERROR: StringRelatedField doesn't handle input!
})
```

## SlugRelatedField

Represents relationships using a specific field (slug) on the related object.

### When to Use

- ✅ Natural keys (username, email, slug, code)
- ✅ Human-readable IDs
- ✅ When you want to reference by something other than PK
- ✅ Both readable and writable

### Basic Usage

```python
class Author(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

class BookSerializer(serializers.ModelSerializer):
    # Reference author by slug instead of ID
    author = serializers.SlugRelatedField(
        slug_field='slug',  # Field to use on Author model (required)
        queryset=Author.objects.all()
    )

    class Meta:
        model = Book
        fields = ['id', 'title', 'author']

# Output:
# {
#     "id": 1,
#     "title": "Django Book",
#     "author": "jane-smith"  # The slug value
# }

# Input:
# POST {"title": "New Book", "author": "jane-smith"}
# Looks up Author by slug="jane-smith"
```

### Common Slug Fields

```python
# By username
author = serializers.SlugRelatedField(
    slug_field='username',
    queryset=User.objects.all()
)

# By email
user = serializers.SlugRelatedField(
    slug_field='email',
    queryset=User.objects.all()
)

# By code
product = serializers.SlugRelatedField(
    slug_field='sku',
    queryset=Product.objects.all()
)

# By UUID (as string)
resource = serializers.SlugRelatedField(
    slug_field='uuid',
    queryset=Resource.objects.all()
)
```

### Nested Slug Fields

```python
# Access nested fields with double underscore
class BookSerializer(serializers.ModelSerializer):
    # Use author's user's username
    author_username = serializers.SlugRelatedField(
        source='author',
        slug_field='user__username',  # Nested field
        queryset=Author.objects.all()
    )
```

### Read-Only Slug

```python
# Read-only slug field (no queryset needed)
author_slug = serializers.SlugRelatedField(
    source='author',
    slug_field='slug',
    read_only=True
)
```

### Many-to-Many

```python
# Multiple slugs
categories = serializers.SlugRelatedField(
    many=True,
    slug_field='slug',
    queryset=Category.objects.all()
)

# Output: "categories": ["technology", "programming", "web"]
# Input: POST {"categories": ["technology", "programming"]}
```

## HyperlinkedRelatedField

Represents relationships using URLs to the related object's detail endpoint.

### When to Use

- ✅ HATEOAS (Hypermedia As The Engine Of Application State)
- ✅ Public APIs where discoverability matters
- ✅ When clients should navigate via URLs
- ✅ Self-documenting APIs
- ❌ Requires URL routing configuration
- ❌ Requires `request` in context
- ❌ Slightly more complex setup

### Basic Usage

```python
class BookSerializer(serializers.ModelSerializer):
    # Hyperlinked author field
    author = serializers.HyperlinkedRelatedField(
        view_name='author-detail',  # URL pattern name (required)
        queryset=Author.objects.all()
    )

    class Meta:
        model = Book
        fields = ['id', 'title', 'author']

# Output:
# {
#     "id": 1,
#     "title": "Django Book",
#     "author": "http://example.com/api/authors/5/"  # Full URL
# }

# Input:
# POST {"title": "New Book", "author": "http://example.com/api/authors/5/"}
# Resolves URL to find author with ID 5
```

### URL Configuration Required

```python
# urls.py
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'authors', AuthorViewSet, basename='author')
router.register(r'books', BookViewSet, basename='book')

# This creates URL patterns:
# /api/authors/        -> author-list
# /api/authors/<pk>/   -> author-detail (used in view_name)
# /api/books/          -> book-list
# /api/books/<pk>/     -> book-detail
```

### Context Required

```python
# Must pass request in context
book = Book.objects.get(pk=1)

# Correct - with context
serializer = BookSerializer(book, context={'request': request})

# Wrong - will crash when accessing .data
serializer = BookSerializer(book)  # Missing request context!
```

### Lookup Field Customization

```python
class BookSerializer(serializers.ModelSerializer):
    author = serializers.HyperlinkedRelatedField(
        view_name='author-detail',
        queryset=Author.objects.all(),
        lookup_field='slug',        # Look up by slug instead of pk
        lookup_url_kwarg='slug',    # URL kwarg name (default: same as lookup_field)
    )

# URLs must match:
# path('authors/<slug:slug>/', AuthorDetailView.as_view(), name='author-detail')

# Output: "author": "http://example.com/api/authors/jane-smith/"
```

### Format Parameter

```python
author = serializers.HyperlinkedRelatedField(
    view_name='author-detail',
    queryset=Author.objects.all(),
    format='json',  # Append .json to URLs
)

# Output: "author": "http://example.com/api/authors/5/.json"
```

### Many-to-Many

```python
categories = serializers.HyperlinkedRelatedField(
    many=True,
    view_name='category-detail',
    queryset=Category.objects.all()
)

# Output:
# "categories": [
#     "http://example.com/api/categories/1/",
#     "http://example.com/api/categories/3/",
#     "http://example.com/api/categories/5/"
# ]
```

### Read-Only Hyperlink

```python
author_url = serializers.HyperlinkedRelatedField(
    source='author',
    view_name='author-detail',
    read_only=True  # No queryset needed
)
```

## HyperlinkedIdentityField

A read-only field that represents the object's own URL (not a relationship to another object).

### When to Use

- ✅ Object's self-reference URL
- ✅ Used by HyperlinkedModelSerializer for the 'url' field
- ✅ Always read-only (it's the object itself!)

### Basic Usage

```python
class BookSerializer(serializers.ModelSerializer):
    # Object's own URL
    url = serializers.HyperlinkedIdentityField(
        view_name='book-detail'  # URL pattern for THIS model
    )

    class Meta:
        model = Book
        fields = ['url', 'id', 'title']

# Output:
# {
#     "url": "http://example.com/api/books/1/",  # This book's URL
#     "id": 1,
#     "title": "Django Book"
# }
```

### Custom Field Name

```python
# Use 'self' instead of 'url'
class BookSerializer(serializers.ModelSerializer):
    self = serializers.HyperlinkedIdentityField(
        view_name='book-detail'
    )

    class Meta:
        model = Book
        fields = ['self', 'id', 'title']
```

### Lookup Field

```python
# Use slug instead of pk for lookup
url = serializers.HyperlinkedIdentityField(
    view_name='book-detail',
    lookup_field='slug'
)

# URLs must match:
# path('books/<slug:slug>/', BookDetailView.as_view(), name='book-detail')

# Output: "url": "http://example.com/api/books/django-beginners/"
```

### Alternative URLs

```python
class BookSerializer(serializers.ModelSerializer):
    # Object's main URL
    url = serializers.HyperlinkedIdentityField(view_name='book-detail')

    # Additional action URLs
    reviews_url = serializers.HyperlinkedIdentityField(
        view_name='book-reviews'
    )
    purchase_url = serializers.HyperlinkedIdentityField(
        view_name='book-purchase'
    )

# Output:
# {
#     "url": "http://example.com/api/books/1/",
#     "reviews_url": "http://example.com/api/books/1/reviews/",
#     "purchase_url": "http://example.com/api/books/1/purchase/"
# }
```

## Comparison Matrix

### Feature Comparison

| Feature | PrimaryKey | String | Slug | Hyperlinked | Identity |
|---------|-----------|--------|------|-------------|----------|
| Writable | ✅ | ❌ | ✅ | ✅ | ❌ |
| Readable | ✅ | ✅ | ✅ | ✅ | ✅ |
| Needs queryset | ✅ | ❌ | ✅ | ✅ | ❌ |
| Needs URL routing | ❌ | ❌ | ❌ | ✅ | ✅ |
| Needs request context | ❌ | ❌ | ❌ | ✅ | ✅ |
| Human-readable | ❌ | ✅ | ✅ | ❌ | ❌ |
| Efficient | ✅ | ✅ | ✅ | ❌ | ❌ |

### Use Case Matrix

| Scenario | Recommended Field |
|----------|------------------|
| Standard FK relationship | PrimaryKeyRelatedField |
| Display-only relationship | StringRelatedField |
| Username/email/slug lookup | SlugRelatedField |
| HATEOAS/discoverable API | HyperlinkedRelatedField |
| Object's self-URL | HyperlinkedIdentityField |
| M2M with IDs | PrimaryKeyRelatedField(many=True) |
| M2M with natural keys | SlugRelatedField(many=True) |
| M2M with URLs | HyperlinkedRelatedField(many=True) |

## Advanced Patterns

### Mixing Representations

```python
class BookSerializer(serializers.ModelSerializer):
    # Write with ID, read with full details
    author_id = serializers.PrimaryKeyRelatedField(
        source='author',
        queryset=Author.objects.all(),
        write_only=True
    )
    author = AuthorSerializer(read_only=True)

    class Meta:
        model = Book
        fields = ['id', 'title', 'author_id', 'author']

# Input: POST {"title": "New Book", "author_id": 5}
# Output: {
#     "id": 1,
#     "title": "New Book",
#     "author": {"id": 5, "name": "Jane Smith", "email": "..."}
# }
```

### Custom Queryset Filtering

```python
class BookSerializer(serializers.ModelSerializer):
    # Only allow active authors
    author = serializers.PrimaryKeyRelatedField(
        queryset=Author.objects.filter(is_active=True)
    )

    # Dynamic queryset based on request
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Filter to user's organization
            self.fields['author'].queryset = Author.objects.filter(
                organization=request.user.organization
            )
```

### Nested Relationships

```python
# One level: Use nested serializer
class BookSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)

# Two levels: Use depth
class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = '__all__'
        depth = 2  # Auto-nest 2 levels (use sparingly!)
```

### Reverse Relationships

```python
class AuthorSerializer(serializers.ModelSerializer):
    # Reverse FK (author.books)
    books = serializers.PrimaryKeyRelatedField(
        many=True,
        read_only=True  # Usually read-only for reverse relationships
    )

    # With nested representation
    books = BookSerializer(many=True, read_only=True)

    # With hyperlinks
    books = serializers.HyperlinkedRelatedField(
        many=True,
        read_only=True,
        view_name='book-detail'
    )
```

### Allow Null Relationships

```python
# Optional relationship
author = serializers.PrimaryKeyRelatedField(
    queryset=Author.objects.all(),
    allow_null=True,  # Allow null value
    required=False    # Allow omitting from input
)

# Input: {"title": "Book", "author": null}  # Valid
# Input: {"title": "Book"}                  # Valid (omitted)
```

## Performance Considerations

### N+1 Query Problem

```python
# BAD: N+1 queries
books = Book.objects.all()
serializer = BookSerializer(books, many=True)
# 1 query for books + N queries for each book.author

# GOOD: With select_related
books = Book.objects.select_related('author').all()
serializer = BookSerializer(books, many=True)
# 1 query with JOIN

# For reverse FK or M2M: use prefetch_related
authors = Author.objects.prefetch_related('books').all()
```

### Use PK When Possible

```python
# Most efficient
author = serializers.PrimaryKeyRelatedField(queryset=Author.objects.all())

# Less efficient (requires URL resolution)
author = serializers.HyperlinkedRelatedField(
    view_name='author-detail',
    queryset=Author.objects.all()
)
```

### Read-Only Optimization

```python
# If you don't need to write, make it read-only
# This skips queryset evaluation and validation
author = serializers.PrimaryKeyRelatedField(read_only=True)
```

## Common Errors

### "RelationalField must provide a queryset"

```python
# Wrong
author = serializers.PrimaryKeyRelatedField()

# Correct
author = serializers.PrimaryKeyRelatedField(
    queryset=Author.objects.all()
)
# OR
author = serializers.PrimaryKeyRelatedField(read_only=True)
```

### "Invalid pk - object does not exist"

The provided ID doesn't exist in the queryset:
- Check the ID is correct
- Check queryset includes the object
- Check for soft-deletes or filters

### HyperlinkedRelatedField requires request context

```python
# Wrong
serializer = BookSerializer(book)

# Correct
serializer = BookSerializer(book, context={'request': request})
```

### "No URL match" for HyperlinkedRelatedField

The view_name doesn't match any URL pattern:
- Check URL patterns are configured
- Check basename in router.register()
- Check view_name spelling
