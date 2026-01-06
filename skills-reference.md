# Claude Skills Best Practices Reference

## Core Quality Checklist

### Description Requirements
- [ ] Specific and includes key terms
- [ ] Explains WHAT the Skill does AND WHEN to use it
- [ ] Consistent terminology throughout

### Size & Structure
- [ ] SKILL.md body under 500 lines
- [ ] Additional details in separate reference files (if needed)
- [ ] File references are one level deep (no nested references)
- [ ] Progressive disclosure used appropriately
- [ ] Reference files >100 lines have table of contents

### Content Quality
- [ ] No time-sensitive information (or in "old patterns" section)
- [ ] Examples are concrete, not abstract
- [ ] Workflows have clear steps

### Scripts & Code
- [ ] Scripts solve problems rather than punt to Claude
- [ ] Error handling is explicit and helpful
- [ ] No "voodoo constants" (all values justified)
- [ ] Required packages listed and verified
- [ ] Scripts have clear documentation
- [ ] No Windows-style paths (use forward slashes)
- [ ] Validation/verification steps for critical operations
- [ ] Feedback loops for quality-critical tasks

---

## Recommended Structure

```
skill-name/
├── SKILL.md              # Overview, points to reference files (<500 lines)
└── reference/
    ├── topic-a.md        # Detailed reference for topic A
    ├── topic-b.md        # Detailed reference for topic B
    └── examples/
        └── example.py    # Concrete code examples
```

---

## Key Patterns

### 1. Progressive Disclosure
Put high-level overview in SKILL.md, detailed information in reference files.

### 2. Plan-Validate-Execute
For complex tasks:
1. Analyze → Create plan file
2. Validate plan with script
3. Execute
4. Verify

### 3. Table of Contents
For files >100 lines, include TOC at top so Claude sees full scope.

### 4. One-Level Deep References
All reference files should link directly from SKILL.md - avoid nesting.

---

## Anti-Patterns to Avoid

1. **Nested references** - Claude may only preview nested files
2. **Abstract examples** - Use concrete, copy-paste-ready code
3. **Time-sensitive info** - Avoid unless in "old patterns" section
4. **Overly long SKILL.md** - Split into reference files
5. **Unexplained constants** - Document why values are chosen
6. **Missing error handling** - Be explicit about failure modes

---

## Description Template

```
[Skill Name]: [What it does]. Use when [specific trigger conditions].
Helps with [concrete outcomes]. Covers [key topics/features].
```

Example:
```
DRF Serializers: Creating and customizing Django REST Framework serializers.
Use when building API endpoints that need data validation and transformation.
Helps with field definitions, nested relationships, and custom validation.
Covers ModelSerializer, custom fields, and validation patterns.
```
