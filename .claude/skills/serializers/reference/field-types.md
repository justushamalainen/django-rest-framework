# Field Types Reference

DRF provides 40+ built-in field types covering all common data types. This reference covers every field with parameters, validation, and examples.

## Field Type Categories

- **Boolean:** BooleanField
- **String:** CharField, EmailField, RegexField, SlugField, URLField
- **Numeric:** IntegerField, BigIntegerField, FloatField, DecimalField
- **Date/Time:** DateTimeField, DateField, TimeField, DurationField
- **Choice:** ChoiceField, MultipleChoiceField, FilePathField
- **File:** FileField, ImageField
- **Composite:** ListField, DictField, HStoreField, JSONField
- **Specialized:** UUIDField, IPAddressField, SerializerMethodField, ReadOnlyField, HiddenField, ModelField

## Common Parameters

All fields accept these parameters:

```python
field = SomeField(
    # Validation
    required=True,              # Default: True (False if default is set)
    allow_null=False,           # Allow None values (default: False)
    default=empty,              # Default value if not provided
    validators=[],              # List of validator functions

    # Access control
    read_only=False,            # Only in output, never in input
    write_only=False,           # Only in input, never in output

    # Metadata
    label='Field Label',        # Human-readable label
    help_text='Help text',      # Description
    initial=None,               # Initial value for HTML forms
    error_messages={},          # Custom error messages
    source=None,                # Source attribute name (default: field name)
    style={},                   # Rendering hints for browsable API
)
```

**Key Rules:**
- `read_only=True` implies `required=False`
- `default` implies `required=False`
- `read_only` and `write_only` cannot both be True
- `read_only` and `required` cannot both be True

## Boolean Fields

### BooleanField

Represents `True`, `False`, and optionally `None`.

**True values:** `True, 'true', 'True', 'TRUE', 't', 'T', '1', 1, 'yes', 'y', 'on'`
**False values:** `False, 'false', 'False', 'FALSE', 'f', 'F', '0', 0, 0.0, 'no', 'n', 'off'`

```python
class BookSerializer(serializers.Serializer):
    is_available = serializers.BooleanField(default=True)
    is_featured = serializers.BooleanField(required=False)
    is_published = serializers.BooleanField(allow_null=True)  # True/False/None

# Examples
BooleanField().to_internal_value('true')    # True
BooleanField().to_internal_value('yes')     # True
BooleanField().to_internal_value(1)         # True
BooleanField().to_internal_value('false')   # False
BooleanField().to_internal_value(0)         # False
BooleanField(allow_null=True).to_internal_value(None)  # None
```

**Parameters:**
- All common parameters
- Note: `allow_null=True` enables three-state boolean

## String Fields

### CharField

Basic string field with length validation.

```python
class BookSerializer(serializers.Serializer):
    title = serializers.CharField(
        max_length=200,          # Maximum length (adds MaxLengthValidator)
        min_length=1,            # Minimum length (adds MinLengthValidator)
        allow_blank=False,       # Allow empty strings (default: False)
        trim_whitespace=True,    # Strip leading/trailing whitespace (default: True)
    )

    # Common patterns
    name = serializers.CharField(max_length=100, required=True)
    notes = serializers.CharField(allow_blank=True, required=False)
    code = serializers.CharField(min_length=3, max_length=10)
```

**Validation errors:**
- `blank`: "This field may not be blank."
- `max_length`: "Ensure this field has no more than {max_length} characters."
- `min_length`: "Ensure this field has at least {min_length} characters."

### EmailField

CharField with email validation.

```python
email = serializers.EmailField(
    max_length=254,  # Standard email max length
)

# Examples
EmailField().to_internal_value('user@example.com')  # Valid
EmailField().to_internal_value('invalid')           # ValidationError
```

### RegexField

CharField that must match a regex pattern.

```python
class ProductSerializer(serializers.Serializer):
    sku = serializers.RegexField(
        regex=r'^[A-Z]{3}-\d{4}$',  # Pattern like 'ABC-1234'
    )

    # With custom error message
    postal_code = serializers.RegexField(
        regex=r'^\d{5}(-\d{4})?$',
        error_messages={
            'invalid': 'Enter a valid postal code (12345 or 12345-6789)'
        }
    )
```

### SlugField

String containing only letters, numbers, underscores, or hyphens.

```python
class ArticleSerializer(serializers.Serializer):
    slug = serializers.SlugField(
        max_length=100,
        allow_unicode=False,  # ASCII only (default)
    )

    # Unicode slugs (for internationalization)
    unicode_slug = serializers.SlugField(allow_unicode=True)

# Valid: 'my-article', 'article_2', 'article-123'
# Invalid: 'my article', 'article!', 'article@home'
```

### URLField

CharField with URL validation.

```python
website = serializers.URLField(
    max_length=200,
)

# Examples
URLField().to_internal_value('https://example.com')      # Valid
URLField().to_internal_value('http://example.com/path')  # Valid
URLField().to_internal_value('not a url')                # ValidationError
```

## Numeric Fields

### IntegerField

Integer number with optional min/max validation.

```python
class BookSerializer(serializers.Serializer):
    pages = serializers.IntegerField(
        min_value=1,           # Minimum value (adds MinValueValidator)
        max_value=10000,       # Maximum value (adds MaxValueValidator)
    )

    year = serializers.IntegerField(min_value=1000, max_value=9999)
    quantity = serializers.IntegerField(min_value=0, default=0)

# Examples
IntegerField().to_internal_value(42)        # 42
IntegerField().to_internal_value('42')      # 42
IntegerField().to_internal_value('42.0')    # 42 (decimal part ignored if .0)
IntegerField().to_internal_value('42.5')    # ValidationError
```

### BigIntegerField

Like IntegerField but for larger numbers. Can coerce to string for JavaScript compatibility.

```python
class DataSerializer(serializers.Serializer):
    big_number = serializers.BigIntegerField(
        coerce_to_string=None,  # None = use setting (default)
        # True = return as string (for JavaScript safe integers)
        # False = return as int
    )

# When COERCE_BIGINT_TO_STRING = True (default for BigInt):
BigIntegerField().to_representation(9007199254740992)  # '9007199254740992'

# When coerce_to_string=False:
BigIntegerField(coerce_to_string=False).to_representation(123)  # 123
```

### FloatField

Floating-point number.

```python
class MeasurementSerializer(serializers.Serializer):
    temperature = serializers.FloatField(
        min_value=-273.15,    # Absolute zero
        max_value=1000.0,
    )

    percentage = serializers.FloatField(min_value=0.0, max_value=100.0)

# Examples
FloatField().to_internal_value(3.14)      # 3.14
FloatField().to_internal_value('3.14')    # 3.14
FloatField().to_internal_value('3')       # 3.0
```

### DecimalField

Precise decimal numbers (use for money/financial data).

```python
class ProductSerializer(serializers.Serializer):
    price = serializers.DecimalField(
        max_digits=8,          # Total digits (required)
        decimal_places=2,      # Digits after decimal point (required)
        coerce_to_string=None, # None = use setting, True = string output
        max_value=None,        # Optional max value
        min_value=None,        # Optional min value
        localize=False,        # Use locale-specific formatting
        rounding=None,         # Rounding mode (decimal.ROUND_*)
        normalize_output=False, # Remove trailing zeros
    )

    # Common pattern for money
    price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)

    # With rounding
    import decimal
    tax_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=4,
        rounding=decimal.ROUND_HALF_UP
    )

# Examples
field = DecimalField(max_digits=5, decimal_places=2)
field.to_internal_value('123.45')    # Decimal('123.45')
field.to_internal_value(123.45)      # Decimal('123.45')
field.to_internal_value('123.456')   # Decimal('123.46') - rounded
```

**Important:** Always use DecimalField for money, never FloatField!

## Date/Time Fields

### DateTimeField

Date and time with timezone support.

```python
class EventSerializer(serializers.Serializer):
    created_at = serializers.DateTimeField(
        format=None,           # Output format (None = ISO-8601)
        input_formats=None,    # Input formats (None = use settings)
        default_timezone=None, # Timezone for naive datetimes
    )

    # Common patterns
    created_at = serializers.DateTimeField(read_only=True)
    scheduled_at = serializers.DateTimeField(required=True)

    # Custom format
    formatted_date = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S')

    # ISO-8601 (default)
    iso_date = serializers.DateTimeField(format='iso-8601')

# Examples
DateTimeField().to_internal_value('2024-01-15T10:30:00Z')  # datetime with UTC
DateTimeField().to_internal_value('2024-01-15 10:30:00')   # datetime (naive or aware based on USE_TZ)
```

**Output formats:**
- `None` or `'iso-8601'`: ISO-8601 format (default)
- `'%Y-%m-%d %H:%M:%S'`: Custom strftime format

### DateField

Date without time.

```python
class PersonSerializer(serializers.Serializer):
    birth_date = serializers.DateField(
        format=None,           # Output format (None = ISO-8601)
        input_formats=None,    # Input formats
    )

    # Common patterns
    birth_date = serializers.DateField()
    formatted_date = serializers.DateField(format='%m/%d/%Y')

# Examples
DateField().to_internal_value('2024-01-15')    # date(2024, 1, 15)
DateField().to_internal_value('01/15/2024')    # ValidationError (wrong format)
```

### TimeField

Time without date.

```python
opening_time = serializers.TimeField(
    format=None,           # Output format
    input_formats=None,    # Input formats
)

# Examples
TimeField().to_internal_value('14:30:00')      # time(14, 30, 0)
TimeField().to_internal_value('14:30')         # time(14, 30)
```

### DurationField

Time duration (timedelta).

```python
class TaskSerializer(serializers.Serializer):
    duration = serializers.DurationField(
        format=None,           # 'iso-8601', 'django', or None
        max_value=None,        # Maximum duration
        min_value=None,        # Minimum duration
    )

# Examples - accepts various formats
DurationField().to_internal_value('1 12:00:00')    # 1 day, 12 hours
DurationField().to_internal_value('12:00:00')      # 12 hours
DurationField().to_internal_value('P1DT12H')       # ISO-8601: 1 day, 12 hours

# Output
from datetime import timedelta
DurationField().to_representation(timedelta(days=1, hours=12))  # '1 12:00:00'
```

## Choice Fields

### ChoiceField

Field that must be one of a limited set of values.

```python
class BookSerializer(serializers.Serializer):
    # List of choices
    status = serializers.ChoiceField(
        choices=['draft', 'published', 'archived'],
        allow_blank=False,
    )

    # Tuple choices (value, display)
    genre = serializers.ChoiceField(
        choices=[
            ('fiction', 'Fiction'),
            ('nonfiction', 'Non-Fiction'),
            ('scifi', 'Science Fiction'),
        ]
    )

    # Grouped choices
    category = serializers.ChoiceField(
        choices=[
            ('Fiction', [
                ('mystery', 'Mystery'),
                ('thriller', 'Thriller'),
            ]),
            ('Non-Fiction', [
                ('history', 'History'),
                ('biography', 'Biography'),
            ]),
        ]
    )

    # With HTML cutoff (for large choice lists)
    country = serializers.ChoiceField(
        choices=list_of_countries,
        html_cutoff=100,  # Only show first 100 in HTML forms
    )

# Django model choices
class Book(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

class BookSerializer(serializers.ModelSerializer):
    # Automatically becomes ChoiceField with model choices
    class Meta:
        model = Book
        fields = ['status']
```

### MultipleChoiceField

Select multiple values from choices.

```python
class BookSerializer(serializers.Serializer):
    genres = serializers.MultipleChoiceField(
        choices=['fiction', 'nonfiction', 'scifi', 'mystery'],
        allow_empty=True,  # Allow empty list (default: True)
    )

# Examples - input/output is a set or list
field = MultipleChoiceField(choices=['a', 'b', 'c'])
field.to_internal_value(['a', 'b'])  # {'a', 'b'}
field.to_representation(['a', 'c'])  # {'a', 'c'}
```

### FilePathField

Choice field that lists files in a directory.

```python
class TemplateSerializer(serializers.Serializer):
    template = serializers.FilePathField(
        path='/path/to/templates/',  # Directory to scan (required)
        match=r'.*\.html$',           # Regex to filter files
        recursive=False,              # Include subdirectories
        allow_files=True,             # Include files
        allow_folders=False,          # Include folders
    )

# Example
field = FilePathField(
    path='/var/templates',
    match=r'.*\.html$',
    recursive=True
)
# choices will be all .html files in /var/templates and subdirs
```

## File Fields

### FileField

File upload field.

```python
class DocumentSerializer(serializers.Serializer):
    file = serializers.FileField(
        max_length=None,        # Max filename length
        allow_empty_file=False, # Allow 0-byte files
        use_url=True,           # Return URL in representation (default: True)
    )

# Usage in view
@api_view(['POST'])
def upload_file(request):
    serializer = DocumentSerializer(data=request.data)
    if serializer.is_valid():
        file = serializer.validated_data['file']
        # file.name, file.size, file.read(), etc.
        return Response({'filename': file.name})
    return Response(serializer.errors, status=400)

# Representation
# If use_url=True: returns file.url
# If use_url=False: returns file.name
```

### ImageField

File field with image validation.

```python
avatar = serializers.ImageField(
    max_length=None,        # Max filename length
    allow_empty_file=False,
    use_url=True,
)

# Validates that uploaded file is a valid image (uses Pillow)
# Same parameters as FileField
```

## Composite Fields

### ListField

Field containing a list of items.

```python
class ArticleSerializer(serializers.Serializer):
    # List of strings
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        min_length=None,        # Minimum list length
        max_length=None,        # Maximum list length
        allow_empty=True,       # Allow empty list (default: True)
    )

    # List of integers
    scores = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=100),
        min_length=1,
        max_length=10,
    )

    # Unvalidated list (not recommended)
    raw_data = serializers.ListField()

# Examples
field = ListField(child=IntegerField())
field.to_internal_value([1, 2, 3])       # [1, 2, 3]
field.to_internal_value(['1', '2'])      # [1, 2] - child converts to int

# Validation per item
field = ListField(
    child=IntegerField(min_value=0, max_value=10),
    min_length=2,
    max_length=5,
)
field.to_internal_value([1, 5, 9])       # [1, 5, 9] - valid
field.to_internal_value([15])            # ValidationError - value too high
field.to_internal_value([1])             # ValidationError - too few items
```

### DictField

Field containing a dictionary of items.

```python
class ConfigSerializer(serializers.Serializer):
    # Dict with string values
    settings = serializers.DictField(
        child=serializers.CharField(max_length=100),
        allow_empty=True,       # Allow empty dict (default: True)
    )

    # Dict with integer values
    scores = serializers.DictField(
        child=serializers.IntegerField(min_value=0)
    )

    # Unvalidated dict (not recommended)
    metadata = serializers.DictField()

# Examples
field = DictField(child=IntegerField())
field.to_internal_value({'a': 1, 'b': 2})       # {'a': 1, 'b': 2}
field.to_internal_value({'x': '10'})            # {'x': 10} - child converts
```

### HStoreField

PostgreSQL HStore field (dict with string values only).

```python
# Requires PostgreSQL with HStore extension
attributes = serializers.HStoreField(
    child=serializers.CharField(allow_blank=True, allow_null=True),
)

# All keys and values must be strings
field.to_internal_value({'color': 'red', 'size': 'large'})  # Valid
```

### JSONField

Field for arbitrary JSON data.

```python
class DataSerializer(serializers.Serializer):
    metadata = serializers.JSONField(
        binary=False,           # Expect bytes instead of string
        encoder=None,           # Custom JSON encoder
        decoder=None,           # Custom JSON decoder
    )

# Accepts any JSON-serializable data
field = JSONField()
field.to_internal_value({'key': 'value'})     # {'key': 'value'}
field.to_internal_value([1, 2, 3])            # [1, 2, 3]
field.to_internal_value('string')             # 'string'
field.to_internal_value(123)                  # 123

# Custom encoder example
import json
from datetime import datetime

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

data_field = JSONField(encoder=DateTimeEncoder)
```

## Specialized Fields

### UUIDField

UUID field with format options.

```python
class ResourceSerializer(serializers.Serializer):
    id = serializers.UUIDField(
        format='hex_verbose',  # Output format (see below)
    )

# Format options:
# 'hex_verbose': '12345678-1234-5678-1234-567812345678' (default)
# 'hex': '12345678123456781234567812345678'
# 'int': 12345678123456781234567812345678 (integer)
# 'urn': 'urn:uuid:12345678-1234-5678-1234-567812345678'

# Examples
import uuid
field = UUIDField()
field.to_internal_value('12345678-1234-5678-1234-567812345678')  # UUID object
field.to_internal_value(12345678123456781234567812345678)        # UUID object
field.to_representation(uuid.uuid4())                             # String UUID
```

### IPAddressField

IPv4 or IPv6 address.

```python
class ServerSerializer(serializers.Serializer):
    ip_address = serializers.IPAddressField(
        protocol='both',  # 'both', 'ipv4', or 'ipv6'
    )

# Examples
field = IPAddressField(protocol='ipv4')
field.to_internal_value('192.168.1.1')      # '192.168.1.1'
field.to_internal_value('::1')              # ValidationError - IPv6 not allowed

field = IPAddressField(protocol='both')
field.to_internal_value('192.168.1.1')      # '192.168.1.1'
field.to_internal_value('2001:db8::1')      # '2001:db8::1'
```

### SerializerMethodField

Read-only field computed by a method.

```python
class BookSerializer(serializers.Serializer):
    title = serializers.CharField()
    author_name = serializers.CharField()

    # Method field (read-only)
    full_title = serializers.SerializerMethodField()

    def get_full_title(self, obj):
        """
        Method name is 'get_<field_name>'
        Receives the object being serialized
        """
        return f"{obj.title} by {obj.author_name}"

    # Custom method name
    summary = serializers.SerializerMethodField(method_name='generate_summary')

    def generate_summary(self, obj):
        return f"{obj.title[:50]}..."

# Always read-only, always uses source='*' (receives full object)
# Performance note: Called once per object, can't be optimized with select_related
```

### ReadOnlyField

Returns the field value as-is, no validation.

```python
class BookSerializer(serializers.Serializer):
    # Read-only field that returns attribute value
    id = serializers.ReadOnlyField()

    # With method call
    full_name = serializers.ReadOnlyField(source='get_full_name')

    # With dotted notation
    author_email = serializers.ReadOnlyField(source='author.email')

# Always read-only (implicitly)
# No to_internal_value() - never used for input
# Simple to_representation() - returns value as-is
```

### HiddenField

Field with a default value, not shown in input/output.

```python
class CommentSerializer(serializers.Serializer):
    text = serializers.CharField()

    # Hidden field with default
    created_by = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

    # Usage in view
    def create(self, request):
        serializer = CommentSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            # validated_data includes 'created_by' automatically
            comment = serializer.save()

# Common defaults:
# CurrentUserDefault() - returns request.user
# CreateOnlyDefault(value) - only used on create, not update
```

### ModelField

Generic wrapper for custom Django model fields.

```python
# Automatically used by ModelSerializer for unrecognized field types
# Rarely used explicitly

# Example: Custom Django field
class ColorField(models.Field):
    # Custom model field implementation
    pass

class Product(models.Model):
    color = ColorField()

class ProductSerializer(serializers.ModelSerializer):
    # ModelField is automatically used for 'color'
    class Meta:
        model = Product
        fields = ['color']

# Or explicitly:
color = serializers.ModelField(model_field=Product._meta.get_field('color'))
```

## Field Type Selection Guide

### For Validation

| Data Type | Recommended Field | Why |
|-----------|------------------|-----|
| Text | CharField | Length validation |
| Email | EmailField | Email validation |
| URL | URLField | URL validation |
| Money | DecimalField | Precision |
| Integer | IntegerField | Range validation |
| Float | FloatField | Approximate numbers |
| Boolean | BooleanField | True/False |
| Date | DateField | Date-only |
| DateTime | DateTimeField | Timezone handling |
| Duration | DurationField | Time spans |
| UUID | UUIDField | Format handling |
| File | FileField | Upload handling |
| Image | ImageField | Image validation |
| JSON | JSONField | Nested data |
| List | ListField | Multiple values |
| Choices | ChoiceField | Limited options |

### For Performance

- Use `read_only=True` for computed fields
- Use `source` instead of SerializerMethodField when possible
- Use `ReadOnlyField` for simple attribute access
- Avoid SerializerMethodField in list views (can't optimize)

### For Type Safety

- Always specify `max_length` for CharField
- Always specify `max_digits` and `decimal_places` for DecimalField
- Use `allow_null=True` explicitly when None is valid
- Use `required=False` explicitly when field is optional
