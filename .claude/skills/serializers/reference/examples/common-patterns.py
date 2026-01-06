"""
Common Serializer Patterns - Working Code Examples

This file contains working examples of common DRF serializer patterns.
Copy and adapt these patterns for your own use cases.

Each pattern includes:
- Model definitions
- Serializer implementation
- Usage examples
- Common variations
"""

# =============================================================================
# Pattern 1: Basic ModelSerializer with Validation
# =============================================================================

from django.db import models
from rest_framework import serializers

# Models
class Book(models.Model):
    title = models.CharField(max_length=200)
    isbn = models.CharField(max_length=13, unique=True)
    pages = models.IntegerField()
    published_date = models.DateField()
    price = models.DecimalField(max_digits=8, decimal_places=2)

# Serializer
class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['id', 'title', 'isbn', 'pages', 'published_date', 'price']
        read_only_fields = ['id']

    def validate_isbn(self, value):
        """Validate ISBN format"""
        if not value.isdigit() or len(value) != 13:
            raise serializers.ValidationError("ISBN must be exactly 13 digits")
        return value

    def validate_pages(self, value):
        """Validate pages is positive"""
        if value <= 0:
            raise serializers.ValidationError("Pages must be positive")
        return value

    def validate(self, attrs):
        """Cross-field validation"""
        if attrs['price'] > 1000 and attrs['pages'] < 100:
            raise serializers.ValidationError(
                "Books under 100 pages cannot cost more than $1000"
            )
        return attrs

# Usage
"""
# Create
data = {
    'title': 'Django Book',
    'isbn': '1234567890123',
    'pages': 300,
    'published_date': '2024-01-15',
    'price': '29.99'
}
serializer = BookSerializer(data=data)
if serializer.is_valid():
    book = serializer.save()

# Update
book = Book.objects.get(pk=1)
serializer = BookSerializer(book, data={'title': 'Updated Title'}, partial=True)
if serializer.is_valid():
    book = serializer.save()

# List
books = Book.objects.all()
serializer = BookSerializer(books, many=True)
data = serializer.data
"""


# =============================================================================
# Pattern 2: SerializerMethodField for Computed Values
# =============================================================================

class Author(models.Model):
    name = models.CharField(max_length=100)
    birth_date = models.DateField(null=True)

class BookWithAuthor(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='books')

class AuthorSerializer(serializers.ModelSerializer):
    # Computed fields
    age = serializers.SerializerMethodField()
    book_count = serializers.SerializerMethodField()
    latest_book = serializers.SerializerMethodField()

    class Meta:
        model = Author
        fields = ['id', 'name', 'birth_date', 'age', 'book_count', 'latest_book']

    def get_age(self, obj):
        """Calculate age from birth_date"""
        if not obj.birth_date:
            return None
        from datetime import date
        today = date.today()
        return today.year - obj.birth_date.year - (
            (today.month, today.day) < (obj.birth_date.month, obj.birth_date.day)
        )

    def get_book_count(self, obj):
        """Count books (optimized with annotate)"""
        # If using annotate in view: obj.book_count
        # Otherwise: obj.books.count()
        return getattr(obj, 'book_count', obj.books.count())

    def get_latest_book(self, obj):
        """Get latest book title"""
        latest = obj.books.order_by('-published_date').first()
        return latest.title if latest else None

# Optimized query in view
"""
from django.db.models import Count

# Annotate to avoid N+1 queries
authors = Author.objects.annotate(
    book_count=Count('books')
).prefetch_related('books')

serializer = AuthorSerializer(authors, many=True)
"""


# =============================================================================
# Pattern 3: source= Parameter for Field Mapping
# =============================================================================

class Product(models.Model):
    internal_name = models.CharField(max_length=200)
    public_description = models.TextField()
    manufacturer_name = models.CharField(max_length=100)

class ProductSerializer(serializers.ModelSerializer):
    # Map serializer fields to different model fields
    name = serializers.CharField(source='internal_name')
    description = serializers.CharField(source='public_description')

    # Access nested attributes
    manufacturer = serializers.CharField(source='manufacturer_name', read_only=True)

    # Use source='*' to access the entire object
    full_info = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'manufacturer', 'full_info']

    def get_full_info(self, obj):
        """source='*' means this method receives the full object"""
        return f"{obj.internal_name} by {obj.manufacturer_name}"


# =============================================================================
# Pattern 4: Read-Write Field Separation
# =============================================================================

class Article(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    content = models.TextField()

class ArticleSerializer(serializers.ModelSerializer):
    # Write-only: accept author ID for input
    author_id = serializers.PrimaryKeyRelatedField(
        source='author',
        queryset=Author.objects.all(),
        write_only=True
    )

    # Read-only: return full author details
    author = AuthorSerializer(read_only=True)

    # Read-only computed field
    word_count = serializers.SerializerMethodField()

    # Write-only sensitive field
    draft_notes = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Article
        fields = [
            'id', 'title', 'author_id', 'author',
            'content', 'word_count', 'draft_notes'
        ]

    def get_word_count(self, obj):
        return len(obj.content.split())

# Usage
"""
# Input (write):
{
    "title": "Article",
    "author_id": 5,
    "content": "...",
    "draft_notes": "Remember to review"
}

# Output (read):
{
    "id": 1,
    "title": "Article",
    "author": {"id": 5, "name": "Jane Smith", ...},
    "content": "...",
    "word_count": 150
}
"""


# =============================================================================
# Pattern 5: Dynamic Fields (Flexible Serializers)
# =============================================================================

class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    """
    A ModelSerializer that takes an additional `fields` argument to
    dynamically select fields to include.
    """

    def __init__(self, *args, **kwargs):
        # Extract fields argument
        fields = kwargs.pop('fields', None)

        # Instantiate parent
        super().__init__(*args, **kwargs)

        if fields is not None:
            # Drop any fields not specified in the `fields` argument
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)

class FlexibleBookSerializer(DynamicFieldsModelSerializer):
    author = AuthorSerializer(read_only=True)

    class Meta:
        model = BookWithAuthor
        fields = ['id', 'title', 'author', 'published_date', 'pages']

# Usage
"""
# Only include specific fields
serializer = FlexibleBookSerializer(
    book,
    fields=['id', 'title', 'author']
)

# Or via query params in view
class BookView(APIView):
    def get(self, request, pk):
        book = Book.objects.get(pk=pk)
        fields = request.query_params.get('fields')
        if fields:
            fields = fields.split(',')
        serializer = FlexibleBookSerializer(book, fields=fields)
        return Response(serializer.data)

# Request: /api/books/1/?fields=id,title
# Response: {"id": 1, "title": "Book Title"}
"""


# =============================================================================
# Pattern 6: Writable Nested Serializer (One-to-One/FK)
# =============================================================================

class Profile(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE)
    bio = models.TextField()
    location = models.CharField(max_length=100)

class User(models.Model):
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True)

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['bio', 'location']

class UserWithProfileSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'profile']

    def create(self, validated_data):
        from django.db import transaction

        with transaction.atomic():
            profile_data = validated_data.pop('profile')
            user = User.objects.create(**validated_data)
            Profile.objects.create(user=user, **profile_data)
            return user

    def update(self, instance, validated_data):
        from django.db import transaction

        with transaction.atomic():
            profile_data = validated_data.pop('profile', None)

            # Update user
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            # Update profile
            if profile_data is not None:
                profile = instance.profile
                for attr, value in profile_data.items():
                    setattr(profile, attr, value)
                profile.save()

            return instance


# =============================================================================
# Pattern 7: Writable Nested Many-to-Many
# =============================================================================

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)

class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    tags = models.ManyToManyField(Tag, related_name='posts')

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']

class BlogPostSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True)

    class Meta:
        model = BlogPost
        fields = ['id', 'title', 'content', 'tags']

    def create(self, validated_data):
        from django.db import transaction
        from django.utils.text import slugify

        with transaction.atomic():
            tags_data = validated_data.pop('tags')

            # Create post
            post = BlogPost.objects.create(**validated_data)

            # Get or create tags
            for tag_data in tags_data:
                if 'slug' not in tag_data:
                    tag_data['slug'] = slugify(tag_data['name'])
                tag, created = Tag.objects.get_or_create(
                    slug=tag_data['slug'],
                    defaults={'name': tag_data['name']}
                )
                post.tags.add(tag)

            return post

    def update(self, instance, validated_data):
        from django.db import transaction
        from django.utils.text import slugify

        with transaction.atomic():
            tags_data = validated_data.pop('tags', None)

            # Update post
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            # Update tags
            if tags_data is not None:
                instance.tags.clear()
                for tag_data in tags_data:
                    if 'slug' not in tag_data:
                        tag_data['slug'] = slugify(tag_data['name'])
                    tag, created = Tag.objects.get_or_create(
                        slug=tag_data['slug'],
                        defaults={'name': tag_data['name']}
                    )
                    instance.tags.add(tag)

            return instance


# =============================================================================
# Pattern 8: Polymorphic Serializers (Different Types)
# =============================================================================

class BaseNotification(models.Model):
    """Base notification model"""
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    type = models.CharField(max_length=20)

    class Meta:
        abstract = True

class EmailNotification(BaseNotification):
    email_subject = models.CharField(max_length=200)
    email_body = models.TextField()

class SMSNotification(BaseNotification):
    phone_number = models.CharField(max_length=20)
    message = models.CharField(max_length=160)

class NotificationSerializer(serializers.Serializer):
    """Base serializer that dispatches to type-specific serializers"""

    def to_representation(self, instance):
        """Serialize based on type"""
        if isinstance(instance, EmailNotification):
            return EmailNotificationSerializer(instance).data
        elif isinstance(instance, SMSNotification):
            return SMSNotificationSerializer(instance).data
        return super().to_representation(instance)

    def to_internal_value(self, data):
        """Deserialize based on type field"""
        notification_type = data.get('type')

        if notification_type == 'email':
            serializer = EmailNotificationSerializer(data=data)
        elif notification_type == 'sms':
            serializer = SMSNotificationSerializer(data=data)
        else:
            raise serializers.ValidationError({'type': 'Unknown notification type'})

        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

class EmailNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailNotification
        fields = ['id', 'user', 'type', 'email_subject', 'email_body', 'created_at']

class SMSNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMSNotification
        fields = ['id', 'user', 'type', 'phone_number', 'message', 'created_at']


# =============================================================================
# Pattern 9: Context-Aware Serializers
# =============================================================================

class PermissionAwareSerializer(serializers.ModelSerializer):
    """Serializer that changes behavior based on user permissions"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get request from context
        request = self.context.get('request')
        if not request:
            return

        # Modify fields based on user permissions
        if not request.user.is_staff:
            # Non-staff can't see these fields
            self.fields.pop('internal_notes', None)
            self.fields.pop('cost', None)

        if not request.user.is_authenticated:
            # Anonymous users can't see these fields
            self.fields.pop('email', None)

class SensitiveDataSerializer(serializers.ModelSerializer):
    """Serializer that requires specific permissions"""

    internal_notes = serializers.CharField(read_only=True)
    cost = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    email = serializers.EmailField(read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'internal_notes', 'cost', 'email']

# Usage
"""
# Pass request in context
serializer = PermissionAwareSerializer(
    product,
    context={'request': request}
)

# Staff sees all fields
# Non-staff doesn't see internal_notes, cost
# Anonymous doesn't see email
"""


# =============================================================================
# Pattern 10: Custom Validation with External Services
# =============================================================================

class AddressSerializer(serializers.Serializer):
    street = serializers.CharField(max_length=200)
    city = serializers.CharField(max_length=100)
    state = serializers.CharField(max_length=2)
    zip_code = serializers.CharField(max_length=10)

    def validate(self, attrs):
        """Validate address with external service"""
        # Mock external validation
        # In reality, you'd call a geocoding API

        # Cache validation results
        cache_key = f"address_{attrs['zip_code']}"
        # Check cache first...

        # Validate format
        if len(attrs['zip_code']) not in [5, 10]:
            raise serializers.ValidationError({
                'zip_code': 'Invalid ZIP code format'
            })

        # Validate state
        valid_states = ['CA', 'NY', 'TX', 'FL']  # etc.
        if attrs['state'] not in valid_states:
            raise serializers.ValidationError({
                'state': 'Invalid state code'
            })

        return attrs


# =============================================================================
# Pattern 11: Bulk Operations with ListSerializer
# =============================================================================

class BulkUpdateListSerializer(serializers.ListSerializer):
    """Custom list serializer for bulk updates"""

    def update(self, instances, validated_data):
        """
        Bulk update - match by ID.
        """
        from django.db import transaction

        # Map instances by ID
        instance_mapping = {instance.id: instance for instance in instances}

        # Prepare updates
        updated_instances = []

        with transaction.atomic():
            for item in validated_data:
                instance_id = item.get('id')
                if instance_id and instance_id in instance_mapping:
                    instance = instance_mapping[instance_id]

                    # Update fields
                    for attr, value in item.items():
                        if attr != 'id':
                            setattr(instance, attr, value)

                    instance.save()
                    updated_instances.append(instance)

        return updated_instances

class BulkUpdateBookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['id', 'title', 'pages', 'price']
        list_serializer_class = BulkUpdateListSerializer

# Usage
"""
# Bulk create
data = [
    {'title': 'Book 1', 'pages': 100, 'price': '10.00'},
    {'title': 'Book 2', 'pages': 200, 'price': '20.00'},
]
serializer = BulkUpdateBookSerializer(data=data, many=True)
if serializer.is_valid():
    books = serializer.save()

# Bulk update
books = Book.objects.filter(author=author)
data = [
    {'id': 1, 'price': '15.00'},
    {'id': 2, 'price': '25.00'},
]
serializer = BulkUpdateBookSerializer(books, data=data, many=True)
if serializer.is_valid():
    serializer.save()
"""


# =============================================================================
# Pattern 12: File Upload with Validation
# =============================================================================

class DocumentSerializer(serializers.Serializer):
    """Serializer for file uploads with validation"""

    title = serializers.CharField(max_length=200)
    file = serializers.FileField()
    category = serializers.ChoiceField(choices=['pdf', 'image', 'video'])

    def validate_file(self, value):
        """Validate file size and type"""
        # Check file size (5MB limit)
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("File size must be under 5MB")

        # Check file extension
        import os
        ext = os.path.splitext(value.name)[1].lower()
        valid_extensions = ['.pdf', '.jpg', '.png', '.mp4']
        if ext not in valid_extensions:
            raise serializers.ValidationError(
                f"Invalid file type. Must be one of: {', '.join(valid_extensions)}"
            )

        return value

    def validate(self, attrs):
        """Cross-field validation"""
        file = attrs['file']
        category = attrs['category']

        # Validate file type matches category
        import os
        ext = os.path.splitext(file.name)[1].lower()

        if category == 'pdf' and ext != '.pdf':
            raise serializers.ValidationError("PDF category requires .pdf file")
        elif category == 'image' and ext not in ['.jpg', '.png']:
            raise serializers.ValidationError("Image category requires .jpg or .png")
        elif category == 'video' and ext != '.mp4':
            raise serializers.ValidationError("Video category requires .mp4")

        return attrs

    def create(self, validated_data):
        """Save file and create document record"""
        from django.core.files.storage import default_storage

        file = validated_data['file']

        # Save file
        filename = default_storage.save(file.name, file)

        # Create document record (you'd have a Document model)
        # document = Document.objects.create(
        #     title=validated_data['title'],
        #     file_path=filename,
        #     category=validated_data['category']
        # )

        return {
            'title': validated_data['title'],
            'file_path': filename,
            'category': validated_data['category']
        }


# =============================================================================
# Pattern 13: Custom Field for Special Formatting
# =============================================================================

class ColorField(serializers.Field):
    """
    Custom field for color values.
    Accepts hex (#FF0000) or rgb (255,0,0) format.
    Always outputs as hex.
    """

    def to_representation(self, value):
        """Convert to hex format for output"""
        if isinstance(value, str) and value.startswith('#'):
            return value
        # Assume it's stored as hex in database
        return value

    def to_internal_value(self, data):
        """Accept hex or rgb, convert to hex"""
        import re

        if isinstance(data, str):
            # Hex format
            if re.match(r'^#[0-9A-Fa-f]{6}$', data):
                return data.upper()

            # RGB format
            rgb_match = re.match(r'^(\d{1,3}),(\d{1,3}),(\d{1,3})$', data)
            if rgb_match:
                r, g, b = map(int, rgb_match.groups())
                if all(0 <= x <= 255 for x in [r, g, b]):
                    return f'#{r:02X}{g:02X}{b:02X}'

        raise serializers.ValidationError(
            'Invalid color format. Use hex (#FF0000) or rgb (255,0,0)'
        )

class ProductWithColorSerializer(serializers.ModelSerializer):
    color = ColorField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'color']

# Usage
"""
# Input: {"name": "Product", "color": "255,0,0"}
# Output: {"id": 1, "name": "Product", "color": "#FF0000"}

# Input: {"name": "Product", "color": "#00FF00"}
# Output: {"id": 1, "name": "Product", "color": "#00FF00"}
"""


# =============================================================================
# Pattern 14: Optimized Queries with Prefetching
# =============================================================================

class OptimizedAuthorSerializer(serializers.ModelSerializer):
    """Author serializer optimized to avoid N+1 queries"""

    books = serializers.SerializerMethodField()
    total_pages = serializers.SerializerMethodField()

    class Meta:
        model = Author
        fields = ['id', 'name', 'books', 'total_pages']

    def get_books(self, obj):
        """
        Get books - assumes they're prefetched.
        Using .all() on prefetched queryset doesn't hit DB.
        """
        # If prefetched: no extra query
        # If not prefetched: N+1 problem!
        books = obj.books.all()
        return BookSerializer(books, many=True).data

    def get_total_pages(self, obj):
        """
        Get total pages - assumes annotation or prefetch.
        """
        # Option 1: If annotated in queryset
        if hasattr(obj, 'total_pages'):
            return obj.total_pages

        # Option 2: If prefetched, sum in Python (no DB hit)
        return sum(book.pages for book in obj.books.all())

# Optimized query
"""
from django.db.models import Sum, Prefetch

# Option 1: Prefetch related objects
authors = Author.objects.prefetch_related('books').all()

# Option 2: Prefetch with custom queryset
authors = Author.objects.prefetch_related(
    Prefetch(
        'books',
        queryset=Book.objects.filter(published_date__year=2024)
    )
).all()

# Option 3: Annotate aggregates
authors = Author.objects.annotate(
    total_pages=Sum('books__pages')
).all()

serializer = OptimizedAuthorSerializer(authors, many=True)
# No N+1 queries!
"""


# =============================================================================
# Pattern 15: Pagination-Aware Serializers
# =============================================================================

from rest_framework.pagination import PageNumberPagination

class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class PaginatedBookListSerializer(serializers.Serializer):
    """Wrapper serializer for paginated results"""
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = BookSerializer(many=True)

# Usage in view
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def book_list(request):
    books = Book.objects.all()

    # Paginate
    paginator = CustomPagination()
    paginated_books = paginator.paginate_queryset(books, request)

    # Serialize
    serializer = BookSerializer(paginated_books, many=True)

    # Return paginated response
    return paginator.get_paginated_response(serializer.data)
"""


# =============================================================================
# Summary of Patterns
# =============================================================================

"""
1. Basic ModelSerializer - Standard CRUD with validation
2. SerializerMethodField - Computed/derived values
3. source parameter - Map fields to different names
4. Read-Write separation - Different fields for input/output
5. Dynamic fields - Flexible field inclusion
6. Writable nested (FK) - Handle nested object creation
7. Writable nested (M2M) - Handle many-to-many relationships
8. Polymorphic - Different types of objects
9. Context-aware - Behavior based on request/user
10. External validation - Integrate with external services
11. Bulk operations - Efficient batch create/update
12. File uploads - Handle file validation and storage
13. Custom fields - Special data type handling
14. Query optimization - Avoid N+1 problems
15. Pagination - Handle paginated responses

Copy and adapt these patterns for your specific use cases!
"""
