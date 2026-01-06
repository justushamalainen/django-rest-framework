# Skills Plan Improvement Recommendations

Based on comprehensive review by 10 specialized subagents analyzing different aspects of the plan against the actual DRF codebase and documentation.

---

## Executive Summary

The original SKILLS_PLAN.md is a **solid foundation** but requires significant improvements:

| Issue | Severity | Impact |
|-------|----------|--------|
| "drf-advanced" is too broad | CRITICAL | Should split into 4-5 focused skills |
| Missing 5-8 critical skills | CRITICAL | Incomplete coverage of DRF |
| Auth/Permissions in wrong phase | HIGH | Developers can't build secure APIs in Phase 1 |
| File size estimates too low | HIGH | ~50% underestimated for advanced topics |
| No skill dependencies documented | MEDIUM | Unclear learning path |
| Naming convention redundant | LOW | `drf-` prefix unnecessary |

---

## 1. STRUCTURAL CHANGES

### 1.1 Remove `drf-` Prefix
Skills are already in `.claude/skills/` directory. Simpler names are better:
- `drf-serializers` → `serializers`
- `drf-views` → `views`
- etc.

### 1.2 Split "drf-advanced" Into Focused Skills

**Current (problematic):**
```
drf-advanced/
├── pagination.md
├── filtering.md
├── throttling.md
├── versioning.md
└── schema-generation.md
```

**Recommended (split by concern):**
```
pagination-filtering/     # Related: both about data presentation
throttling/               # Rate limiting (separate concern)
versioning/               # API evolution (separate concern)
api-documentation/        # Schema generation (1,859 lines - deserves its own skill!)
```

### 1.3 Add Missing Critical Skills

| New Skill | Why Critical | Source Lines |
|-----------|--------------|--------------|
| **error-handling** | Exception handling, debugging patterns | 264 lines |
| **validators** | Custom validation (currently scattered) | 354 lines |
| **responses-rendering** | Renderers, content negotiation | 1,107 lines |
| **function-based-views** | @api_view decorator patterns | 289 lines |
| **routers** | URL routing (missing from plan!) | 390 lines |
| **third-party-integrations** | django-filter, JWT, drf-spectacular | N/A |

### 1.4 New Directory Structure

```
.claude/skills/
├── README.md                    # NEW: Navigation index
│
├── _core/                       # Phase 1 skills
│   ├── quickstart/
│   ├── serializers/
│   ├── views/
│   ├── authentication/
│   └── permissions/
│
├── _essential/                  # Phase 2 skills
│   ├── routers/                 # NEW
│   ├── testing/
│   ├── validation/              # NEW (extracted from serializers)
│   └── error-handling/          # NEW
│
└── _advanced/                   # Phase 3 skills
    ├── pagination-filtering/    # MERGED
    ├── throttling/              # SPLIT from advanced
    ├── versioning/              # SPLIT from advanced
    ├── api-documentation/       # NEW (schemas)
    ├── responses-rendering/     # NEW
    └── third-party/             # NEW
```

---

## 2. PHASE REORDERING

### Current (Problematic)
```
Phase 1: quickstart, serializers, views
Phase 2: authentication, permissions
Phase 3: testing, advanced
```

### Recommended (Follows DRF Tutorial)
```
Phase 1: COMPLETE WORKING API (~3,150 lines)
├── quickstart (350 lines)
├── serializers (1,100 lines)  # Expanded
├── views (750 lines)          # Expanded
├── authentication (500 lines) # MOVED UP
└── permissions (450 lines)    # MOVED UP

Phase 2: PRODUCTION PATTERNS (~1,150 lines)
├── routers (300 lines)        # NEW
├── testing (550 lines)
└── error-handling (300 lines) # NEW

Phase 3: ADVANCED FEATURES (~2,500 lines)
├── pagination-filtering (800 lines)
├── throttling (200 lines)
├── versioning (200 lines)
├── api-documentation (500 lines)
├── responses-rendering (400 lines)
└── validators (400 lines)
```

**Rationale:** DRF tutorial introduces auth/permissions in lesson 4 of 6. Most real APIs need authentication from day one.

---

## 3. SKILL-SPECIFIC IMPROVEMENTS

### 3.1 serializers (Highest Priority)

**Current estimate:** 900 lines → **Revised: 1,100+ lines**

**Add reference files:**
```
reference/
├── serializer-types.md          # Serializer vs ModelSerializer vs HyperlinkedModelSerializer
├── field-types-comprehensive.md # All 40+ field types
├── relations-complete.md        # All 5 relation field types
├── validation-detailed.md       # Field-level, object-level, built-in validators
├── nested-serializers.md        # Read-only nested
├── nested-writes.md             # NEW: Writable nested (critical gap!)
├── model-serializer-advanced.md # NEW: build_* methods, Meta options
├── anti-patterns.md             # NEW: N+1 queries, common mistakes
├── examples/
│   ├── basic-serializers.py
│   ├── nested-patterns.py
│   ├── nested-writes.py         # NEW
│   ├── custom-fields.py         # NEW
│   └── performance-optimization.py # NEW
└── troubleshooting.md           # NEW
```

**Critical additions:**
- Writable nested serializers (most common pain point)
- Custom field creation (`to_representation`, `to_internal_value`)
- N+1 query prevention patterns
- `source='*'` and dotted notation
- ListSerializer customization

### 3.2 views

**Current estimate:** 650 lines → **Revised: 750+ lines**

**Add:**
```
reference/
├── apiview.md
├── generic-views.md
├── viewsets.md
├── mixins.md                    # NEW: Dedicated mixin reference
├── decorators-and-fbv.md        # NEW: @api_view patterns
├── routers.md                   # Or separate skill
└── examples/
    ├── view-patterns.py
    ├── custom-actions.py
    ├── function-based-views.py  # NEW
    └── mixin-composition.py     # NEW
```

**Critical additions:**
- Function-based views with @api_view (currently missing!)
- Decision tree: APIView vs Generic vs ViewSet
- @action decorator with detail=True/False
- Policy decorator ordering (must come AFTER @api_view)
- Mixin composition patterns

### 3.3 authentication

**Add:**
```
reference/
├── builtin-auth.md
├── custom-auth.md
├── token-auth.md                # EXPAND significantly
├── jwt-oauth-comparison.md      # NEW: Decision matrix
├── jwt-integration-guide.md     # NEW: simplejwt setup
└── oauth2-patterns.md           # NEW
```

**Critical additions:**
- JWT vs Token vs Session decision matrix
- Token lifecycle management (generation, revocation, expiry)
- Security best practices checklist
- Production deployment guide
- Troubleshooting common auth errors

### 3.4 permissions

**Add:**
```
reference/
├── builtin-permissions.md
├── custom-permissions.md
├── object-permissions.md
└── permission-composition.md    # NEW: AND, OR, NOT operators
```

**Critical additions:**
- Permission composition with examples (currently just mentioned)
- Operator precedence clarification
- Object-level permission performance considerations
- Testing permission patterns

### 3.5 testing

**Current estimate:** 550 lines → **Revised: 950-1,100 lines**

**Add:**
```
reference/
├── test-clients.md              # APIRequestFactory vs APIClient
├── pytest-patterns.md           # NEW: pytest integration
├── testing-authentication.md    # NEW
├── testing-permissions.md       # NEW
├── testing-throttling.md        # NEW
├── fixtures-and-setup.md        # NEW
└── examples/
    ├── basic-client-usage.py
    ├── request-factory-patterns.py
    ├── authentication-testing.py
    ├── permissions-testing.py
    └── serializer-testing.py
```

**Critical additions:**
- Pytest integration (31 DRF test files use pytest)
- Mock patterns with `unittest.mock`
- force_authenticate() patterns
- Cache clearing for throttle tests
- Fixture strategies

### 3.6 quickstart

**Add:**
```
├── SKILL.md
│   ├── PATH A: Absolute Beginner (5 min)
│   ├── PATH B: Real Project (15 min)
│   └── PATH C: Production API (30 min)
└── templates/
    ├── basic-api.py
    ├── create_drf_api.py        # NEW: Scaffolding script
    ├── models-template.py
    ├── serializer-template.py
    └── views-template.py
```

**Critical additions:**
- Three distinct paths for different experience levels
- Common gotchas section (10+ items)
- Scaffolding script for project generation
- Tiered settings reference (essential vs optional)

---

## 4. CONTENT GUIDELINES IMPROVEMENTS

### 4.1 Add Metadata/Frontmatter
```yaml
---
version: 1.0
last_updated: 2026-01-06
difficulty: intermediate
keywords: serializers, validation, nested-data
dependencies: djangorestframework>=3.14
---
```

### 4.2 Improve SKILL.md Template
```markdown
# Skill Name

## What You'll Learn
- [Concrete outcomes]

## Before You Start
- [Prerequisites]

## Quick Start
[Working example with imports]

## Decision Tree: When to Use What
[Detailed branching logic]

## Common Mistakes & How to Fix Them
[Anti-patterns with consequences + fixes]

## Implementation Details
[Links to reference files]

## Troubleshooting
[Common errors with solutions]
```

### 4.3 Anti-patterns Format
```markdown
### ❌ Mistake: [Name]
- **Wrong:** [Code example]
- **Why it fails:** [Consequence]
- **✅ Correct:** [Fixed code]
- **Test:** [How to verify]
```

### 4.4 Decision Trees Must Branch
```
Question 1: Do you have a Django model?
├─ No → Use basic Serializer
└─ Yes → Question 2

Question 2: Need automatic field mapping?
├─ No → Use basic Serializer
└─ Yes → Question 3
[etc.]
```

---

## 5. REVISED FILE SIZE ESTIMATES

| Skill | Original | Revised | Change |
|-------|----------|---------|--------|
| quickstart | 350 | 400 | +14% |
| serializers | 900 | 1,100 | +22% |
| views | 650 | 750 | +15% |
| authentication | 500 | 600 | +20% |
| permissions | 450 | 500 | +11% |
| testing | 550 | 1,000 | +82% |
| **advanced** | **750** | **N/A** | **SPLIT** |
| routers (NEW) | - | 300 | NEW |
| error-handling (NEW) | - | 300 | NEW |
| pagination-filtering | - | 800 | NEW |
| throttling | - | 200 | NEW |
| versioning | - | 200 | NEW |
| api-documentation | - | 500 | NEW |
| responses-rendering | - | 400 | NEW |
| validators | - | 400 | NEW |
| **TOTAL** | ~4,150 | ~7,450 | +79% |

---

## 6. DEPENDENCY MATRIX

```
quickstart
    ↓
serializers ←──────────────────┐
    ↓                          │
views ─────────────────────────┤
    ↓                          │
    ├→ routers                 │
    ├→ authentication          │
    │      ↓                   │
    │   permissions            │
    │                          │
    └→ testing ────────────────┘
           ↓
    error-handling
           ↓
    [advanced skills]
```

---

## 7. SUCCESS METRICS

1. **Tutorial Coverage:** Can complete DRF tutorials 1-6 with <2 external lookups
2. **Pattern Coverage:** >95% of common GitHub DRF patterns addressable
3. **Developer Speed:** Tasks completed ≤ time with official docs
4. **Completeness Score:** Each skill scores ≥75% on quality rubric
5. **Question Coverage:** >85% of top 50 DRF Stack Overflow questions answerable

---

## 8. IMPLEMENTATION PRIORITY

### Immediate (Week 1)
1. Restructure directory with hierarchy
2. Move auth/permissions to Phase 1
3. Split "advanced" into focused skills
4. Add routers skill

### High Priority (Week 2)
5. Expand serializers with nested-writes.md
6. Add function-based views to views skill
7. Create permission-composition.md
8. Add pytest-patterns.md to testing

### Medium Priority (Week 3)
9. Create error-handling skill
10. Create api-documentation skill
11. Add jwt-oauth-comparison.md
12. Add troubleshooting to all skills

### Lower Priority (Week 4+)
13. Create responses-rendering skill
14. Create third-party-integrations skill
15. Add scaffolding script to quickstart
16. Add validation metrics

---

## Summary of Changes

| Category | Action Items |
|----------|--------------|
| **Structure** | Remove drf- prefix, add hierarchy, split advanced |
| **New Skills** | +6-8 skills (routers, error-handling, validators, api-docs, rendering, FBV) |
| **Phase Order** | Move auth/permissions to Phase 1 |
| **Content** | Add nested-writes, permission composition, pytest, troubleshooting |
| **Guidelines** | Add frontmatter, improve decision trees, fix anti-patterns format |
| **Estimates** | Increase total from ~4,150 to ~7,450 lines (+79%) |
