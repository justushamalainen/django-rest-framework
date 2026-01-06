# Django REST Framework - Claude Skills Plan

## Overview

This document outlines the proposed structure for Claude Skills to help developers use Django REST Framework more efficiently and idiomatically.

Based on codebase analysis:
- **12,551 lines** of core code across 34 Python modules
- **69 documentation files** covering tutorials, API guides, and topics
- Key areas: Serializers, Views/ViewSets, Authentication, Permissions, Pagination, Filtering, Testing

---

## Proposed Skills Structure

```
.claude/skills/
├── drf-quickstart/
│   ├── SKILL.md
│   └── reference/
│       ├── project-setup.md
│       └── templates/
│           └── basic-api.py
│
├── drf-serializers/
│   ├── SKILL.md
│   └── reference/
│       ├── field-types.md
│       ├── validation.md
│       ├── nested-serializers.md
│       └── examples/
│           └── common-patterns.py
│
├── drf-views/
│   ├── SKILL.md
│   └── reference/
│       ├── apiview.md
│       ├── generic-views.md
│       ├── viewsets.md
│       └── examples/
│           └── view-patterns.py
│
├── drf-authentication/
│   ├── SKILL.md
│   └── reference/
│       ├── builtin-auth.md
│       ├── custom-auth.md
│       └── token-auth.md
│
├── drf-permissions/
│   ├── SKILL.md
│   └── reference/
│       ├── builtin-permissions.md
│       ├── custom-permissions.md
│       └── object-permissions.md
│
├── drf-testing/
│   ├── SKILL.md
│   └── reference/
│       ├── test-client.md
│       ├── test-patterns.md
│       └── examples/
│           └── test-templates.py
│
└── drf-advanced/
    ├── SKILL.md
    └── reference/
        ├── pagination.md
        ├── filtering.md
        ├── throttling.md
        ├── versioning.md
        └── schema-generation.md
```

---

## Skill Descriptions & Triggers

### 1. drf-quickstart
**Description:** Quick setup and scaffolding for Django REST Framework projects. Use when starting a new DRF project, adding DRF to existing Django project, or creating basic CRUD APIs. Provides project setup, settings configuration, and basic API patterns.

**Trigger Conditions:**
- "Create a new DRF project"
- "Add REST API to Django project"
- "Setup Django REST Framework"
- "Create basic API endpoint"

**Contents:**
- Project setup checklist
- Settings configuration (INSTALLED_APPS, REST_FRAMEWORK settings)
- Basic serializer + viewset + router pattern
- URL configuration

---

### 2. drf-serializers
**Description:** Creating and customizing Django REST Framework serializers for data validation and transformation. Use when defining API data schemas, handling complex nested data, implementing custom validation, or optimizing serializer performance.

**Trigger Conditions:**
- "Create serializer for model"
- "Nested serializer"
- "Custom validation"
- "Serializer fields"
- "Writable nested serializers"

**Contents:**
- Field type reference (30+ field types)
- ModelSerializer patterns
- Nested serializer handling
- Validation (field-level, object-level)
- Performance optimization (select_related, prefetch_related)
- Custom field creation

**Key Classes:**
- `Serializer`, `ModelSerializer`
- `SerializerMethodField`, `SlugRelatedField`
- `PrimaryKeyRelatedField`, `HyperlinkedRelatedField`

---

### 3. drf-views
**Description:** Building API views and viewsets in Django REST Framework. Use when creating API endpoints, choosing between APIView/generic views/viewsets, implementing custom actions, or configuring URL routing.

**Trigger Conditions:**
- "Create API view"
- "ViewSet vs APIView"
- "Custom viewset action"
- "Router configuration"
- "Generic views"

**Contents:**
- APIView basics
- Generic views (List, Create, Retrieve, Update, Destroy)
- ViewSets and ModelViewSet
- Mixin composition patterns
- Custom actions with @action decorator
- Router registration and URL generation

**Key Classes:**
- `APIView`, `GenericAPIView`
- `ViewSet`, `GenericViewSet`, `ModelViewSet`
- `SimpleRouter`, `DefaultRouter`

---

### 4. drf-authentication
**Description:** Implementing authentication in Django REST Framework APIs. Use when adding user authentication, implementing token-based auth, creating custom authentication schemes, or integrating with OAuth/JWT.

**Trigger Conditions:**
- "Add authentication to API"
- "Token authentication"
- "Custom authentication"
- "Session authentication"
- "API authentication"

**Contents:**
- Built-in authentication classes
- Token authentication setup
- Custom authentication implementation
- Authentication flow explanation
- Multi-authentication configuration

**Key Classes:**
- `BaseAuthentication`
- `TokenAuthentication`, `SessionAuthentication`, `BasicAuthentication`
- `Token` model (authtoken app)

---

### 5. drf-permissions
**Description:** Implementing permission and access control in Django REST Framework. Use when restricting API access, creating custom permission classes, implementing object-level permissions, or combining permission logic.

**Trigger Conditions:**
- "Add permissions to API"
- "Custom permission class"
- "Object permissions"
- "IsAuthenticated permission"
- "Owner-only access"

**Contents:**
- Built-in permission classes
- Custom permission implementation
- Object-level permissions
- Permission composition (AND, OR, NOT operators)
- Django model permissions integration

**Key Classes:**
- `BasePermission`
- `IsAuthenticated`, `IsAdminUser`, `IsAuthenticatedOrReadOnly`
- `DjangoModelPermissions`, `DjangoObjectPermissions`

---

### 6. drf-testing
**Description:** Testing Django REST Framework APIs effectively. Use when writing API tests, setting up test fixtures, testing authentication/permissions, or debugging API behavior.

**Trigger Conditions:**
- "Test DRF API"
- "API test client"
- "Test authentication"
- "APIRequestFactory"
- "Test viewset"

**Contents:**
- APIRequestFactory vs APIClient
- force_authenticate() usage
- Testing serializers
- Testing views and viewsets
- Testing authentication and permissions
- Common test patterns and fixtures

**Key Classes:**
- `APIRequestFactory`, `APIClient`, `APITestCase`
- `force_authenticate()`

---

### 7. drf-advanced
**Description:** Advanced Django REST Framework features including pagination, filtering, throttling, versioning, and schema generation. Use when implementing complex API features, optimizing performance, or generating API documentation.

**Trigger Conditions:**
- "Add pagination"
- "Filter queryset"
- "Rate limiting"
- "API versioning"
- "OpenAPI schema"
- "API documentation"

**Contents:**
- Pagination (Page, LimitOffset, Cursor)
- Filtering backends (Search, Ordering, DjangoFilter)
- Throttling/rate limiting
- API versioning strategies
- Schema generation (OpenAPI)
- Content negotiation

---

## Priority and Implementation Order

### Phase 1: Core Skills (Essential)
1. **drf-quickstart** - Foundation for all DRF work
2. **drf-serializers** - Most complex and frequently used component
3. **drf-views** - Core API endpoint creation

### Phase 2: Security Skills
4. **drf-authentication** - Required for any authenticated API
5. **drf-permissions** - Access control patterns

### Phase 3: Quality & Advanced
6. **drf-testing** - Ensure code quality
7. **drf-advanced** - Production-ready features

---

## Skill Content Guidelines

### Each SKILL.md Should Include:
1. **Description** - What it does and when to use it
2. **Quick Reference** - Most common patterns (copy-paste ready)
3. **Decision Trees** - Help choose between options (APIView vs ViewSet, etc.)
4. **Anti-patterns** - Common mistakes to avoid
5. **Links to Reference Files** - For detailed information

### Reference Files Should Include:
1. **Table of Contents** (if >100 lines)
2. **Code Examples** - Concrete, working code
3. **Configuration Options** - Settings and their effects
4. **Troubleshooting** - Common errors and solutions

### Scripts/Templates Should Include:
1. **Validation Logic** - Check prerequisites
2. **Error Handling** - Clear error messages
3. **Documentation** - Comments explaining each section

---

## Example: drf-serializers SKILL.md Structure

```markdown
# DRF Serializers

Creating and customizing Django REST Framework serializers.
Use when building API endpoints that need data validation and transformation.

## Quick Start

### Basic ModelSerializer
[code example]

### Nested Serializer
[code example]

### Custom Validation
[code example]

## Decision Tree

- Need automatic model field mapping? → ModelSerializer
- Need complete control? → Serializer
- Read-only data? → SerializerMethodField
- Complex nested writes? → See reference/nested-serializers.md

## Common Patterns
[link to reference/common-patterns.py]

## Field Types
[link to reference/field-types.md]

## Validation
[link to reference/validation.md]

## Anti-patterns
- Don't use `SerializerMethodField` for writable fields
- Don't forget `select_related` for FK fields
- Don't override `save()` when `create()`/`update()` suffice
```

---

## File Size Estimates

| Skill | SKILL.md | Reference Files | Total |
|-------|----------|-----------------|-------|
| drf-quickstart | ~150 lines | ~200 lines | ~350 lines |
| drf-serializers | ~300 lines | ~600 lines | ~900 lines |
| drf-views | ~250 lines | ~400 lines | ~650 lines |
| drf-authentication | ~200 lines | ~300 lines | ~500 lines |
| drf-permissions | ~200 lines | ~250 lines | ~450 lines |
| drf-testing | ~200 lines | ~350 lines | ~550 lines |
| drf-advanced | ~250 lines | ~500 lines | ~750 lines |

All SKILL.md files kept under 500 lines as recommended.

---

## Next Steps

1. Create directory structure
2. Implement drf-quickstart skill (foundation)
3. Implement drf-serializers skill (highest complexity)
4. Implement remaining skills in priority order
5. Test skills with common DRF tasks
6. Iterate based on usage patterns
