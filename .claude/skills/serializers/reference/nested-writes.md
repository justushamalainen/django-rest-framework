# Writable Nested Serializers

**CRITICAL SKILL:** This is the #1 pain point for DRF developers. By default, ModelSerializer **does not support** writable nested relationships. You must implement custom `create()` and `update()` methods.

## The Problem

By default, this doesn't work:

```python
# models.py
class Author(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)

# serializers.py
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
data = {
    'title': 'Django Book',
    'author': {'name': 'Jane Smith', 'email': 'jane@example.com'}
}
serializer = BookSerializer(data=data)
serializer.is_valid()  # ✅ This works
serializer.save()      # ❌ CRASH! "The .create() method does not support writable nested fields"
```

**Why?** DRF doesn't know your business logic:
- Should it create a new Author or look up an existing one?
- What if the nested object already exists?
- What about validation and transactions?
- What about many-to-many relationships?

You must implement `create()` and `update()` yourself.

## Solution Patterns

### Pattern 1: Create Nested Object (One-to-One / Foreign Key)

Create the nested object if it doesn't exist:

```python
class BookSerializer(serializers.ModelSerializer):
    author = AuthorSerializer()

    class Meta:
        model = Book
        fields = ['id', 'title', 'author']

    def create(self, validated_data):
        """
        Handle creation with nested author.
        validated_data = {
            'title': 'Book Title',
            'author': {'name': 'Jane', 'email': 'jane@example.com'}
        }
        """
        # Extract nested data
        author_data = validated_data.pop('author')

        # Create the nested object
        author = Author.objects.create(**author_data)

        # Create the main object with the nested object
        book = Book.objects.create(author=author, **validated_data)

        return book

    def update(self, instance, validated_data):
        """
        Handle update with nested author.
        instance = Book object being updated
        validated_data = updated data dict
        """
        # Extract nested data (may not be present in partial updates)
        author_data = validated_data.pop('author', None)

        # Update the nested object if provided
        if author_data is not None:
            # Update author fields
            for attr, value in author_data.items():
                setattr(instance.author, attr, value)
            instance.author.save()

        # Update main object fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance

# Usage:
# CREATE
data = {
    'title': 'New Book',
    'author': {'name': 'Jane Smith', 'email': 'jane@example.com'}
}
serializer = BookSerializer(data=data)
if serializer.is_valid():
    book = serializer.save()  # Creates both Book and Author

# UPDATE
book = Book.objects.get(pk=1)
data = {
    'title': 'Updated Title',
    'author': {'name': 'Jane Doe', 'email': 'jane.doe@example.com'}
}
serializer = BookSerializer(book, data=data)
if serializer.is_valid():
    book = serializer.save()  # Updates both Book and Author
```

### Pattern 2: Get or Create Nested Object

More realistic - look up existing or create new:

```python
class BookSerializer(serializers.ModelSerializer):
    author = AuthorSerializer()

    class Meta:
        model = Book
        fields = ['id', 'title', 'author']

    def create(self, validated_data):
        """Get or create author by email"""
        author_data = validated_data.pop('author')

        # Try to find existing author by email
        author, created = Author.objects.get_or_create(
            email=author_data['email'],
            defaults={'name': author_data['name']}
        )

        # If author exists, optionally update name
        if not created and 'name' in author_data:
            author.name = author_data['name']
            author.save()

        book = Book.objects.create(author=author, **validated_data)
        return book

    def update(self, instance, validated_data):
        """Update author or reassign to different author"""
        author_data = validated_data.pop('author', None)

        if author_data is not None:
            # Get or create the author
            author, created = Author.objects.get_or_create(
                email=author_data['email'],
                defaults={'name': author_data['name']}
            )

            # Assign to book (might change author)
            instance.author = author

        # Update book fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance
```

### Pattern 3: Many-to-Many Relationships

Handle lists of nested objects:

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
        """Create with many-to-many nested objects"""
        tags_data = validated_data.pop('tags')

        # Create the book first (M2M requires saved instance)
        book = Book.objects.create(**validated_data)

        # Create or get each tag and add to book
        for tag_data in tags_data:
            tag, created = Tag.objects.get_or_create(
                name=tag_data['name']
            )
            book.tags.add(tag)

        return book

    def update(self, instance, validated_data):
        """Update many-to-many relationship"""
        tags_data = validated_data.pop('tags', None)

        # Update book fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update tags if provided
        if tags_data is not None:
            # Clear existing tags
            instance.tags.clear()

            # Add new tags
            for tag_data in tags_data:
                tag, created = Tag.objects.get_or_create(
                    name=tag_data['name']
                )
                instance.tags.add(tag)

        return instance

# Usage:
data = {
    'title': 'Django Book',
    'tags': [
        {'name': 'python'},
        {'name': 'web'},
        {'name': 'django'}
    ]
}
serializer = BookSerializer(data=data)
if serializer.is_valid():
    book = serializer.save()
```

### Pattern 4: Reverse Foreign Key (One-to-Many)

Handle a list of related objects on the "one" side:

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
    # Reverse FK - list of books
    books = BookSerializer(many=True)

    class Meta:
        model = Author
        fields = ['id', 'name', 'books']

    def create(self, validated_data):
        """Create author with multiple books"""
        books_data = validated_data.pop('books')

        # Create author first
        author = Author.objects.create(**validated_data)

        # Create each book with this author
        for book_data in books_data:
            Book.objects.create(author=author, **book_data)

        return author

    def update(self, instance, validated_data):
        """Update author and their books"""
        books_data = validated_data.pop('books', None)

        # Update author fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if books_data is not None:
            # Strategy 1: Replace all books (delete old, create new)
            instance.books.all().delete()
            for book_data in books_data:
                Book.objects.create(author=instance, **book_data)

            # Strategy 2: Update by ID (more complex but preserves books)
            # See Pattern 5 below

        return instance

# Usage:
data = {
    'name': 'Jane Smith',
    'books': [
        {'title': 'Book 1'},
        {'title': 'Book 2'},
        {'title': 'Book 3'}
    ]
}
serializer = AuthorSerializer(data=data)
if serializer.is_valid():
    author = serializer.save()
    # Creates 1 Author and 3 Books
```

### Pattern 5: Update by ID (Preserve Existing Objects)

More sophisticated update that preserves existing objects:

```python
class AuthorSerializer(serializers.ModelSerializer):
    books = BookSerializer(many=True)

    class Meta:
        model = Author
        fields = ['id', 'name', 'books']

    def update(self, instance, validated_data):
        """Update books by ID - preserve, update, or delete"""
        books_data = validated_data.pop('books', None)

        # Update author
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if books_data is not None:
            # Get IDs of books in the input
            input_book_ids = [
                book['id'] for book in books_data if 'id' in book
            ]

            # Delete books not in input (if they have IDs)
            if input_book_ids:
                instance.books.exclude(id__in=input_book_ids).delete()

            # Update or create each book
            for book_data in books_data:
                book_id = book_data.get('id')

                if book_id:
                    # Update existing book
                    try:
                        book = Book.objects.get(id=book_id, author=instance)
                        for attr, value in book_data.items():
                            if attr != 'id':
                                setattr(book, attr, value)
                        book.save()
                    except Book.DoesNotExist:
                        # ID provided but doesn't exist - skip or error
                        pass
                else:
                    # Create new book
                    Book.objects.create(author=instance, **book_data)

        return instance

# Usage:
# Original: Author with books [1, 2, 3]
author = Author.objects.get(pk=1)

data = {
    'name': 'Updated Name',
    'books': [
        {'id': 1, 'title': 'Updated Book 1'},  # Update existing
        {'id': 2, 'title': 'Updated Book 2'},  # Update existing
        # Book 3 not included - will be deleted
        {'title': 'New Book 4'}  # Create new
    ]
}
serializer = AuthorSerializer(author, data=data)
if serializer.is_valid():
    author = serializer.save()
    # Result: Books [1, 2, 4] (3 deleted, 4 created)
```

### Pattern 6: Transactions for Safety

Wrap in transaction to ensure atomicity:

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
        """
        Create with transaction - all or nothing.
        If any part fails, entire creation is rolled back.
        """
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
        """Update with transaction"""
        author_data = validated_data.pop('author', None)
        tags_data = validated_data.pop('tags', None)

        # Update author
        if author_data:
            for attr, value in author_data.items():
                setattr(instance.author, attr, value)
            instance.author.save()

        # Update book
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update tags
        if tags_data is not None:
            instance.tags.clear()
            for tag_data in tags_data:
                tag, created = Tag.objects.get_or_create(**tag_data)
                instance.tags.add(tag)

        return instance
```

### Pattern 7: Mixed Write Modes

Write with ID, read with full details:

```python
class BookSerializer(serializers.ModelSerializer):
    # For writing - accept just the ID
    author_id = serializers.PrimaryKeyRelatedField(
        source='author',
        queryset=Author.objects.all(),
        write_only=True
    )

    # For reading - return full nested representation
    author = AuthorSerializer(read_only=True)

    class Meta:
        model = Book
        fields = ['id', 'title', 'author_id', 'author']

    # No custom create() or update() needed!
    # ModelSerializer's default implementation handles author_id

# Input (simple):
# POST {"title": "New Book", "author_id": 5}

# Output (detailed):
# {
#     "id": 1,
#     "title": "New Book",
#     "author": {
#         "id": 5,
#         "name": "Jane Smith",
#         "email": "jane@example.com"
#     }
# }
```

## Deep Nesting (3+ Levels)

Handle deeply nested structures:

```python
# models.py
class Publisher(models.Model):
    name = models.CharField(max_length=100)

class Author(models.Model):
    name = models.CharField(max_length=100)
    publisher = models.ForeignKey(Publisher, on_delete=models.CASCADE)

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)

# serializers.py
class PublisherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publisher
        fields = ['id', 'name']

class AuthorSerializer(serializers.ModelSerializer):
    publisher = PublisherSerializer()

    class Meta:
        model = Author
        fields = ['id', 'name', 'publisher']

    def create(self, validated_data):
        publisher_data = validated_data.pop('publisher')
        publisher, _ = Publisher.objects.get_or_create(**publisher_data)
        author = Author.objects.create(publisher=publisher, **validated_data)
        return author

    def update(self, instance, validated_data):
        publisher_data = validated_data.pop('publisher', None)

        if publisher_data:
            publisher, _ = Publisher.objects.get_or_create(**publisher_data)
            instance.publisher = publisher

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class BookSerializer(serializers.ModelSerializer):
    author = AuthorSerializer()

    class Meta:
        model = Book
        fields = ['id', 'title', 'author']

    @transaction.atomic
    def create(self, validated_data):
        """3 levels deep: Book -> Author -> Publisher"""
        author_data = validated_data.pop('author')
        publisher_data = author_data.pop('publisher')

        # Create from deepest to shallowest
        publisher, _ = Publisher.objects.get_or_create(**publisher_data)
        author = Author.objects.create(publisher=publisher, **author_data)
        book = Book.objects.create(author=author, **validated_data)

        return book

# Usage - 3 levels deep:
data = {
    'title': 'Django Book',
    'author': {
        'name': 'Jane Smith',
        'publisher': {
            'name': 'Tech Books Inc'
        }
    }
}
```

## Common Patterns Summary

### Create Patterns

```python
def create(self, validated_data):
    # 1. Simple nested create
    nested_data = validated_data.pop('nested_field')
    nested_obj = NestedModel.objects.create(**nested_data)
    instance = MainModel.objects.create(nested_field=nested_obj, **validated_data)
    return instance

    # 2. Get or create nested
    nested_data = validated_data.pop('nested_field')
    nested_obj, created = NestedModel.objects.get_or_create(
        unique_field=nested_data['unique_field'],
        defaults=nested_data
    )
    instance = MainModel.objects.create(nested_field=nested_obj, **validated_data)
    return instance

    # 3. Many-to-many
    nested_data_list = validated_data.pop('nested_field')
    instance = MainModel.objects.create(**validated_data)
    for item in nested_data_list:
        nested_obj, _ = NestedModel.objects.get_or_create(**item)
        instance.nested_field.add(nested_obj)
    return instance

    # 4. Reverse FK (one-to-many)
    nested_data_list = validated_data.pop('nested_field')
    instance = MainModel.objects.create(**validated_data)
    for item in nested_data_list:
        NestedModel.objects.create(main=instance, **item)
    return instance
```

### Update Patterns

```python
def update(self, instance, validated_data):
    # 1. Update nested object in-place
    nested_data = validated_data.pop('nested_field', None)
    if nested_data:
        for attr, value in nested_data.items():
            setattr(instance.nested_field, attr, value)
        instance.nested_field.save()

    for attr, value in validated_data.items():
        setattr(instance, attr, value)
    instance.save()
    return instance

    # 2. Replace nested object
    nested_data = validated_data.pop('nested_field', None)
    if nested_data:
        nested_obj, _ = NestedModel.objects.get_or_create(**nested_data)
        instance.nested_field = nested_obj

    for attr, value in validated_data.items():
        setattr(instance, attr, value)
    instance.save()
    return instance

    # 3. Replace M2M
    nested_data_list = validated_data.pop('nested_field', None)
    if nested_data_list is not None:
        instance.nested_field.clear()
        for item in nested_data_list:
            nested_obj, _ = NestedModel.objects.get_or_create(**item)
            instance.nested_field.add(nested_obj)

    for attr, value in validated_data.items():
        setattr(instance, attr, value)
    instance.save()
    return instance

    # 4. Update by ID (preserve objects)
    nested_data_list = validated_data.pop('nested_field', None)
    if nested_data_list is not None:
        input_ids = [item['id'] for item in nested_data_list if 'id' in item]
        if input_ids:
            instance.nested_field.exclude(id__in=input_ids).delete()

        for item in nested_data_list:
            if 'id' in item:
                # Update existing
                nested_obj = NestedModel.objects.get(id=item['id'])
                for attr, value in item.items():
                    if attr != 'id':
                        setattr(nested_obj, attr, value)
                nested_obj.save()
            else:
                # Create new
                NestedModel.objects.create(main=instance, **item)

    for attr, value in validated_data.items():
        setattr(instance, attr, value)
    instance.save()
    return instance
```

## Best Practices

### 1. Use Transactions

Always wrap nested creates/updates in transactions:

```python
@transaction.atomic
def create(self, validated_data):
    # ...
```

### 2. Handle Partial Updates

Check if nested data is provided:

```python
def update(self, instance, validated_data):
    nested_data = validated_data.pop('nested', None)
    # None means not provided (don't update)
    # {} means provided but empty (might mean clear relationship)

    if nested_data is not None:
        # Update nested
        pass
```

### 3. Validate Before Creating

Validate nested data before creating objects:

```python
def create(self, validated_data):
    # validated_data is already validated by is_valid()
    # But you can add extra checks

    author_data = validated_data.pop('author')

    # Extra validation
    if Author.objects.filter(email=author_data['email']).exists():
        # Decide: error or reuse existing
        pass

    # Create...
```

### 4. Document Your Logic

```python
def create(self, validated_data):
    """
    Create book with nested author.

    Logic:
    - If author email exists, reuse that author
    - If author email is new, create new author
    - Update author name if provided and different

    Example:
        data = {
            'title': 'Book',
            'author': {'name': 'Jane', 'email': 'jane@example.com'}
        }
    """
    # Implementation...
```

### 5. Consider Using write_only and read_only

```python
class BookSerializer(serializers.ModelSerializer):
    # Write: accept ID
    author_id = serializers.PrimaryKeyRelatedField(
        source='author',
        queryset=Author.objects.all(),
        write_only=True
    )

    # Read: full nested representation
    author = AuthorSerializer(read_only=True)

    class Meta:
        model = Book
        fields = ['id', 'title', 'author_id', 'author']

    # No custom create/update needed!
```

This avoids complex nested write logic entirely!

## Troubleshooting

### "The .create() method does not support writable nested fields"

You're using a nested serializer without custom create():

```python
# Add create() method as shown in patterns above
def create(self, validated_data):
    nested = validated_data.pop('nested_field')
    # Handle nested creation
    return instance
```

### "NOT NULL constraint failed"

You're trying to create an object without its required FK:

```python
# Wrong order
author_data = validated_data.pop('author')
book = Book.objects.create(**validated_data)  # No author yet!
author = Author.objects.create(**author_data)

# Correct order
author_data = validated_data.pop('author')
author = Author.objects.create(**author_data)  # Create FK first
book = Book.objects.create(author=author, **validated_data)
```

### M2M requires saved instance

```python
# Wrong
book = Book(**validated_data)  # Not saved yet
book.tags.add(tag)  # ERROR! Can't add M2M to unsaved object

# Correct
book = Book.objects.create(**validated_data)  # Saved
book.tags.add(tag)  # Now it works
```

### Nested validation not running

Nested serializer validation runs during `is_valid()`:

```python
serializer = BookSerializer(data=data)
serializer.is_valid()  # Validates nested author too
# If author has invalid email, serializer.errors includes it
```

### Partial updates not working

Handle partial updates explicitly:

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
