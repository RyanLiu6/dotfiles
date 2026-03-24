---
name: simplify
description: Review changed code for unnecessary complexity and simplify with approval
---

# Simplify - Code Simplifier

Review recently modified files for unnecessary complexity. Language-agnostic best practices applied with surgical precision.

## Triggers

- `/simplify` - Review recently changed files
- `/simplify <file-path>` - Review a specific file

## Getting the Targets

1. If a file path is provided, use that file
2. Otherwise, find recently modified files: `git diff --name-only HEAD~1` or `git diff --name-only` for uncommitted changes
3. Read each target file in full

## Simplification Checklist

Look for these patterns and fix them:

### Flatten Nesting
- Early returns instead of nested if/else
- Guard clauses at the top of functions
- Reduce indentation depth

### Prefer Standard Library
- Replace hand-rolled utilities with stdlib equivalents
- Use built-in data structures over custom ones
- Leverage language-native patterns

### Remove Dead Code
- Unused imports, variables, functions
- Commented-out code blocks
- Unreachable branches

### Simplify Conditionals
- Collapse redundant boolean expressions
- Replace complex ternaries with if/else or early returns
- Use truthiness checks where appropriate

### Reduce Abstraction
- Inline single-use helper functions
- Remove wrapper functions that add no value
- Flatten unnecessary class hierarchies

### Tighten Scope
- Move declarations closer to usage
- Reduce variable lifetime
- Extract only when it improves readability

## Process

1. Read the target files
2. Identify simplification opportunities
3. Present each finding with before/after code blocks:

```
### Finding: <description>
**File:** path/to/file.ts:42

**Before:**
\`\`\`
<original code>
\`\`\`

**After:**
\`\`\`
<simplified code>
\`\`\`

**Why:** <brief explanation>
```

4. Ask for approval before applying any changes
5. Only apply approved changes

## Rules

- **Never change behavior.** Simplification must be semantically equivalent.
- **Show before applying.** Always present changes before making them.
- **One concern per finding.** Keep findings atomic and reviewable.
- **Skip if clean.** If the code is already simple, say so and move on.
