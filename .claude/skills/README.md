# Django REST Framework Skills

Comprehensive Claude Skills for building APIs with Django REST Framework efficiently and idiomatically.

---

## Quick Navigation

| Phase | Skill | Description | Difficulty |
|-------|-------|-------------|------------|
| **Core** | [quickstart](./quickstart/) | Project setup and first API | Beginner |
| **Core** | [serializers](./serializers/) | Data validation and transformation | Intermediate |
| **Core** | [views](./views/) | APIView, ViewSets, generic views | Intermediate |
| **Core** | [authentication](./authentication/) | Auth schemes and token management | Intermediate |
| **Core** | [permissions](./permissions/) | Access control and custom permissions | Intermediate |
| **Essential** | [routers](./routers/) | URL routing and patterns | Intermediate |
| **Essential** | [testing](./testing/) | API testing patterns | Intermediate |
| **Essential** | [error-handling](./error-handling/) | Exceptions and error responses | Intermediate |
| **Advanced** | [pagination-filtering](./pagination-filtering/) | Pagination and filter backends | Intermediate |
| **Advanced** | [throttling](./throttling/) | Rate limiting | Intermediate |
| **Advanced** | [versioning](./versioning/) | API versioning strategies | Advanced |
| **Advanced** | [api-documentation](./api-documentation/) | OpenAPI and schema generation | Advanced |
| **Special** | [advanced-routing](./advanced-routing/) | Custom routers, nested URLs (edge cases) | Advanced |

---

## Learning Path

### Phase 1: Core Skills (Build a Working API)

Start here to build a complete, secured REST API.

```
quickstart → serializers → views → authentication → permissions
```

1. **[quickstart](./quickstart/)** - Set up your project and create your first endpoint
2. **[serializers](./serializers/)** - Master data validation and transformation
3. **[views](./views/)** - Build API endpoints with views and viewsets
4. **[authentication](./authentication/)** - Add user authentication
5. **[permissions](./permissions/)** - Control who can access what

**Outcome:** A fully functional, authenticated REST API

### Phase 2: Essential Skills (Production-Ready)

Add testing, routing, and error handling for production.

```
routers → testing → error-handling
```

6. **[routers](./routers/)** - Automatic URL routing for viewsets
7. **[testing](./testing/)** - Write comprehensive API tests
8. **[error-handling](./error-handling/)** - Handle errors gracefully

**Outcome:** A testable, maintainable API ready for deployment

### Phase 3: Advanced Skills (Enterprise Features)

Add advanced features for large-scale APIs.

```
pagination-filtering → throttling → versioning → api-documentation
```

9. **[pagination-filtering](./pagination-filtering/)** - Handle large datasets efficiently
10. **[throttling](./throttling/)** - Protect your API with rate limiting
11. **[versioning](./versioning/)** - Manage API evolution
12. **[api-documentation](./api-documentation/)** - Generate OpenAPI docs

**Outcome:** An enterprise-grade API with all production features

---

## Skill Dependencies

```
                    quickstart
                        │
                        ▼
                   serializers
                        │
                        ▼
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
    views ────► authentication ────► permissions
        │               │               │
        ├───────────────┼───────────────┤
        │               │               │
        ▼               ▼               ▼
    routers         testing      error-handling
        │               │               │
        └───────────────┼───────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
  pagination-      throttling      versioning
   filtering            │               │
        │               │               │
        └───────────────┼───────────────┘
                        │
                        ▼
               api-documentation
```

---

## Skill Contents

Each skill contains:

```
skill-name/
├── SKILL.md              # Main guide with quick start and decision trees
└── reference/
    ├── topic-a.md        # Detailed reference documentation
    ├── topic-b.md        # More reference documentation
    └── examples/
        └── patterns.py   # Working, copy-paste ready code
```

### What's in Each SKILL.md

- **Frontmatter** - Metadata, difficulty, keywords
- **What You'll Learn** - Clear learning objectives
- **Quick Start** - Get running in 5 minutes
- **Decision Tree** - Choose the right approach
- **Common Mistakes** - Avoid common pitfalls
- **Reference Links** - Deep-dive documentation

---

## Skills by Use Case

### "I'm building my first DRF API"
→ Start with [quickstart](./quickstart/) Path A

### "I need to validate complex data"
→ See [serializers](./serializers/), especially nested-writes.md

### "Which view type should I use?"
→ Check the decision tree in [views](./views/)

### "How do I add authentication?"
→ [authentication](./authentication/) covers Token, JWT, OAuth

### "I need to restrict access"
→ [permissions](./permissions/) with composition patterns

### "How do I test my API?"
→ [testing](./testing/) covers pytest and unittest approaches

### "My API returns errors incorrectly"
→ [error-handling](./error-handling/) for custom handlers

### "I need pagination for large datasets"
→ [pagination-filtering](./pagination-filtering/) with performance tips

### "How do I prevent API abuse?"
→ [throttling](./throttling/) for rate limiting

### "I need to version my API"
→ [versioning](./versioning/) covers all 5 strategies

### "I need API documentation"
→ [api-documentation](./api-documentation/) for OpenAPI/Swagger

### "I need custom URL patterns or nested routes"
→ [advanced-routing](./advanced-routing/) for custom routers and nested resources (special cases only)

---

## Total Content

| Metric | Count |
|--------|-------|
| Skills | 13 |
| Reference Files | 35+ |
| Code Examples | 3,000+ lines |
| Total Documentation | ~12,000 lines |

---

## DRF Source Reference

These skills are based on Django REST Framework source code:

| Module | Lines | Primary Skills |
|--------|-------|----------------|
| serializers.py | 1,742 | serializers |
| fields.py | 1,964 | serializers |
| views.py | 527 | views |
| generics.py | 295 | views |
| viewsets.py | 255 | views |
| routers.py | 390 | routers |
| authentication.py | 232 | authentication |
| permissions.py | 314 | permissions |
| pagination.py | 990 | pagination-filtering |
| filters.py | 383 | pagination-filtering |
| throttling.py | 250 | throttling |
| versioning.py | 186 | versioning |
| schemas/ | 1,859 | api-documentation |
| exceptions.py | 264 | error-handling |
| test.py | 403 | testing |

---

## Version

- **Skills Version:** 1.0.0
- **DRF Compatibility:** 3.14+
- **Django Compatibility:** 4.0+
- **Python Compatibility:** 3.8+
- **Last Updated:** 2026-01-06
