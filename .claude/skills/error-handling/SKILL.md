---
name: Error Handling
description: Master DRF exception handling, custom error responses, and debugging strategies
keywords: [exceptions, errors, APIException, validation, error responses, debugging]
version: 1.0.0
---

# DRF Error Handling Skill

**Key Insight: Most error handling is automatic. You rarely need custom handlers.**

Django REST Framework's default error handling covers 95% of use cases. This skill teaches you how to use built-in exceptions effectively and when (rarely) to customize.

## What You'll Learn

- Use **ValidationError** for invalid input (the 80% case)
- Choose between **NotFound**, **PermissionDenied**, and **NotAuthenticated**
- Avoid common mistakes with error handling
- Customize exception handlers only when truly needed

## Quick Start: ValidationError (The 80% Case)

Most API errors are validation errors. DRF makes these simple:

```python
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['POST'])
def create_user(request):
    # Field-specific errors (best practice)
    if not request.data.get('email'):
        raise ValidationError({'email': 'This field is required'})

    if '@' not in request.data.get('email', ''):
        raise ValidationError({'email': 'Enter a valid email address'})

    # Multiple field errors
    errors = {}
    if len(request.data.get('password', '')) < 8:
        errors['password'] = 'Password must be at least 8 characters'
    if request.data.get('age', 0) < 18:
        errors['age'] = 'Must be 18 or older'

    if errors:
        raise ValidationError(errors)

    # Single error message (less common)
    if User.objects.filter(email=request.data['email']).exists():
        raise ValidationError('Email already registered')

    # Create user...
    return Response({'id': user.id}, status=201)
```

**Response format:**
```json
{
  "email": ["Enter a valid email address"],
  "password": ["Password must be at least 8 characters"]
}
```

## Decision Tree: Which Exception?

90% of the time, you only need these three:

```
Is the data invalid?
└─ YES → ValidationError (400)

Does the resource exist?
└─ NO → NotFound (404)

Does the user have permission?
└─ NO → PermissionDenied (403)
```

### The Essential Three Exceptions

```python
from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied

@api_view(['GET', 'PUT'])
def update_post(request, post_id):
    # 1. Check if exists
    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        raise NotFound('Post not found')

    # 2. Check permission
    if post.author != request.user:
        raise PermissionDenied('Only the author can edit this post')

    # 3. Validate input
    if request.method == 'PUT':
        if not request.data.get('title'):
            raise ValidationError({'title': 'This field is required'})

        if len(request.data['title']) > 200:
            raise ValidationError({'title': 'Title too long (max 200 chars)'})

        # Update post...

    return Response(PostSerializer(post).data)
```

## Quick Reference: Other Built-in Exceptions

DRF automatically handles these - you rarely raise them manually:

```python
from rest_framework.exceptions import (
    NotAuthenticated,      # 401 - No auth provided (auto-handled by auth classes)
    AuthenticationFailed,  # 401 - Invalid credentials (auto-handled by auth classes)
    Throttled,            # 429 - Rate limited (auto-handled by throttle classes)
    MethodNotAllowed,     # 405 - Wrong HTTP method (auto-handled by DRF)
    ParseError,           # 400 - Malformed JSON (auto-handled by parsers)
)
```

**Example when you might use them:**
```python
from rest_framework.exceptions import NotAuthenticated

@api_view(['POST'])
def create_premium_content(request):
    if not request.user.is_authenticated:
        raise NotAuthenticated('Login required')

    if not request.user.has_subscription:
        raise PermissionDenied('Premium subscription required')

    # Create content...
```

## Common Mistakes

### 1. Using Wrong Exception for Validation

**Wrong:**
```python
from rest_framework.exceptions import APIException

if not email_valid(data['email']):
    raise APIException("Invalid email")  # Returns 500 - not appropriate!
```

**Right:**
```python
from rest_framework.exceptions import ValidationError

if not email_valid(data['email']):
    raise ValidationError({'email': 'Enter a valid email address'})  # Returns 400
```

### 2. String Errors Instead of Field Mapping

**Wrong:**
```python
# Hard for clients to parse and display field-specific errors
raise ValidationError("Email is invalid and password is too short")
```

**Right:**
```python
# Clients can show errors next to each field
raise ValidationError({
    'email': 'Enter a valid email address',
    'password': 'Password must be at least 8 characters'
})
```

### 3. Not Checking Response is None in Custom Handlers

**Wrong:**
```python
def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    response.data['custom'] = 'field'  # Crashes if response is None!
    return response
```

**Right:**
```python
def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:  # Always check!
        response.data['custom'] = 'field'

    return response
```

## When to Customize Exception Handlers

**You probably don't need a custom handler.** The default is excellent.

Only customize if you need to:
- Add a request ID to all errors for tracking
- Log errors to a monitoring service
- Transform error format for legacy clients

See [Exception Handlers](./reference/exception-handlers.md) for details.

## Reference Documentation

- [Built-in Exceptions](./reference/builtin-exceptions.md) - Complete guide to all exception types
- [Exception Handlers](./reference/exception-handlers.md) - Customizing error responses (rarely needed)

## Key Files in DRF Source

- `/home/user/django-rest-framework/rest_framework/exceptions.py` - All exception classes
- `/home/user/django-rest-framework/rest_framework/views.py` - Default exception_handler

## Pro Tips

1. **Use field-specific errors** - Help users fix issues quickly
2. **ValidationError covers most cases** - Don't overthink it
3. **The default handler is excellent** - Resist customizing it
4. **Django exceptions work too** - `Http404` and Django's `PermissionDenied` are auto-converted
5. **Test error responses** - They're part of your API contract

## Example: Complete View with Error Handling

```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied
from rest_framework.response import Response

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def manage_article(request, article_id):
    """Complete example showing error handling patterns."""

    # Get object or 404
    try:
        article = Article.objects.get(id=article_id)
    except Article.DoesNotExist:
        raise NotFound('Article not found')

    if request.method == 'GET':
        # Anyone can read
        return Response(ArticleSerializer(article).data)

    # Check ownership for modifications
    if article.author != request.user:
        raise PermissionDenied('Only the author can modify this article')

    if request.method == 'PUT':
        # Validate input
        title = request.data.get('title', '').strip()
        content = request.data.get('content', '').strip()

        errors = {}
        if not title:
            errors['title'] = 'This field is required'
        elif len(title) > 200:
            errors['title'] = 'Title too long (max 200 characters)'

        if not content:
            errors['content'] = 'This field is required'
        elif len(content) < 100:
            errors['content'] = 'Content too short (min 100 characters)'

        if errors:
            raise ValidationError(errors)

        # Update article
        article.title = title
        article.content = content
        article.save()

        return Response(ArticleSerializer(article).data)

    if request.method == 'DELETE':
        article.delete()
        return Response(status=204)
```
