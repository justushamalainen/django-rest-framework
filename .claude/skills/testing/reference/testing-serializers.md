# Testing Serializers and Validation

Comprehensive guide to testing DRF serializers, validation logic, and data transformations.

## Table of Contents

- [Basic Serializer Testing](#basic-serializer-testing)
- [Testing Validation](#testing-validation)
- [Testing Serialization](#testing-serialization)
- [Testing Deserialization](#testing-deserialization)
- [Testing Nested Serializers](#testing-nested-serializers)
- [Testing Custom Fields](#testing-custom-fields)
- [Testing Custom Validation](#testing-custom-validation)
- [Testing SerializerMethodField](#testing-serializermethodfield)
- [Testing Model Serializers](#testing-model-serializers)

## Basic Serializer Testing

### Simple Serializer

```python
# serializers.py
from rest_framework import serializers


class ArticleSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    content = serializers.CharField()
    published = serializers.BooleanField(default=False)
    created = serializers.DateTimeField(read_only=True)


# tests.py
from django.test import TestCase


class ArticleSerializerTest(TestCase):
    def test_serializer_with_valid_data(self):
        """Serializer should validate correct data."""
        data = {
            'title': 'Test Article',
            'content': 'Test content'
        }
        serializer = ArticleSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['title'], 'Test Article')
        self.assertEqual(serializer.validated_data['content'], 'Test content')
        self.assertEqual(serializer.validated_data['published'], False)

    def test_serializer_with_invalid_data(self):
        """Serializer should reject invalid data."""
        data = {'title': ''}  # Empty title, missing content
        serializer = ArticleSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn('title', serializer.errors)
        self.assertIn('content', serializer.errors)

    def test_serializer_serialization(self):
        """Serializer should serialize objects correctly."""
        article = Article.objects.create(
            title='Test',
            content='Content',
            published=True
        )
        serializer = ArticleSerializer(article)

        self.assertEqual(serializer.data['title'], 'Test')
        self.assertEqual(serializer.data['content'], 'Content')
        self.assertEqual(serializer.data['published'], True)
        self.assertIn('created', serializer.data)
```

## Testing Validation

### Required Fields

```python
class ArticleSerializer(serializers.Serializer):
    title = serializers.CharField(required=True)
    content = serializers.CharField(required=True)
    tags = serializers.ListField(required=False)


class ArticleValidationTest(TestCase):
    def test_missing_required_field(self):
        """Should reject data missing required fields."""
        data = {'title': 'Test'}  # Missing content
        serializer = ArticleSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn('content', serializer.errors)
        self.assertEqual(
            serializer.errors['content'][0],
            'This field is required.'
        )

    def test_optional_field_missing(self):
        """Should accept data with missing optional fields."""
        data = {
            'title': 'Test',
            'content': 'Content'
            # tags is optional
        }
        serializer = ArticleSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertNotIn('tags', serializer.validated_data)
```

### Field-Level Validation

```python
class ArticleSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    content = serializers.CharField()

    def validate_title(self, value):
        """Validate title field."""
        if 'spam' in value.lower():
            raise serializers.ValidationError("Title cannot contain 'spam'")
        return value


class FieldLevelValidationTest(TestCase):
    def test_valid_title(self):
        """Should accept valid title."""
        data = {'title': 'Good Title', 'content': 'Content'}
        serializer = ArticleSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test_invalid_title(self):
        """Should reject title containing spam."""
        data = {'title': 'Spam Article', 'content': 'Content'}
        serializer = ArticleSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn('title', serializer.errors)
        self.assertIn("cannot contain 'spam'", str(serializer.errors['title']))
```

### Object-Level Validation

```python
class DateRangeSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, data):
        """Validate that end_date is after start_date."""
        if data['end_date'] < data['start_date']:
            raise serializers.ValidationError(
                "end_date must be after start_date"
            )
        return data


class ObjectLevelValidationTest(TestCase):
    def test_valid_date_range(self):
        """Should accept valid date range."""
        data = {
            'start_date': '2024-01-01',
            'end_date': '2024-12-31'
        }
        serializer = DateRangeSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test_invalid_date_range(self):
        """Should reject invalid date range."""
        data = {
            'start_date': '2024-12-31',
            'end_date': '2024-01-01'
        }
        serializer = DateRangeSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
```

### Validators

```python
from rest_framework.validators import UniqueValidator


class ArticleSerializer(serializers.ModelSerializer):
    title = serializers.CharField(
        validators=[
            UniqueValidator(
                queryset=Article.objects.all(),
                message="Title must be unique"
            )
        ]
    )

    class Meta:
        model = Article
        fields = ['title', 'content']


class ValidatorTest(TestCase):
    def test_unique_title(self):
        """Should reject duplicate titles."""
        Article.objects.create(title='Unique', content='Content')

        data = {'title': 'Unique', 'content': 'Different content'}
        serializer = ArticleSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn('title', serializer.errors)
        self.assertIn('unique', str(serializer.errors['title']).lower())

    def test_new_title(self):
        """Should accept new unique title."""
        data = {'title': 'New Title', 'content': 'Content'}
        serializer = ArticleSerializer(data=data)

        self.assertTrue(serializer.is_valid())
```

## Testing Serialization

### Serializing Single Objects

```python
class ArticleSerializationTest(TestCase):
    def setUp(self):
        self.article = Article.objects.create(
            title='Test Article',
            content='Test content',
            published=True
        )

    def test_serialize_article(self):
        """Should serialize article to dict."""
        serializer = ArticleSerializer(self.article)

        self.assertIsInstance(serializer.data, dict)
        self.assertEqual(serializer.data['title'], 'Test Article')
        self.assertEqual(serializer.data['content'], 'Test content')
        self.assertEqual(serializer.data['published'], True)

    def test_serialize_article_subset_fields(self):
        """Should serialize only specified fields."""
        serializer = ArticleSerializer(
            self.article,
            fields=['title', 'published']
        )

        self.assertIn('title', serializer.data)
        self.assertIn('published', serializer.data)
        self.assertNotIn('content', serializer.data)
```

### Serializing Multiple Objects

```python
class MultipleObjectSerializationTest(TestCase):
    def setUp(self):
        Article.objects.create(title='Article 1', content='Content 1')
        Article.objects.create(title='Article 2', content='Content 2')
        Article.objects.create(title='Article 3', content='Content 3')

    def test_serialize_queryset(self):
        """Should serialize multiple objects."""
        articles = Article.objects.all()
        serializer = ArticleSerializer(articles, many=True)

        self.assertIsInstance(serializer.data, list)
        self.assertEqual(len(serializer.data), 3)
        self.assertEqual(serializer.data[0]['title'], 'Article 1')
```

### Read-Only and Write-Only Fields

```python
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    full_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'full_name']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"


class ReadWriteFieldsTest(TestCase):
    def test_write_only_field_in_input(self):
        """Write-only field should accept input."""
        data = {
            'username': 'testuser',
            'password': 'securepass123'
        }
        serializer = UserSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertIn('password', serializer.validated_data)

    def test_write_only_field_not_in_output(self):
        """Write-only field should not appear in serialized data."""
        user = User.objects.create_user(
            username='testuser',
            password='securepass123',
            first_name='Test',
            last_name='User'
        )
        serializer = UserSerializer(user)

        self.assertNotIn('password', serializer.data)
        self.assertIn('full_name', serializer.data)

    def test_read_only_field_ignored_in_input(self):
        """Read-only field should be ignored in input."""
        data = {
            'username': 'testuser',
            'password': 'pass',
            'full_name': 'Ignored Value'
        }
        serializer = UserSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertNotIn('full_name', serializer.validated_data)
```

## Testing Deserialization

### Creating Objects

```python
class ArticleDeserializationTest(TestCase):
    def test_create_from_validated_data(self):
        """Should create object from validated data."""
        data = {
            'title': 'New Article',
            'content': 'New content'
        }
        serializer = ArticleSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        article = serializer.save()

        self.assertIsInstance(article, Article)
        self.assertEqual(article.title, 'New Article')
        self.assertEqual(Article.objects.count(), 1)
```

### Updating Objects

```python
class ArticleUpdateTest(TestCase):
    def setUp(self):
        self.article = Article.objects.create(
            title='Original',
            content='Original content'
        )

    def test_update_article(self):
        """Should update existing article."""
        data = {
            'title': 'Updated',
            'content': 'Updated content'
        }
        serializer = ArticleSerializer(self.article, data=data)

        self.assertTrue(serializer.is_valid())
        article = serializer.save()

        self.assertEqual(article.id, self.article.id)
        self.assertEqual(article.title, 'Updated')
        self.assertEqual(Article.objects.count(), 1)

    def test_partial_update(self):
        """Should partially update article."""
        data = {'title': 'Partially Updated'}
        serializer = ArticleSerializer(
            self.article,
            data=data,
            partial=True
        )

        self.assertTrue(serializer.is_valid())
        article = serializer.save()

        self.assertEqual(article.title, 'Partially Updated')
        self.assertEqual(article.content, 'Original content')
```

## Testing Nested Serializers

### Basic Nested Serializer

```python
class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class ArticleSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)

    class Meta:
        model = Article
        fields = ['id', 'title', 'content', 'author']


class NestedSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        self.article = Article.objects.create(
            title='Test',
            content='Content',
            author=self.user
        )

    def test_nested_serialization(self):
        """Should include nested author data."""
        serializer = ArticleSerializer(self.article)

        self.assertIn('author', serializer.data)
        self.assertEqual(serializer.data['author']['username'], 'testuser')
        self.assertEqual(serializer.data['author']['email'], 'test@example.com')

    def test_nested_serialization_list(self):
        """Should serialize nested data in lists."""
        articles = Article.objects.all()
        serializer = ArticleSerializer(articles, many=True)

        self.assertEqual(len(serializer.data), 1)
        self.assertIn('author', serializer.data[0])
```

### Writable Nested Serializer

```python
class ArticleWithAuthorSerializer(serializers.ModelSerializer):
    author = AuthorSerializer()

    class Meta:
        model = Article
        fields = ['title', 'content', 'author']

    def create(self, validated_data):
        author_data = validated_data.pop('author')
        author = User.objects.create(**author_data)
        article = Article.objects.create(author=author, **validated_data)
        return article


class WritableNestedSerializerTest(TestCase):
    def test_create_with_nested_data(self):
        """Should create article with nested author."""
        data = {
            'title': 'Test Article',
            'content': 'Content',
            'author': {
                'username': 'newuser',
                'email': 'new@example.com'
            }
        }
        serializer = ArticleWithAuthorSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        article = serializer.save()

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(article.author.username, 'newuser')
```

### Many-to-Many Relationships

```python
class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']


class ArticleSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Article
        fields = ['title', 'content', 'tags']


class ManyToManySerializerTest(TestCase):
    def setUp(self):
        self.tag1 = Tag.objects.create(name='Django')
        self.tag2 = Tag.objects.create(name='Python')
        self.article = Article.objects.create(
            title='Test',
            content='Content'
        )
        self.article.tags.set([self.tag1, self.tag2])

    def test_serialize_many_to_many(self):
        """Should serialize many-to-many relationships."""
        serializer = ArticleSerializer(self.article)

        self.assertEqual(len(serializer.data['tags']), 2)
        tag_names = [tag['name'] for tag in serializer.data['tags']]
        self.assertIn('Django', tag_names)
        self.assertIn('Python', tag_names)
```

## Testing Custom Fields

### Custom Field Implementation

```python
from rest_framework import serializers


class ColorField(serializers.Field):
    """Custom field for color hex values."""

    def to_representation(self, value):
        """Convert internal value to hex color."""
        return f"#{value}"

    def to_internal_value(self, data):
        """Convert hex color to internal format."""
        if not isinstance(data, str):
            raise serializers.ValidationError("Must be a string")

        if not data.startswith('#'):
            raise serializers.ValidationError("Must start with #")

        if len(data) != 7:
            raise serializers.ValidationError("Must be 7 characters")

        return data[1:]  # Remove # prefix


class ProductSerializer(serializers.Serializer):
    name = serializers.CharField()
    color = ColorField()


class CustomFieldTest(TestCase):
    def test_custom_field_serialization(self):
        """Should serialize color with # prefix."""
        product = Product(name='Widget', color='FF0000')
        serializer = ProductSerializer(product)

        self.assertEqual(serializer.data['color'], '#FF0000')

    def test_custom_field_deserialization(self):
        """Should deserialize hex color."""
        data = {'name': 'Widget', 'color': '#00FF00'}
        serializer = ProductSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['color'], '00FF00')

    def test_custom_field_validation(self):
        """Should validate hex color format."""
        data = {'name': 'Widget', 'color': 'red'}
        serializer = ProductSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn('color', serializer.errors)
```

## Testing Custom Validation

### Custom Validators

```python
def validate_positive(value):
    """Validator for positive numbers."""
    if value <= 0:
        raise serializers.ValidationError("Must be positive")


class ProductSerializer(serializers.Serializer):
    name = serializers.CharField()
    price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[validate_positive]
    )


class CustomValidatorTest(TestCase):
    def test_positive_price(self):
        """Should accept positive price."""
        data = {'name': 'Widget', 'price': '9.99'}
        serializer = ProductSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test_negative_price(self):
        """Should reject negative price."""
        data = {'name': 'Widget', 'price': '-5.00'}
        serializer = ProductSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn('price', serializer.errors)

    def test_zero_price(self):
        """Should reject zero price."""
        data = {'name': 'Widget', 'price': '0.00'}
        serializer = ProductSerializer(data=data)

        self.assertFalse(serializer.is_valid())
```

### Conditional Validation

```python
class DiscountSerializer(serializers.Serializer):
    discount_type = serializers.ChoiceField(choices=['percentage', 'fixed'])
    discount_value = serializers.DecimalField(max_digits=10, decimal_places=2)

    def validate(self, data):
        """Validate discount based on type."""
        if data['discount_type'] == 'percentage':
            if data['discount_value'] > 100:
                raise serializers.ValidationError(
                    "Percentage discount cannot exceed 100"
                )
        return data


class ConditionalValidationTest(TestCase):
    def test_valid_percentage_discount(self):
        """Should accept valid percentage."""
        data = {'discount_type': 'percentage', 'discount_value': '25.00'}
        serializer = DiscountSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test_invalid_percentage_discount(self):
        """Should reject percentage over 100."""
        data = {'discount_type': 'percentage', 'discount_value': '150.00'}
        serializer = DiscountSerializer(data=data)

        self.assertFalse(serializer.is_valid())

    def test_fixed_discount_over_100(self):
        """Should accept fixed discount over 100."""
        data = {'discount_type': 'fixed', 'discount_value': '150.00'}
        serializer = DiscountSerializer(data=data)

        self.assertTrue(serializer.is_valid())
```

## Testing SerializerMethodField

### Basic SerializerMethodField

```python
class ArticleSerializer(serializers.ModelSerializer):
    word_count = serializers.SerializerMethodField()
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = ['title', 'content', 'word_count', 'author_name']

    def get_word_count(self, obj):
        return len(obj.content.split())

    def get_author_name(self, obj):
        return obj.author.get_full_name()


class SerializerMethodFieldTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            first_name='Test',
            last_name='User'
        )
        self.article = Article.objects.create(
            title='Test',
            content='This is a test article',
            author=self.user
        )

    def test_method_field_calculation(self):
        """Should calculate word count correctly."""
        serializer = ArticleSerializer(self.article)

        self.assertEqual(serializer.data['word_count'], 5)

    def test_method_field_with_relation(self):
        """Should access related object data."""
        serializer = ArticleSerializer(self.article)

        self.assertEqual(serializer.data['author_name'], 'Test User')
```

## Testing Model Serializers

### Auto-Generated Fields

```python
class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = '__all__'


class ModelSerializerTest(TestCase):
    def test_all_fields_included(self):
        """Should include all model fields."""
        serializer = ArticleSerializer()

        expected_fields = ['id', 'title', 'content', 'created', 'modified']
        for field in expected_fields:
            self.assertIn(field, serializer.fields)

    def test_read_only_fields(self):
        """Should mark appropriate fields as read-only."""
        serializer = ArticleSerializer()

        self.assertTrue(serializer.fields['created'].read_only)
        self.assertTrue(serializer.fields['modified'].read_only)
```

### Extra Kwargs

```python
class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ['title', 'content', 'published']
        extra_kwargs = {
            'content': {'write_only': True},
            'published': {'default': False}
        }


class ExtraKwargsTest(TestCase):
    def test_write_only_field(self):
        """Content should be write-only."""
        article = Article.objects.create(
            title='Test',
            content='Secret content'
        )
        serializer = ArticleSerializer(article)

        self.assertNotIn('content', serializer.data)

    def test_default_value(self):
        """Published should default to False."""
        data = {'title': 'Test', 'content': 'Content'}
        serializer = ArticleSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['published'], False)
```

## Best Practices

1. **Test both validation and serialization** - Ensure data flows correctly in both directions
2. **Test edge cases** - Empty strings, None values, boundary conditions
3. **Test error messages** - Verify users get helpful validation errors
4. **Use is_valid(raise_exception=True) in views** - But test with is_valid() in tests
5. **Test with and without partial=True** - Ensure update logic works correctly
6. **Test nested serializers separately** - Isolate complexity
7. **Test custom validators independently** - Unit test validation logic
8. **Mock external dependencies** - Don't call external APIs in serializer tests

## See Also

- [Testing Views](./testing-views.md) - Testing views that use serializers
- [Test Clients Reference](./test-clients.md) - Testing with API clients
- [Test Pattern Examples](./examples/test-patterns.py) - Working code examples
