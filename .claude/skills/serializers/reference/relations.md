# Relational Fields Reference

DRF provides 5 relational field types. Focus on PrimaryKeyRelatedField (most common) and SlugRelatedField (for natural keys).

## Overview

| Field Type | Representation | Use Case |
|------------|---------------|----------|
| `PrimaryKeyRelatedField` | Integer ID | Standard FK relationships (95% of cases) |
| `SlugRelatedField` | Slug/natural key | Username, email, SKU lookups |
| `StringRelatedField` | String (`__str__`) | Read-only display |
| `HyperlinkedRelatedField` | URL | HATEOAS APIs |
| `HyperlinkedIdentityField` | Self URL | Object's own URL |

## PrimaryKeyRelatedField

Represents relationships using the related object's primary key. **This is your default choice.**

### Basic Usage

```python
from django.db import models
from rest_framework import serializers

class Author(models.Model):
    name = models.CharField(max_length=100)

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)

# Serializer
class BookSerializer(serializers.ModelSerializer):
    author = serializers.PrimaryKeyRelatedField(
        queryset=Author.objects.all()
    )

    class Meta:
        model = Book
        fields = ['id', 'title', 'author']

# Input:  {"title": "Django Book", "author": 5}
# Output: {"id": 1, "title": "Django Book", "author": 5}
```

### Read-Only

```python
# Read-only - just show the ID
author = serializers.PrimaryKeyRelatedField(read_only=True)
# No queryset needed for read-only fields
```

### Many-to-Many

```python
class Book(models.Model):
    categories = models.ManyToManyField('Category')

class BookSerializer(serializers.ModelSerializer):
    categories = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Category.objects.all()
    )

# Input:  {"title": "Book", "categories": [1, 3, 5]}
# Output: {"id": 1, "title": "Book", "categories": [1, 3, 5]}
```

### Allow Null

```python
# Optional relationship
author = serializers.PrimaryKeyRelatedField(
    queryset=Author.objects.all(),
    allow_null=True,
    required=False
)

# Input: {"title": "Book", "author": null}  # Valid
```

### Performance

```python
# BAD: N+1 queries
books = Book.objects.all()
serializer = BookSerializer(books, many=True)

# GOOD: Single query with JOIN
books = Book.objects.select_related('author').all()
serializer = BookSerializer(books, many=True)

# For reverse FK or M2M: use prefetch_related
authors = Author.objects.prefetch_related('books').all()
```

## SlugRelatedField

Represents relationships using a specific field (natural key).

### Basic Usage

```python
class Author(models.Model):
    name = models.CharField(max_length=100)
    username = models.SlugField(unique=True)

class BookSerializer(serializers.ModelSerializer):
    # Reference author by username instead of ID
    author = serializers.SlugRelatedField(
        slug_field='username',  # Field to use (required)
        queryset=Author.objects.all()
    )

    class Meta:
        model = Book
        fields = ['id', 'title', 'author']

# Input:  {"title": "Book", "author": "jane-smith"}
# Output: {"id": 1, "title": "Book", "author": "jane-smith"}
```

### Common Use Cases

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

# By SKU
product = serializers.SlugRelatedField(
    slug_field='sku',
    queryset=Product.objects.all()
)
```

### Many-to-Many

```python
categories = serializers.SlugRelatedField(
    many=True,
    slug_field='slug',
    queryset=Category.objects.all()
)

# Input:  {"categories": ["tech", "programming", "web"]}
# Output: {"categories": ["tech", "programming", "web"]}
```

## StringRelatedField

Always read-only. Uses `__str__()` method.

```python
class Author(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class BookSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField()

# Output: {"id": 1, "title": "Book", "author": "Jane Smith"}
# Can't be used for input!
```

## Common Patterns

### Read with Details, Write with ID

Most common pattern - simple writes, detailed reads:

```python
class BookSerializer(serializers.ModelSerializer):
    # Write-only: accept author ID
    author_id = serializers.PrimaryKeyRelatedField(
        source='author',
        queryset=Author.objects.all(),
        write_only=True
    )

    # Read-only: return full author details
    author = AuthorSerializer(read_only=True)

    class Meta:
        model = Book
        fields = ['id', 'title', 'author_id', 'author']

# Input:  {"title": "New Book", "author_id": 5}
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

    # Dynamic queryset based on user
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Filter to user's organization
            self.fields['author'].queryset = Author.objects.filter(
                organization=request.user.organization
            )
```

### Reverse Relationships

```python
class AuthorSerializer(serializers.ModelSerializer):
    # Reverse FK (author.books)
    books = serializers.PrimaryKeyRelatedField(
        many=True,
        read_only=True  # Usually read-only for reverse
    )

    # Or with nested representation
    books = BookSerializer(many=True, read_only=True)

# Optimize with prefetch_related
authors = Author.objects.prefetch_related('books').all()
```

## Common Errors

### "RelationalField must provide a queryset"

```python
# Wrong
author = serializers.PrimaryKeyRelatedField()

# Correct - provide queryset OR make it read-only
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
- Check for filters or soft-deletes

### N+1 Query Problem

```python
# Wrong - N+1 queries
books = Book.objects.all()

# Correct - use select_related for FK
books = Book.objects.select_related('author').all()

# Correct - use prefetch_related for M2M or reverse FK
authors = Author.objects.prefetch_related('books').all()
```

## Decision Guide

**Use PrimaryKeyRelatedField when:**
- Standard database relationships (95% of cases)
- You want efficient queries
- Client knows IDs or can look them up

**Use SlugRelatedField when:**
- Natural keys (username, email, SKU)
- Human-readable identifiers
- Client doesn't have IDs but has natural keys

**Use StringRelatedField when:**
- Read-only display
- Simple representation
- Quick prototyping

**Use read/write separation when:**
- You want simple writes (just ID) but rich reads (full object)
- Most common production pattern
