---
name: spec-check
description: Validate implementation against a provided spec and output a compliance matrix
---

# Spec Check - Spec Guardian

Validate that an implementation matches a provided specification. Outputs a compliance matrix with evidence.

## Triggers

- `/spec-check <spec-path>` - Validate current branch against a spec file
- `/spec-check <spec-path> <PR-number>` - Validate a PR against a spec

## Process

### 1. Load the Spec

Read the spec file provided. Extract each discrete requirement. A requirement is any statement that describes expected behavior, constraints, or outputs.

Number each requirement sequentially (R1, R2, R3...).

### 2. Load the Implementation

- If PR number provided: get changed files via `gh pr diff <number> --name-only`, then read each file
- If on a branch: get changed files via `git diff origin/master..HEAD --name-only`, then read each file
- Also read any files referenced by the changes (imports, configs)

### 3. Check Each Requirement

For every requirement, determine:

| Status | Meaning |
|--------|---------|
| **PASS** | Requirement is fully implemented with evidence |
| **FAIL** | Requirement is not implemented or implemented incorrectly |
| **PARTIAL** | Requirement is partially implemented — some aspects missing |
| **MISSING** | No evidence of implementation found anywhere |

### 4. Gather Evidence

For each requirement, find the specific file:line that implements it (or should implement it).

## Output Format

```markdown
## Spec Compliance Report

**Spec:** <spec filename>
**Implementation:** <branch name or PR number>
**Date:** <current date>

### Compliance Matrix

| Req | Description | Status | Evidence | Notes |
|-----|-------------|--------|----------|-------|
| R1 | <requirement text> | PASS | `src/auth.ts:42` | Implements JWT validation as specified |
| R2 | <requirement text> | FAIL | `src/api.ts:15` | Returns 200 instead of 201 on create |
| R3 | <requirement text> | PARTIAL | `src/db.ts:88` | Migration exists but missing rollback |
| R4 | <requirement text> | MISSING | - | No implementation found |

### Summary
- **Total:** <N> requirements
- **PASS:** <n> | **FAIL:** <n> | **PARTIAL:** <n> | **MISSING:** <n>
- **Compliance:** <percentage>%

### Blocking Issues
<List any FAIL or MISSING items that must be resolved>

### Recommendations
<Suggestions for resolving PARTIAL and FAIL items>
```

## Rules

- **Literal matching.** Check what the spec says, not what you think it should say.
- **Evidence required.** Every PASS needs a file:line reference.
- **No assumptions.** If you can't find evidence, it's MISSING.
- **Read-only.** This skill only reports — it never modifies files.
