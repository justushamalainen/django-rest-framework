---
version: 1.0
last_updated: 2026-01-06
difficulty: intermediate
keywords: serializers, validation, nested-data, model-serializer, fields, relations
dependencies: djangorestframework>=3.14
source_files:
  - rest_framework/serializers.py
  - rest_framework/fields.py
  - rest_framework/relations.py
  - rest_framework/validators.py
---

# DRF Serializers

Serializers convert between Django models and JSON/XML. They handle validation, relationships, and nested data. This is the most critical skill in DRF.

## What You'll Learn

- Choose the right serializer type (Serializer, ModelSerializer, HyperlinkedModelSerializer)
- Use common field types and relational fields effectively
- Implement field-level and object-level validation
- Create writable nested serializers (the #1 pain point)
- Optimize queries to avoid N+1 problems
- Handle partial updates and read/write field separation

## Quick Start

ModelSerializer is your go-to for 95% of use cases:

```python
# models.py
from django.db import models

class Author(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='books')
    isbn = models.CharField(max_length=13, unique=True)
    pages = models.IntegerField()
    price = models.DecimalField(max_digits=6, decimal_places=2)

# serializers.py
from rest_framework import serializers

class BookSerializer(serializers.ModelSerializer):
    # Read-only computed field
    author_name = serializers.CharField(source='author.name', read_only=True)

    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'author_name', 'isbn', 'pages', 'price']
        read_only_fields = ['id']
        extra_kwargs = {
            'isbn': {'required': True},
            'pages': {'min_value': 1},
        }

    def validate_pages(self, value):
        """Field-level validation"""
        if value > 10000:
            raise serializers.ValidationError("Too many pages")
        return value

    def validate(self, attrs):
        """Object-level validation"""
        if attrs.get('price', 0) > 1000 and attrs.get('pages', 0) < 100:
            raise serializers.ValidationError(
                "Books under 100 pages cannot cost more than $1000"
            )
        return attrs

# views.py - Usage
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['POST'])
def create_book(request):
    serializer = BookSerializer(data=request.data)
    if serializer.is_valid():
        book = serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)

@api_view(['PUT', 'PATCH'])
def update_book(request, pk):
    book = Book.objects.get(pk=pk)
    partial = request.method == 'PATCH'
    serializer = BookSerializer(book, data=request.data, partial=partial)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)

@api_view(['GET'])
def list_books(request):
    # Optimize with select_related to avoid N+1 queries
    books = Book.objects.select_related('author').all()
    serializer = BookSerializer(books, many=True)
    return Response(serializer.data)
```

## Serializer Types

### ModelSerializer (95% of use cases)

Auto-generates fields and validators from Django models:

```python
class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = '__all__'  # Or list specific fields
        # fields = ['id', 'title', 'author']
        # exclude = ['internal_notes']
```

**When to use:** Model-backed APIs, standard CRUD operations

### Basic Serializer

Full control over fields and validation:

```python
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=100)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        from django.contrib.auth import authenticate
        user = authenticate(**attrs)
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        return attrs
```

**When to use:** Non-model data (forms, computed data, external APIs)

### HyperlinkedModelSerializer

Uses URLs instead of IDs for relationships:

```python
class BookSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Book
        fields = ['url', 'title', 'author']
        # 'author' will be a URL like "http://api.com/authors/5/"

# Requires request context
serializer = BookSerializer(book, context={'request': request})
```

**When to use:** HATEOAS APIs, public APIs where discoverability matters

## Common Patterns

### Read/Write Field Separation

Write with ID, read with full details:

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
# Output: {"id": 1, "title": "New Book", "author": {"id": 5, "name": "Jane"}}
```

### Writable Nested Relationships

See [reference/nested-writes.md](./reference/nested-writes.md) - this is THE most common pain point:

```python
class BookSerializer(serializers.ModelSerializer):
    author = AuthorSerializer()

    class Meta:
        model = Book
        fields = ['id', 'title', 'author']

    def create(self, validated_data):
        author_data = validated_data.pop('author')
        author = Author.objects.create(**author_data)
        book = Book.objects.create(author=author, **validated_data)
        return book
```

### Computed Fields

```python
class AuthorSerializer(serializers.ModelSerializer):
    book_count = serializers.SerializerMethodField()

    class Meta:
        model = Author
        fields = ['id', 'name', 'book_count']

    def get_book_count(self, obj):
        return obj.books.count()
```

## Common Mistakes

### ❌ Mistake 1: Not calling is_valid() before save()

```python
# Wrong
serializer = BookSerializer(data=request.data)
serializer.save()  # CRASH!

# Correct
serializer = BookSerializer(data=request.data)
if serializer.is_valid():
    serializer.save()
```

### ❌ Mistake 2: N+1 Query Problem

```python
# Wrong - Each book.author hits the database
books = Book.objects.all()
serializer = BookSerializer(books, many=True)

# Correct - Single query with JOIN
books = Book.objects.select_related('author').all()
serializer = BookSerializer(books, many=True)

# For reverse FK or M2M, use prefetch_related
authors = Author.objects.prefetch_related('books').all()
```

### ❌ Mistake 3: Not handling partial updates

```python
# Wrong - PATCH will fail if required fields missing
serializer = BookSerializer(book, data=request.data)

# Correct
serializer = BookSerializer(book, data=request.data, partial=True)
```

### ❌ Mistake 4: Forgetting to return from validate methods

```python
# Wrong
def validate_pages(self, value):
    if value <= 0:
        raise serializers.ValidationError("Invalid")
    # Missing return!

# Correct
def validate_pages(self, value):
    if value <= 0:
        raise serializers.ValidationError("Invalid")
    return value  # MUST return
```

## Reference Documentation

For comprehensive details, see:

- **[Field Types](./reference/field-types.md)** - Common field types and parameters
- **[Relations](./reference/relations.md)** - PrimaryKeyRelatedField, SlugRelatedField patterns
- **[Validation](./reference/validation.md)** - Field-level and object-level validation
- **[Nested Writes](./reference/nested-writes.md)** - CRITICAL: Handling writable nested serializers

## Quick Reference

```python
# Basic usage
serializer = BookSerializer(data=data)           # Deserialize
serializer = BookSerializer(book)                # Serialize
serializer = BookSerializer(books, many=True)    # Multiple objects

# Validation and saving
if serializer.is_valid():
    obj = serializer.save()      # Create or update
    obj = serializer.save(owner=request.user)  # Pass extra fields

# Accessing data
serializer.data          # Python dict (after is_valid() for input)
serializer.errors        # Validation errors (after is_valid())
serializer.validated_data  # Cleaned data (after is_valid())

# Partial updates
serializer = BookSerializer(book, data=data, partial=True)

# Context
serializer = BookSerializer(book, context={'request': request})

# Common Meta options
class Meta:
    model = Book
    fields = ['id', 'title', 'author']  # Explicit
    fields = '__all__'                   # All fields
    exclude = ['internal_notes']         # All except these
    read_only_fields = ['created_at']
    extra_kwargs = {
        'title': {'required': True, 'max_length': 100}
    }
```

## Performance Tips

1. **Always use select_related() and prefetch_related()** for relationships
2. **Use read_only=True** for computed fields to skip validation
3. **Avoid SerializerMethodField** in list views (can't optimize)
4. **Use source** instead of SerializerMethodField when possible
5. **Use only/defer** on querysets to limit fields

## Next Steps

After mastering serializers:
- **views** skill - Learn APIView, generic views, and ViewSets
- **testing** skill - Test serializers effectively
