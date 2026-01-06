# Validation Reference

DRF provides three validation levels: field-level, object-level, and validators.

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
   └─> UniqueValidator, UniqueTogetherValidator

If any step raises ValidationError, validation stops.
```

## Field-Level Validation

### Built-in Field Validation

Every field type has automatic validation:

```python
class BookSerializer(serializers.Serializer):
    # CharField validates type and length
    title = serializers.CharField(
        max_length=200,      # MaxLengthValidator added
        min_length=1,        # MinLengthValidator added
        allow_blank=False,
    )

    # IntegerField validates range
    pages = serializers.IntegerField(
        min_value=1,         # MinValueValidator added
        max_value=10000,     # MaxValueValidator added
    )

    # EmailField validates format
    email = serializers.EmailField()  # EmailValidator added
```

### validate_<field_name>() Method

Custom validation for specific fields:

```python
class BookSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    pages = serializers.IntegerField()

    def validate_title(self, value):
        """
        MUST return the value (or transformed value)
        Called after field.to_internal_value() and validators
        """
        if 'spam' in value.lower():
            raise serializers.ValidationError("Title contains spam")
        return value.title()  # Transform to title case

    def validate_pages(self, value):
        if value <= 0:
            raise serializers.ValidationError("Pages must be positive")
        return value
```

**Important:** Always return the value!

## Object-Level Validation

Cross-field validation using the `validate()` method:

```python
class EventSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, attrs):
        """
        MUST return attrs (or modified attrs)
        Called after all field-level validation
        """
        if attrs['end_date'] < attrs['start_date']:
            raise serializers.ValidationError(
                "End date must be after start date"
            )

        # Can add computed fields
        attrs['duration'] = (attrs['end_date'] - attrs['start_date']).days

        return attrs
```

### Field-Specific Errors from validate()

```python
def validate(self, attrs):
    if attrs['max_attendees'] < attrs['min_attendees']:
        raise serializers.ValidationError({
            'max_attendees': 'Max must be >= min',
            'min_attendees': 'Min must be <= max',
        })
    return attrs
```

### Accessing Instance in validate()

For updates, check the current state:

```python
class BookSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        # self.instance is None for creation, object for updates
        if self.instance is not None:
            # This is an update
            old_status = self.instance.status
            new_status = attrs.get('status', old_status)

            if old_status == 'published' and new_status == 'draft':
                raise serializers.ValidationError(
                    "Cannot revert published book to draft"
                )
        return attrs
```

## Built-in Validators

### UniqueValidator

Ensure field value is unique:

```python
from rest_framework.validators import UniqueValidator

username = serializers.CharField(
    validators=[
        UniqueValidator(
            queryset=User.objects.all(),
            message='Username already exists'
        )
    ]
)

# ModelSerializer adds this automatically for unique fields
```

### UniqueTogetherValidator

Ensure combination of fields is unique:

```python
from rest_framework.validators import UniqueTogetherValidator

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['title', 'author']
        validators = [
            UniqueTogetherValidator(
                queryset=Book.objects.all(),
                fields=['title', 'author']
            )
        ]

# ModelSerializer adds automatically if model has unique_together
```

## Custom Error Messages

```python
title = serializers.CharField(
    max_length=200,
    error_messages={
        'required': 'Title is required',
        'max_length': 'Title too long (max {max_length} chars)',
        'blank': 'Title cannot be blank',
    }
)
```

## Best Practices

### 1. Use Field Validators for Simple Rules

```python
# Good
pages = serializers.IntegerField(min_value=1, max_value=10000)

# Overkill
pages = serializers.IntegerField()
def validate_pages(self, value):
    if value < 1 or value > 10000:
        raise serializers.ValidationError("Invalid")
    return value
```

### 2. Use validate_<field>() for Field-Specific Logic

```python
# Good - field-specific business logic
def validate_username(self, value):
    if User.objects.filter(username=value).exists():
        raise serializers.ValidationError("Username taken")
    return value
```

### 3. Use validate() for Cross-Field Logic

```python
# Good - comparing multiple fields
def validate(self, attrs):
    if attrs['end_date'] < attrs['start_date']:
        raise serializers.ValidationError("Invalid date range")
    return attrs
```

### 4. Always Return Values

```python
# Good
def validate_title(self, value):
    if 'spam' in value:
        raise serializers.ValidationError("Spam")
    return value  # MUST return

# Bad - value becomes None!
def validate_title(self, value):
    if 'spam' in value:
        raise serializers.ValidationError("Spam")
    # Missing return!
```

### 5. Provide Clear Error Messages

```python
# Good - clear and actionable
raise serializers.ValidationError(
    "Password must be at least 8 characters and include a number"
)

# Bad - vague
raise serializers.ValidationError("Invalid password")
```

## Testing Validation

```python
def test_valid_data():
    serializer = BookSerializer(data={'title': 'Book', 'pages': 200})
    assert serializer.is_valid()

def test_invalid_pages():
    serializer = BookSerializer(data={'title': 'Book', 'pages': -5})
    assert not serializer.is_valid()
    assert 'pages' in serializer.errors

def test_cross_field_validation():
    serializer = EventSerializer(data={
        'start_date': '2024-12-31',
        'end_date': '2024-01-01',
    })
    assert not serializer.is_valid()
    assert 'non_field_errors' in serializer.errors
```
