# Writable Nested Serializers

**CRITICAL:** This is the #1 pain point in DRF. By default, ModelSerializer **does not support** writable nested relationships. You must implement custom `create()` and `update()` methods.

## The Problem

This doesn't work by default:

```python
class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ['id', 'name', 'email']

class BookSerializer(serializers.ModelSerializer):
    author = AuthorSerializer()  # Nested serializer

    class Meta:
        model = Book
        fields = ['id', 'title', 'author']

# Attempting to use it:
data = {'title': 'Book', 'author': {'name': 'Jane', 'email': 'jane@example.com'}}
serializer = BookSerializer(data=data)
serializer.is_valid()  # ✅ Works
serializer.save()      # ❌ CRASH! "create() does not support writable nested fields"
```

**Why?** DRF doesn't know your business logic - should it create, lookup, or update the nested object?

## Pattern 1: Create Nested Object (ForeignKey)

```python
class BookSerializer(serializers.ModelSerializer):
    author = AuthorSerializer()

    class Meta:
        model = Book
        fields = ['id', 'title', 'author']

    def create(self, validated_data):
        # Extract nested data
        author_data = validated_data.pop('author')

        # Create nested object first
        author = Author.objects.create(**author_data)

        # Create main object with nested object
        book = Book.objects.create(author=author, **validated_data)
        return book

    def update(self, instance, validated_data):
        # Extract nested data (may not be present)
        author_data = validated_data.pop('author', None)

        # Update nested object if provided
        if author_data is not None:
            for attr, value in author_data.items():
                setattr(instance.author, attr, value)
            instance.author.save()

        # Update main object
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance
```

## Pattern 2: Get or Create Nested Object

More realistic - reuse existing objects:

```python
class BookSerializer(serializers.ModelSerializer):
    author = AuthorSerializer()

    class Meta:
        model = Book
        fields = ['id', 'title', 'author']

    def create(self, validated_data):
        author_data = validated_data.pop('author')

        # Get or create author by email
        author, created = Author.objects.get_or_create(
            email=author_data['email'],
            defaults={'name': author_data['name']}
        )

        book = Book.objects.create(author=author, **validated_data)
        return book

    def update(self, instance, validated_data):
        author_data = validated_data.pop('author', None)

        if author_data is not None:
            # Get or create author
            author, created = Author.objects.get_or_create(
                email=author_data['email'],
                defaults={'name': author_data['name']}
            )
            instance.author = author

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance
```

## Pattern 3: Many-to-Many Relationships

```python
# models.py
class Book(models.Model):
    title = models.CharField(max_length=200)
    tags = models.ManyToManyField('Tag', related_name='books')

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

# serializers.py
class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']

class BookSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True)

    class Meta:
        model = Book
        fields = ['id', 'title', 'tags']

    def create(self, validated_data):
        tags_data = validated_data.pop('tags')

        # Create book first (M2M requires saved instance)
        book = Book.objects.create(**validated_data)

        # Get or create each tag
        for tag_data in tags_data:
            tag, created = Tag.objects.get_or_create(name=tag_data['name'])
            book.tags.add(tag)

        return book

    def update(self, instance, validated_data):
        tags_data = validated_data.pop('tags', None)

        # Update book fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update tags if provided
        if tags_data is not None:
            instance.tags.clear()
            for tag_data in tags_data:
                tag, created = Tag.objects.get_or_create(name=tag_data['name'])
                instance.tags.add(tag)

        return instance

# Usage
data = {
    'title': 'Django Book',
    'tags': [{'name': 'python'}, {'name': 'web'}, {'name': 'django'}]
}
serializer = BookSerializer(data=data)
if serializer.is_valid():
    book = serializer.save()
```

## Pattern 4: Reverse ForeignKey (One-to-Many)

```python
# models.py
class Author(models.Model):
    name = models.CharField(max_length=100)

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='books')

# serializers.py
class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['id', 'title']

class AuthorSerializer(serializers.ModelSerializer):
    books = BookSerializer(many=True)

    class Meta:
        model = Author
        fields = ['id', 'name', 'books']

    def create(self, validated_data):
        books_data = validated_data.pop('books')

        # Create author first
        author = Author.objects.create(**validated_data)

        # Create each book
        for book_data in books_data:
            Book.objects.create(author=author, **book_data)

        return author

    def update(self, instance, validated_data):
        books_data = validated_data.pop('books', None)

        # Update author
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Replace all books (simple strategy)
        if books_data is not None:
            instance.books.all().delete()
            for book_data in books_data:
                Book.objects.create(author=instance, **book_data)

        return instance
```

## Pattern 5: Use Transactions

Always wrap nested creates/updates in transactions:

```python
from django.db import transaction

class BookSerializer(serializers.ModelSerializer):
    author = AuthorSerializer()
    tags = TagSerializer(many=True)

    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'tags']

    @transaction.atomic
    def create(self, validated_data):
        """All or nothing - if any part fails, rollback everything"""
        author_data = validated_data.pop('author')
        tags_data = validated_data.pop('tags')

        # Create author
        author = Author.objects.create(**author_data)

        # Create book
        book = Book.objects.create(author=author, **validated_data)

        # Create/add tags
        for tag_data in tags_data:
            tag, created = Tag.objects.get_or_create(**tag_data)
            book.tags.add(tag)

        return book

    @transaction.atomic
    def update(self, instance, validated_data):
        author_data = validated_data.pop('author', None)
        tags_data = validated_data.pop('tags', None)

        if author_data:
            for attr, value in author_data.items():
                setattr(instance.author, attr, value)
            instance.author.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if tags_data is not None:
            instance.tags.clear()
            for tag_data in tags_data:
                tag, created = Tag.objects.get_or_create(**tag_data)
                instance.tags.add(tag)

        return instance
```

## Pattern 6: Read/Write Separation (Recommended)

**Most common production pattern** - avoid nested writes entirely:

```python
class BookSerializer(serializers.ModelSerializer):
    # Write: accept just author ID
    author_id = serializers.PrimaryKeyRelatedField(
        source='author',
        queryset=Author.objects.all(),
        write_only=True
    )

    # Read: return full nested representation
    author = AuthorSerializer(read_only=True)

    class Meta:
        model = Book
        fields = ['id', 'title', 'author_id', 'author']

    # No custom create() or update() needed!

# Input (simple):  {"title": "Book", "author_id": 5}
# Output (rich):   {"id": 1, "title": "Book", "author": {"id": 5, "name": "Jane"}}
```

## Common Patterns Summary

```python
# 1. Simple nested create
def create(self, validated_data):
    nested_data = validated_data.pop('nested_field')
    nested_obj = NestedModel.objects.create(**nested_data)
    instance = MainModel.objects.create(nested_field=nested_obj, **validated_data)
    return instance

# 2. Get or create nested
def create(self, validated_data):
    nested_data = validated_data.pop('nested_field')
    nested_obj, created = NestedModel.objects.get_or_create(
        unique_field=nested_data['unique_field'],
        defaults=nested_data
    )
    instance = MainModel.objects.create(nested_field=nested_obj, **validated_data)
    return instance

# 3. Many-to-many
def create(self, validated_data):
    nested_data_list = validated_data.pop('nested_field')
    instance = MainModel.objects.create(**validated_data)
    for item in nested_data_list:
        nested_obj, _ = NestedModel.objects.get_or_create(**item)
        instance.nested_field.add(nested_obj)
    return instance

# 4. Reverse FK
def create(self, validated_data):
    nested_data_list = validated_data.pop('nested_field')
    instance = MainModel.objects.create(**validated_data)
    for item in nested_data_list:
        NestedModel.objects.create(main=instance, **item)
    return instance
```

## Troubleshooting

### "create() does not support writable nested fields"

Add custom create() method as shown in patterns above.

### "NOT NULL constraint failed"

Wrong order - create ForeignKey object before the object that references it:

```python
# Wrong
book = Book.objects.create(**validated_data)  # No author yet!
author = Author.objects.create(**author_data)

# Correct
author = Author.objects.create(**author_data)  # Create FK first
book = Book.objects.create(author=author, **validated_data)
```

### M2M requires saved instance

```python
# Wrong
book = Book(**validated_data)  # Not saved
book.tags.add(tag)  # ERROR!

# Correct
book = Book.objects.create(**validated_data)  # Saved
book.tags.add(tag)  # Works
```

### Partial updates not working

```python
# Pass partial=True
serializer = BookSerializer(book, data=data, partial=True)

# Check if nested data provided in update()
def update(self, instance, validated_data):
    nested = validated_data.pop('nested', None)
    if nested is not None:  # Only update if provided
        # update nested
        pass
```

## Best Practices

1. **Use transactions** for nested operations
2. **Use read/write separation** when possible (simplest)
3. **Document your logic** in docstrings
4. **Handle partial updates** explicitly
5. **Validate before creating** objects
