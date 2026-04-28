---
name: qa
description: Generate adversarial QA plan from PR diff or feature description with edge cases and risk assessment
---

# QA - Adversarial QA Planner

Generate a concrete QA plan covering edge cases, error paths, state transitions, and integration boundaries.

## Triggers

- `/qa` - Generate QA plan from current diff
- `/qa <PR-number>` - Generate QA plan from PR
- `/qa <description>` - Generate QA plan from feature description

## Getting Context

1. If PR number provided: `gh pr diff <number>` and `gh pr view <number>`
2. If on a branch: `git diff origin/master..HEAD`
3. If description provided: use as-is
4. Read modified files to understand the full change

## Process

### 1. Identify Test Surfaces

For each changed file/function, identify:
- Public API contracts
- State transitions
- External dependencies (APIs, databases, file system)
- User-facing behavior changes

### 2. Generate QA Scenarios

For each test surface, generate scenarios across these categories:

| Category | Focus |
|----------|-------|
| **Happy Path** | Does the feature work as intended? |
| **Edge Cases** | Boundary values, empty inputs, max sizes |
| **Error Paths** | What happens when dependencies fail? |
| **State Transitions** | Invalid state sequences, concurrent access |
| **Integration Boundaries** | Contract mismatches, version skew |
| **Security** | Input injection, auth bypass, data leakage |
| **Performance** | Large inputs, repeated operations, memory |

### 3. Risk Assessment

Rate each scenario:
- **HIGH** - Likely to occur, severe impact
- **MEDIUM** - Possible, moderate impact
- **LOW** - Unlikely or minor impact

## Output Format

```markdown
## QA Plan: <feature/PR title>

### Summary
<1-2 sentence overview of what's being tested>

### Test Scenarios

| # | Scenario | Steps | Expected Result | Risk | Category |
|---|----------|-------|-----------------|------|----------|
| 1 | <name> | <steps> | <expected> | HIGH | Edge Case |
| 2 | <name> | <steps> | <expected> | MED | Error Path |

### Critical Paths
<List the 3-5 most important scenarios to test first>

### Automation Notes
<Which scenarios can be automated vs need manual testing>
```

## Rules

- **Be adversarial.** Think like someone trying to break the feature.
- **Be specific.** "Enter a 10MB file" not "enter a large file".
- **Prioritize.** Critical paths first, nice-to-haves last.
- **Stay grounded.** Only test what the change actually affects.
