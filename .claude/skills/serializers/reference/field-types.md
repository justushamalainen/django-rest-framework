# Field Types Reference

DRF provides 40+ field types, but these 15 cover 95% of use cases.

## Common Parameters

All fields accept these parameters:

```python
field = SomeField(
    required=True,              # Default: True
    allow_null=False,           # Allow None values (default: False)
    default=None,               # Default value if not provided
    validators=[],              # List of validator functions
    read_only=False,            # Only in output, never in input
    write_only=False,           # Only in input, never in output
    label='Field Label',        # Human-readable label
    help_text='Help text',      # Description
    source=None,                # Source attribute (default: field name)
)
```

## String Fields

### CharField

Basic string field with length validation:

```python
title = serializers.CharField(
    max_length=200,          # Maximum length (required)
    min_length=1,            # Minimum length
    allow_blank=False,       # Allow empty strings (default: False)
    trim_whitespace=True,    # Strip whitespace (default: True)
)

# Common patterns
name = serializers.CharField(max_length=100, required=True)
notes = serializers.CharField(allow_blank=True, required=False)
```

### EmailField

CharField with email validation:

```python
email = serializers.EmailField(max_length=254)
```

### URLField

CharField with URL validation:

```python
website = serializers.URLField(max_length=200)
```

### SlugField

String containing only letters, numbers, underscores, or hyphens:

```python
slug = serializers.SlugField(
    max_length=100,
    allow_unicode=False,  # ASCII only (default)
)
```

## Numeric Fields

### IntegerField

Integer with optional min/max validation:

```python
pages = serializers.IntegerField(
    min_value=1,           # Minimum value
    max_value=10000,       # Maximum value
)

year = serializers.IntegerField(min_value=1000, max_value=9999)
quantity = serializers.IntegerField(min_value=0, default=0)
```

### FloatField

Floating-point number:

```python
temperature = serializers.FloatField(
    min_value=-273.15,
    max_value=1000.0,
)

percentage = serializers.FloatField(min_value=0.0, max_value=100.0)
```

### DecimalField

Precise decimal numbers (use for money):

```python
price = serializers.DecimalField(
    max_digits=8,          # Total digits (required)
    decimal_places=2,      # Digits after decimal (required)
    min_value=0,
)

# Always use DecimalField for money, never FloatField!
```

## Boolean Fields

### BooleanField

True/False values:

```python
is_available = serializers.BooleanField(default=True)
is_published = serializers.BooleanField(allow_null=True)  # Three-state

# Accepts: True, 'true', 't', '1', 1, 'yes', 'on'
# Accepts: False, 'false', 'f', '0', 0, 'no', 'off'
```

## Date/Time Fields

### DateTimeField

Date and time with timezone support:

```python
created_at = serializers.DateTimeField(
    format=None,           # None = ISO-8601 (default)
    read_only=True,
)

# Custom format
formatted_date = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S')

# Input:  '2024-01-15T10:30:00Z'
# Output: '2024-01-15T10:30:00Z' (ISO-8601)
```

### DateField

Date without time:

```python
birth_date = serializers.DateField()
published_date = serializers.DateField(format='%Y-%m-%d')

# Input:  '2024-01-15'
# Output: '2024-01-15'
```

## Choice Fields

### ChoiceField

Field that must be one of limited values:

```python
# List of choices
status = serializers.ChoiceField(
    choices=['draft', 'published', 'archived']
)

# Tuple choices (value, display)
genre = serializers.ChoiceField(
    choices=[
        ('fiction', 'Fiction'),
        ('nonfiction', 'Non-Fiction'),
        ('scifi', 'Science Fiction'),
    ]
)

# Django model choices (automatic with ModelSerializer)
class Book(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
```

## Composite Fields

### ListField

Field containing a list of items:

```python
# List of strings
tags = serializers.ListField(
    child=serializers.CharField(max_length=50),
    min_length=None,        # Minimum list length
    max_length=None,        # Maximum list length
    allow_empty=True,
)

# List of integers
scores = serializers.ListField(
    child=serializers.IntegerField(min_value=0, max_value=100),
    min_length=1,
    max_length=10,
)

# Example
field = ListField(child=IntegerField())
field.to_internal_value([1, 2, 3])       # [1, 2, 3]
field.to_internal_value(['1', '2'])      # [1, 2]
```

### DictField

Field containing a dictionary:

```python
# Dict with string values
settings = serializers.DictField(
    child=serializers.CharField(max_length=100),
    allow_empty=True,
)

# Dict with integer values
scores = serializers.DictField(
    child=serializers.IntegerField(min_value=0)
)

# Example
field = DictField(child=IntegerField())
field.to_internal_value({'a': 1, 'b': 2})  # {'a': 1, 'b': 2}
```

### JSONField

Field for arbitrary JSON data:

```python
metadata = serializers.JSONField()

# Accepts any JSON-serializable data
field = JSONField()
field.to_internal_value({'key': 'value'})  # {'key': 'value'}
field.to_internal_value([1, 2, 3])         # [1, 2, 3]
field.to_internal_value('string')          # 'string'
```

## Specialized Fields

### SerializerMethodField

Read-only computed field:

```python
class BookSerializer(serializers.ModelSerializer):
    # Method field (always read-only)
    full_title = serializers.SerializerMethodField()

    def get_full_title(self, obj):
        """Method name is 'get_<field_name>'"""
        return f"{obj.title} by {obj.author.name}"

    # Custom method name
    summary = serializers.SerializerMethodField(method_name='generate_summary')

    def generate_summary(self, obj):
        return f"{obj.title[:50]}..."
```

**Note:** SerializerMethodField can't be optimized with select_related. Use sparingly in list views.

## Field Selection Guide

| Data Type | Recommended Field | Why |
|-----------|------------------|-----|
| Text | CharField | Length validation |
| Email | EmailField | Email validation |
| URL | URLField | URL validation |
| Money | DecimalField | Precision (never use Float!) |
| Integer | IntegerField | Range validation |
| Float | FloatField | Approximate numbers |
| Boolean | BooleanField | True/False |
| Date | DateField | Date-only |
| DateTime | DateTimeField | Timezone handling |
| Choices | ChoiceField | Limited options |
| List | ListField | Multiple values |
| Dict | DictField | Key-value pairs |
| JSON | JSONField | Nested data |
| Computed | SerializerMethodField | Calculated values |

## Common Patterns

### Optional Fields

```python
# Optional with default
notes = serializers.CharField(default='', allow_blank=True)

# Optional, can be null
middle_name = serializers.CharField(required=False, allow_null=True)

# Optional with callable default
created_at = serializers.DateTimeField(default=timezone.now)
```

### Read-Only vs Write-Only

```python
# Read-only computed field
book_count = serializers.SerializerMethodField()

# Write-only sensitive field
password = serializers.CharField(write_only=True)

# Read-only database field
id = serializers.IntegerField(read_only=True)
```

### source Parameter

```python
# Map to different model field
book_title = serializers.CharField(source='title')

# Access nested attribute
author_name = serializers.CharField(source='author.name', read_only=True)

# Access method
display_name = serializers.CharField(source='get_full_name', read_only=True)
```

## Performance Tips

1. Use `read_only=True` for fields that don't need validation
2. Use `source` instead of SerializerMethodField when possible
3. Avoid SerializerMethodField in list views (can't be optimized)
4. Use appropriate field types to get automatic validation
