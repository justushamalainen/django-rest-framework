# Validation Reference

DRF provides three levels of validation: field-level, object-level, and validators. Understanding all three is essential for robust APIs.

## Validation Flow

When you call `serializer.is_valid()`, validation happens in this order:

```
1. Field-level validation
   └─> to_internal_value() for each field
       └─> run_validators() for each field
           └─> validate_<field_name>() for each field

2. Object-level validation
   └─> validate() method

3. Unique validators
   └─> UniqueValidator
   └─> UniqueTogetherValidator
   └─> UniqueForDateValidator, etc.

If any step raises ValidationError, validation stops and errors are returned.
```

## Field-Level Validation

Validation that applies to a single field.

### Built-in Field Validation

Every field type has built-in validation:

```python
class BookSerializer(serializers.Serializer):
    # CharField validates type and length
    title = serializers.CharField(
        max_length=200,      # MaxLengthValidator added automatically
        min_length=1,        # MinLengthValidator added automatically
        allow_blank=False,   # Rejects empty strings
    )

    # IntegerField validates type and range
    pages = serializers.IntegerField(
        min_value=1,         # MinValueValidator added automatically
        max_value=10000,     # MaxValueValidator added automatically
    )

    # EmailField validates email format
    contact_email = serializers.EmailField()  # EmailValidator added

    # DecimalField validates precision
    price = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=0
    )

# These validations happen in field.to_internal_value()
```

### Custom Field Validators

Add validators to individual fields:

```python
from django.core.validators import RegexValidator

class BookSerializer(serializers.Serializer):
    # Single validator
    isbn = serializers.CharField(
        validators=[
            RegexValidator(
                regex=r'^\d{13}$',
                message='ISBN must be exactly 13 digits'
            )
        ]
    )

    # Multiple validators
    title = serializers.CharField(
        max_length=200,
        validators=[
            lambda value: value if 'spam' not in value.lower()
            else (_ for _ in ()).throw(
                serializers.ValidationError('Title contains spam')
            ),
        ]
    )

# Validator functions
def validate_positive(value):
    """Simple validator function"""
    if value <= 0:
        raise serializers.ValidationError("Must be positive")

def validate_even(value):
    """Another validator function"""
    if value % 2 != 0:
        raise serializers.ValidationError("Must be even")

class NumberSerializer(serializers.Serializer):
    number = serializers.IntegerField(
        validators=[validate_positive, validate_even]
    )

# Validators run in order after to_internal_value()
```

### validate_<field_name>() Method

Define a `validate_<field_name>()` method for field-specific validation:

```python
class BookSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    pages = serializers.IntegerField()
    published_year = serializers.IntegerField()

    def validate_title(self, value):
        """
        Validate title field.
        Called after field.to_internal_value() and field.run_validators()
        MUST return the value (or a transformed value)
        """
        # Check for forbidden words
        forbidden_words = ['spam', 'xxx', 'offensive']
        if any(word in value.lower() for word in forbidden_words):
            raise serializers.ValidationError(
                "Title contains inappropriate content"
            )

        # Can transform the value
        return value.title()  # Title case

    def validate_pages(self, value):
        """Validate pages field"""
        if value <= 0:
            raise serializers.ValidationError("Pages must be positive")
        if value > 10000:
            raise serializers.ValidationError("Too many pages")
        return value

    def validate_published_year(self, value):
        """Validate year field"""
        from datetime import date
        current_year = date.today().year

        if value < 1000:
            raise serializers.ValidationError("Year too old")
        if value > current_year + 1:
            raise serializers.ValidationError(
                "Cannot be published more than 1 year in the future"
            )
        return value

# Usage
serializer = BookSerializer(data={
    'title': 'django book',
    'pages': -5,
    'published_year': 3000
})
serializer.is_valid()
# False

serializer.errors
# {
#     'title': [...],  # Transformed by validate_title
#     'pages': ['Pages must be positive'],
#     'published_year': ['Cannot be published more than 1 year in the future']
# }
```

**Important Rules:**
- Method name MUST be `validate_<field_name>`
- MUST return the value (or modified value)
- Runs AFTER to_internal_value() and field validators
- Can access `self.context` for request data
- Can't access other fields (use object-level validation for that)

### Field Validation with Context

Access the serializer context in validators:

```python
def validate_username_available(value):
    """Context-aware validator"""
    # Can't access context here! Use validate_<field>() method instead

class UserSerializer(serializers.Serializer):
    username = serializers.CharField()

    def validate_username(self, value):
        """Can access context here"""
        request = self.context.get('request')

        # Different validation for different users
        if request and request.user.is_staff:
            # Staff can use any username
            return value

        # Check if username is taken
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already taken")

        return value

# Usage (pass context)
serializer = UserSerializer(
    data={'username': 'john'},
    context={'request': request}
)
```

## Object-Level Validation

Validation that involves multiple fields or business logic.

### validate() Method

Override the `validate()` method for cross-field validation:

```python
class EventSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    max_attendees = serializers.IntegerField()
    min_attendees = serializers.IntegerField()

    def validate(self, attrs):
        """
        Validate the entire object.
        Called after all field-level validation.
        MUST return attrs (or modified attrs)

        attrs is a dict of field_name: validated_value
        """
        # Cross-field validation
        if attrs['end_date'] < attrs['start_date']:
            raise serializers.ValidationError(
                "End date must be after start date"
            )

        if attrs['max_attendees'] < attrs['min_attendees']:
            raise serializers.ValidationError({
                'max_attendees': 'Max must be >= min',
                'min_attendees': 'Min must be <= max',
            })

        # Business logic validation
        if attrs['max_attendees'] > 1000:
            if (attrs['end_date'] - attrs['start_date']).days < 7:
                raise serializers.ValidationError(
                    "Events with >1000 attendees must be at least 7 days"
                )

        # Can add computed fields
        attrs['duration_days'] = (
            attrs['end_date'] - attrs['start_date']
        ).days

        return attrs

# Non-field errors (apply to whole object)
serializer = EventSerializer(data={...})
serializer.is_valid()
serializer.errors
# {
#     'non_field_errors': ['End date must be after start date']
# }

# Field-specific errors from validate()
# {
#     'max_attendees': ['Max must be >= min'],
#     'min_attendees': ['Min must be <= max']
# }
```

**Important Rules:**
- Method MUST be named `validate`
- MUST return attrs (or modified attrs)
- Runs AFTER all field-level validation
- Receives validated data for ALL fields
- Can raise ValidationError with string (non-field error) or dict (field errors)
- Can add/modify fields in attrs

### Accessing Instance in validate()

For updates, you can access the instance being updated:

```python
class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['title', 'status', 'published_date']

    def validate(self, attrs):
        """Validation that depends on current state"""

        # self.instance is None for creation, Book object for updates
        if self.instance is not None:
            # This is an update
            old_status = self.instance.status
            new_status = attrs.get('status', old_status)

            # Don't allow changing from published back to draft
            if old_status == 'published' and new_status == 'draft':
                raise serializers.ValidationError(
                    "Cannot change published book back to draft"
                )

        # For creation (instance is None)
        else:
            # Books must start as draft
            if attrs.get('status') == 'published':
                if not attrs.get('published_date'):
                    raise serializers.ValidationError(
                        "Published books must have published_date"
                    )

        return attrs
```

### Raising Different Error Types

```python
def validate(self, attrs):
    # Non-field error (affects whole object)
    if some_condition:
        raise serializers.ValidationError("General error message")

    # Field-specific errors
    if other_condition:
        raise serializers.ValidationError({
            'field1': 'Error for field1',
            'field2': ['Error 1 for field2', 'Error 2 for field2'],
        })

    # Mix non-field and field errors
    raise serializers.ValidationError({
        'field1': 'Field error',
        'non_field_errors': 'Object error'
    })

    return attrs
```

## Built-in Validators

DRF provides reusable validator classes.

### UniqueValidator

Ensures a field value is unique in the database.

```python
from rest_framework.validators import UniqueValidator

class UserSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=100,
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                message='Username already exists',
                lookup='iexact'  # Case-insensitive lookup (default: 'exact')
            )
        ]
    )

# ModelSerializer adds this automatically for unique fields!
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User  # username is unique on model
        fields = ['username']
    # UniqueValidator is automatically added to username field
```

**Parameters:**
- `queryset` - QuerySet to check uniqueness against
- `message` - Custom error message
- `lookup` - Lookup type ('exact', 'iexact', etc.)

### UniqueTogetherValidator

Ensures combination of fields is unique (for `unique_together`).

```python
from rest_framework.validators import UniqueTogetherValidator

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['title', 'author', 'isbn']
        validators = [
            UniqueTogetherValidator(
                queryset=Book.objects.all(),
                fields=['title', 'author'],
                message='This author already has a book with this title'
            )
        ]

# ModelSerializer adds this automatically for unique_together!
class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)

    class Meta:
        unique_together = [['title', 'author']]

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = '__all__'
    # UniqueTogetherValidator automatically added!
```

**Parameters:**
- `queryset` - QuerySet to check against
- `fields` - Tuple/list of field names
- `message` - Custom error message

### UniqueForDateValidator, UniqueForMonthValidator, UniqueForYearValidator

Ensures field is unique for a date/month/year.

```python
from rest_framework.validators import (
    UniqueForDateValidator,
    UniqueForMonthValidator,
    UniqueForYearValidator
)

class ArticleSerializer(serializers.Serializer):
    title = serializers.CharField()
    published_date = serializers.DateField()

    class Meta:
        validators = [
            # Only one article with this title per day
            UniqueForDateValidator(
                queryset=Article.objects.all(),
                field='title',
                date_field='published_date',
                message='Title must be unique per day'
            ),

            # Only one article with this title per month
            UniqueForMonthValidator(
                queryset=Article.objects.all(),
                field='title',
                date_field='published_date'
            ),

            # Only one article with this title per year
            UniqueForYearValidator(
                queryset=Article.objects.all(),
                field='title',
                date_field='published_date'
            )
        ]

# ModelSerializer adds automatically for unique_for_date, etc.
class Article(models.Model):
    title = models.CharField(
        max_length=200,
        unique_for_date='published_date'
    )
    published_date = models.DateField()
```

### Custom Validators

Create reusable validator classes:

```python
class MultipleOfValidator:
    """Validator that checks if value is multiple of a number"""

    message = 'Value must be a multiple of {multiple}'
    code = 'invalid_multiple'

    def __init__(self, multiple, message=None):
        self.multiple = multiple
        if message:
            self.message = message

    def __call__(self, value):
        """Validator is callable"""
        if value % self.multiple != 0:
            raise serializers.ValidationError(
                self.message.format(multiple=self.multiple),
                code=self.code
            )

class QuantitySerializer(serializers.Serializer):
    quantity = serializers.IntegerField(
        validators=[MultipleOfValidator(5)]
    )
    # Quantity must be multiple of 5

# Context-aware validators
class CurrentUserOwnedValidator:
    """Validate that object is owned by current user"""

    requires_context = True  # Request context in __call__

    def __call__(self, value, serializer_field):
        """Receives both value and field"""
        request = serializer_field.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required")

        if value.owner != request.user:
            raise serializers.ValidationError("Not your object")

class ResourceSerializer(serializers.Serializer):
    resource_id = serializers.PrimaryKeyRelatedField(
        queryset=Resource.objects.all(),
        validators=[CurrentUserOwnedValidator()]
    )
```

## Validation Errors

### Error Format

```python
serializer = BookSerializer(data={...})
if not serializer.is_valid():
    # Access errors
    errors = serializer.errors

    # Format:
    # {
    #     'field_name': ['Error message 1', 'Error message 2'],
    #     'another_field': ['Error message'],
    #     'non_field_errors': ['General error']
    # }

    # Check specific field
    if 'title' in errors:
        print(errors['title'])  # List of errors for title

    # Check for non-field errors
    if 'non_field_errors' in errors:
        print(errors['non_field_errors'])
```

### Custom Error Messages

```python
class BookSerializer(serializers.Serializer):
    # Per-field custom messages
    title = serializers.CharField(
        max_length=200,
        error_messages={
            'required': 'Title is required!',
            'max_length': 'Title too long (max {max_length} chars)',
            'blank': 'Title cannot be blank',
        }
    )

    pages = serializers.IntegerField(
        error_messages={
            'invalid': 'Pages must be a number',
            'max_value': 'Too many pages (max {max_value})',
            'min_value': 'Too few pages (min {min_value})',
        }
    )

# Default error keys by field type:
# CharField: required, blank, max_length, min_length
# IntegerField: required, invalid, max_value, min_value
# EmailField: required, invalid
# etc.
```

### Error Detail Objects

```python
from rest_framework.exceptions import ErrorDetail

# Errors are actually ErrorDetail objects, not strings
serializer = BookSerializer(data={'pages': 'abc'})
serializer.is_valid()

error = serializer.errors['pages'][0]
# ErrorDetail(string='A valid integer is required.', code='invalid')

str(error)        # 'A valid integer is required.'
error.code        # 'invalid'
```

## Validation Best Practices

### 1. Use Field Validators for Simple Rules

```python
# Good: Simple field validation
pages = serializers.IntegerField(min_value=1, max_value=10000)

# Bad: Overkill
pages = serializers.IntegerField()

def validate_pages(self, value):
    if value < 1 or value > 10000:
        raise serializers.ValidationError("Invalid pages")
    return value
```

### 2. Use validate_<field>() for Field-Specific Logic

```python
# Good: Field-specific business logic
def validate_username(self, value):
    if User.objects.filter(username=value).exists():
        raise serializers.ValidationError("Username taken")
    return value

# Bad: Should be in validate() since it involves multiple fields
def validate_start_date(self, value):
    # Checking against end_date - should be in validate()!
    if value > self.initial_data.get('end_date'):
        raise serializers.ValidationError("Start after end")
    return value
```

### 3. Use validate() for Cross-Field Logic

```python
# Good: Cross-field validation
def validate(self, attrs):
    if attrs['end_date'] < attrs['start_date']:
        raise serializers.ValidationError("End before start")
    return attrs

# Bad: Accessing initial_data in field validator
def validate_end_date(self, value):
    if value < self.initial_data.get('start_date'):
        raise serializers.ValidationError("End before start")
    return value
```

### 4. Always Return Values

```python
# Good: Returns value
def validate_title(self, value):
    if 'spam' in value.lower():
        raise serializers.ValidationError("Spam detected")
    return value.title()  # Transform and return

# Bad: Doesn't return - value becomes None!
def validate_title(self, value):
    if 'spam' in value.lower():
        raise serializers.ValidationError("Spam detected")
    # Missing return!
```

### 5. Provide Clear Error Messages

```python
# Good: Clear, actionable message
raise serializers.ValidationError(
    "Password must be at least 8 characters and include a number"
)

# Bad: Vague message
raise serializers.ValidationError("Invalid password")
```

### 6. Use Validation for Business Logic, Not Data Transform

```python
# Good: Validate, don't transform
def validate_email(self, value):
    # Validation
    if not value.endswith('@company.com'):
        raise serializers.ValidationError("Must be company email")
    return value

# Questionable: Heavy transformation in validator
def validate_title(self, value):
    # This is transformation, not validation - consider doing in save()
    value = value.strip().title()
    value = re.sub(r'\s+', ' ', value)
    value = value[:200]
    return value
```

## Testing Validation

```python
import pytest
from rest_framework.exceptions import ValidationError

class TestBookSerializer:
    def test_valid_data(self):
        """Test with valid data"""
        serializer = BookSerializer(data={
            'title': 'Valid Book',
            'pages': 200,
        })
        assert serializer.is_valid()
        assert serializer.validated_data['title'] == 'Valid Book'

    def test_invalid_pages(self):
        """Test pages validation"""
        serializer = BookSerializer(data={
            'title': 'Book',
            'pages': -5,
        })
        assert not serializer.is_valid()
        assert 'pages' in serializer.errors

    def test_cross_field_validation(self):
        """Test object-level validation"""
        serializer = EventSerializer(data={
            'start_date': '2024-12-31',
            'end_date': '2024-01-01',  # Before start!
        })
        assert not serializer.is_valid()
        assert 'non_field_errors' in serializer.errors
```
