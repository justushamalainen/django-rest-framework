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

Serializers are the heart of Django REST Framework. They handle conversion between complex types (like Django models) and Python primitives that can be rendered into JSON/XML, and vice versa. This is the most complex and important skill in DRF.

## What You'll Learn

After mastering this skill, you will be able to:

- Choose the right serializer type (Serializer, ModelSerializer, HyperlinkedModelSerializer) for your use case
- Use all 40+ built-in field types with correct parameters and validation
- Handle all 5 types of relational fields (PrimaryKey, Slug, Hyperlinked, String, Identity)
- Implement field-level and object-level validation with custom validators
- Create writable nested serializers with proper create() and update() methods
- Use source='*', dotted notation, and SerializerMethodField effectively
- Avoid N+1 query problems with select_related() and prefetch_related()
- Customize field mapping with Meta options and extra_kwargs
- Handle read-only, write-only, and required field configurations
- Debug common serializer errors and validation issues

## Before You Start

**Prerequisites:**
- Django models and ORM basics
- Python classes and inheritance
- Understanding of REST API concepts

**Key Concepts:**
- Serialization: Model instance → Python dict → JSON
- Deserialization: JSON → Python dict → Model instance
- Validation happens in `is_valid()`, before `save()`
- `save()` calls either `create()` or `update()` based on `instance`

## Quick Start

Here's a complete working example showing the full lifecycle:

```python
# models.py
from django.db import models

class Author(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    bio = models.TextField(blank=True)
    birth_date = models.DateField(null=True)

    def __str__(self):
        return self.name

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='books')
    isbn = models.CharField(max_length=13, unique=True)
    published_date = models.DateField()
    pages = models.IntegerField()
    price = models.DecimalField(max_digits=6, decimal_places=2)
    is_available = models.BooleanField(default=True)

    class Meta:
        unique_together = [['title', 'author']]

# serializers.py
from rest_framework import serializers
from .models import Author, Book

class AuthorSerializer(serializers.ModelSerializer):
    # Computed field using SerializerMethodField
    book_count = serializers.SerializerMethodField()

    # Read-only field showing age calculation
    age = serializers.SerializerMethodField()

    class Meta:
        model = Author
        fields = ['id', 'name', 'email', 'bio', 'birth_date', 'book_count', 'age']
        # Make email read-only after creation
        extra_kwargs = {
            'email': {'required': True},
            'bio': {'allow_blank': True},
        }

    def get_book_count(self, obj):
        """Custom method for SerializerMethodField"""
        return obj.books.count()

    def get_age(self, obj):
        """Calculate age from birth_date"""
        if not obj.birth_date:
            return None
        from datetime import date
        today = date.today()
        return today.year - obj.birth_date.year

class BookSerializer(serializers.ModelSerializer):
    # Nested read-only representation
    author_detail = AuthorSerializer(source='author', read_only=True)

    # Writable foreign key (just the ID)
    author = serializers.PrimaryKeyRelatedField(queryset=Author.objects.all())

    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'author_detail', 'isbn',
                  'published_date', 'pages', 'price', 'is_available']
        read_only_fields = ['id']

    def validate_pages(self, value):
        """Field-level validation"""
        if value <= 0:
            raise serializers.ValidationError("Pages must be positive")
        if value > 10000:
            raise serializers.ValidationError("Pages seems too high")
        return value

    def validate(self, attrs):
        """Object-level validation"""
        if attrs.get('price', 0) > 1000 and attrs.get('pages', 0) < 100:
            raise serializers.ValidationError(
                "Books under 100 pages cannot cost more than $1000"
            )
        return attrs

# views.py - Usage example
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

@api_view(['POST'])
def create_book(request):
    """Create a new book"""
    serializer = BookSerializer(data=request.data)
    if serializer.is_valid():
        book = serializer.save()  # Calls create() internally
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
def update_book(request, pk):
    """Update an existing book"""
    try:
        book = Book.objects.get(pk=pk)
    except Book.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    serializer = BookSerializer(book, data=request.data)
    if serializer.is_valid():
        serializer.save()  # Calls update() internally
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def list_books(request):
    """List all books with author details"""
    # Optimize query to avoid N+1 problem
    books = Book.objects.select_related('author').all()
    serializer = BookSerializer(books, many=True)
    return Response(serializer.data)
```

## Decision Tree: Choosing Serializer Types

Use this decision tree to pick the right serializer for your use case:

```
START: Do you have a Django model?
│
├─ NO → Question 2A
│   └─ Question 2A: Do you need automatic validation?
│       ├─ NO → Use: Basic Serializer (manual field definition)
│       └─ YES → Use: Basic Serializer with validators
│
└─ YES → Question 2B
    └─ Question 2B: Do you want automatic field generation from model?
        ├─ NO → Use: Basic Serializer (full control over fields)
        │
        └─ YES → Question 3
            └─ Question 3: Do you need hyperlinked relationships?
                ├─ NO → Question 4A
                │   └─ Question 4A: Do you need to customize many fields?
                │       ├─ NO → Use: ModelSerializer (standard choice)
                │       └─ YES → Question 5A
                │           └─ Question 5A: Are you customizing >50% of fields?
                │               ├─ NO → Use: ModelSerializer with extra_kwargs
                │               └─ YES → Use: Basic Serializer (more explicit)
                │
                └─ YES → Question 4B
                    └─ Question 4B: Do you need both 'id' and 'url' fields?
                        ├─ NO → Use: HyperlinkedModelSerializer
                        └─ YES → Use: ModelSerializer with HyperlinkedRelatedField

SPECIAL CASES:
- Writing to nested relationships? → See reference/nested-writes.md
- List operations (many=True)? → Returns ListSerializer automatically
- Custom representation logic? → Override to_representation()
- Custom deserialization logic? → Override to_internal_value()
```

**When to use each:**

**Basic Serializer:**
- Non-model data (API inputs, forms, computed data)
- Complete control over all fields
- Custom validation logic that doesn't map to models
- Example: Login form, search filters, analytics data

**ModelSerializer (most common):**
- Model-backed API endpoints
- Standard CRUD operations
- Automatic field generation and validation
- Default create() and update() implementations
- Example: 80% of DRF APIs use this

**HyperlinkedModelSerializer:**
- API discovery and HATEOAS patterns
- When relationships should be URLs not IDs
- When you want self-documenting APIs
- Example: Public APIs where discoverability matters

## Common Mistakes & How to Fix Them

### ❌ Mistake 1: Forgetting to call is_valid() before save()

**Wrong:**
```python
serializer = BookSerializer(data=request.data)
serializer.save()  # WILL CRASH!
```

**Why it fails:** `save()` requires validation. Without `is_valid()`, `validated_data` doesn't exist.

**✅ Correct:**
```python
serializer = BookSerializer(data=request.data)
if serializer.is_valid():
    serializer.save()
else:
    print(serializer.errors)
```

**Test:** Try to save without validation - you should get an AssertionError.

---

### ❌ Mistake 2: Not handling writable nested serializers

**Wrong:**
```python
class BookSerializer(serializers.ModelSerializer):
    author = AuthorSerializer()  # Nested serializer

    class Meta:
        model = Book
        fields = ['title', 'author']

# Using it:
data = {'title': 'New Book', 'author': {'name': 'John'}}
serializer = BookSerializer(data=data)
serializer.save()  # WILL CRASH!
```

**Why it fails:** ModelSerializer doesn't support writable nested relationships by default.

**✅ Correct:**
```python
class BookSerializer(serializers.ModelSerializer):
    author = AuthorSerializer()

    class Meta:
        model = Book
        fields = ['title', 'author']

    def create(self, validated_data):
        author_data = validated_data.pop('author')
        author = Author.objects.create(**author_data)
        book = Book.objects.create(author=author, **validated_data)
        return book

    def update(self, instance, validated_data):
        author_data = validated_data.pop('author', None)
        if author_data:
            for attr, value in author_data.items():
                setattr(instance.author, attr, value)
            instance.author.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
```

**Test:** Post nested data - it should create both objects.

---

### ❌ Mistake 3: N+1 Query Problem with relationships

**Wrong:**
```python
books = Book.objects.all()
serializer = BookSerializer(books, many=True)
# Each book.author access triggers a query!
```

**Why it fails:** Without select_related/prefetch_related, each book's author lookup hits the database.

**✅ Correct:**
```python
# For ForeignKey (one-to-one)
books = Book.objects.select_related('author').all()

# For ManyToMany or reverse ForeignKey
authors = Author.objects.prefetch_related('books').all()

serializer = BookSerializer(books, many=True)
```

**Test:** Check Django Debug Toolbar or connection.queries - should be 1-2 queries, not N+1.

---

### ❌ Mistake 4: Using read_only=True with required=True

**Wrong:**
```python
class BookSerializer(serializers.ModelSerializer):
    title = serializers.CharField(read_only=True, required=True)  # CONFLICT!
```

**Why it fails:** read_only fields are never required in input. This is a logical contradiction.

**✅ Correct:**
```python
# Read-only field (never in input)
class BookSerializer(serializers.ModelSerializer):
    title = serializers.CharField(read_only=True)

# OR required writable field
class BookSerializer(serializers.ModelSerializer):
    title = serializers.CharField(required=True)
```

**Test:** DRF will raise an assertion error on serializer instantiation.

---

### ❌ Mistake 5: Not handling partial updates

**Wrong:**
```python
# PATCH endpoint
serializer = BookSerializer(book, data=request.data)
if serializer.is_valid():
    serializer.save()  # Will fail validation on missing fields!
```

**Why it fails:** Without `partial=True`, all required fields must be present.

**✅ Correct:**
```python
serializer = BookSerializer(book, data=request.data, partial=True)
if serializer.is_valid():
    serializer.save()
```

**Test:** PATCH with just one field - it should update only that field.

---

### ❌ Mistake 6: Using source incorrectly with model fields

**Wrong:**
```python
class BookSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source='title')

    class Meta:
        model = Book
        fields = ['title', 'book_title']  # 'title' is auto-generated!
```

**Why it fails:** Both fields map to the same model field, causing conflicts.

**✅ Correct:**
```python
# Option 1: Only use the renamed field
class BookSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source='title')

    class Meta:
        model = Book
        fields = ['book_title']  # Only the renamed one

# Option 2: Use read_only for computed field
class BookSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source='title', read_only=True)

    class Meta:
        model = Book
        fields = ['title', 'book_title']  # 'title' is writable
```

**Test:** Try to create/update - you shouldn't get duplicate field errors.

---

### ❌ Mistake 7: Forgetting to return from validate methods

**Wrong:**
```python
def validate_pages(self, value):
    if value <= 0:
        raise serializers.ValidationError("Invalid")
    # Missing return!

def validate(self, attrs):
    # Some validation...
    # Missing return attrs!
```

**Why it fails:** Validation methods must return the value/attrs. Missing return means None.

**✅ Correct:**
```python
def validate_pages(self, value):
    if value <= 0:
        raise serializers.ValidationError("Invalid")
    return value  # MUST return the value

def validate(self, attrs):
    # Some validation...
    return attrs  # MUST return attrs
```

**Test:** Add a print in create() - you should see the validated value, not None.

---

### ❌ Mistake 8: Using many=True in the wrong place

**Wrong:**
```python
class BookSerializer(serializers.ModelSerializer):
    author = serializers.PrimaryKeyRelatedField(
        queryset=Author.objects.all(),
        many=True  # Wrong! Book has ONE author
    )
```

**Why it fails:** `many=True` is for list fields. Use it on serializer instantiation, not field definition (unless the field really is a list).

**✅ Correct:**
```python
# For the model field (Book has one author)
class BookSerializer(serializers.ModelSerializer):
    author = serializers.PrimaryKeyRelatedField(queryset=Author.objects.all())

# For serializing multiple books
books = Book.objects.all()
serializer = BookSerializer(books, many=True)  # Use many here!
```

**Test:** Create a book - it should accept a single author ID, not a list.

## Implementation Details

For comprehensive reference information, see:

- **[Serializer Types](./reference/serializer-types.md)** - Detailed comparison of Serializer, ModelSerializer, HyperlinkedModelSerializer, and ListSerializer
- **[Field Types](./reference/field-types.md)** - All 40+ built-in field types with parameters, validation, and examples
- **[Relations](./reference/relations.md)** - All 5 relation field types: PrimaryKeyRelatedField, SlugRelatedField, HyperlinkedRelatedField, StringRelatedField, HyperlinkedIdentityField
- **[Validation](./reference/validation.md)** - Field-level validation, object-level validation, validators, and error handling
- **[Nested Writes](./reference/nested-writes.md)** - CRITICAL: Handling writable nested serializers with create() and update() patterns
- **[Common Patterns](./reference/examples/common-patterns.py)** - Working code examples for every pattern

## Troubleshooting

### "You must call .is_valid() before calling .save()"

**Cause:** Calling `save()` before `is_valid()`

**Solution:**
```python
serializer = BookSerializer(data=data)
if serializer.is_valid():  # Always call this first!
    serializer.save()
```

### "The .create() method does not support writable nested fields"

**Cause:** Nested serializer without custom create() method

**Solution:** See [reference/nested-writes.md](./reference/nested-writes.md)

### "Invalid pk '...' - object does not exist"

**Cause:** PrimaryKeyRelatedField pointing to non-existent object

**Solution:**
- Check the ID exists in the database
- Verify the queryset includes the object
- Check for soft-deletes or filtering

### "Field name 'X' is not valid for model 'Y'"

**Cause:** Field in Meta.fields doesn't match model or declared fields

**Solution:**
- Check spelling of field names
- Ensure declared fields are in Meta.fields
- Use `fields = '__all__'` to auto-include all model fields

### Serializer returns None or empty dict

**Cause:** Not passing instance to serializer or accessing .data before is_valid()

**Solution:**
```python
# For representation
serializer = BookSerializer(book)  # Pass instance
data = serializer.data  # No need for is_valid()

# For input
serializer = BookSerializer(data=request.data)
if serializer.is_valid():
    data = serializer.data  # Now it's safe
```

## Performance Tips

1. **Always use select_related() and prefetch_related()** for relationships
2. **Use read_only=True** for computed fields to skip validation
3. **Use SerializerMethodField** sparingly - it's not optimizable
4. **Avoid nested serializers** in list views (use flat representations)
5. **Use only/defer** on querysets to limit fields fetched from database
6. **Cache expensive computations** in SerializerMethodField
7. **Use source='*'** to avoid intermediate object access

## Quick Reference Card

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
serializer.instance      # Object being serialized/updated

# Partial updates
serializer = BookSerializer(book, data=data, partial=True)

# Context
serializer = BookSerializer(book, context={'request': request})

# Common Meta options
class Meta:
    model = Book
    fields = ['id', 'title', 'author']  # Explicit fields
    fields = '__all__'                   # All model fields
    exclude = ['internal_notes']         # All except these
    read_only_fields = ['created_at']    # Auto read-only
    extra_kwargs = {                     # Field options
        'title': {'required': True, 'max_length': 100}
    }
```

## Next Steps

After mastering serializers, continue to:
- **views** skill - Learn APIView, generic views, and ViewSets
- **validation** skill - Advanced validation patterns
- **testing** skill - Test serializers effectively
