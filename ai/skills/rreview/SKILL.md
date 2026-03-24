---
name: rreview
description: Code review orchestrator spawning parallel quality and systems reviewers
---

# /rreview - Code Review

Spawn parallel review agents for comprehensive code review.

## Triggers

- `/rreview` - Review current PR or diff
- `/rreview <PR-number>` - Review specific PR

## Getting the Diff

1. If PR number provided: `gh pr diff <number>`
2. If on a branch: `git diff origin/master..HEAD`
3. Otherwise: `git diff` for uncommitted changes

## Execution

Spawn **2 parallel agents** using the Agent tool:

### Agent 1: Code Quality Reviewer

```
Review this code diff for quality issues:

1. **Unnecessary complexity** - Could this be simpler?
2. **Performance** - Multiple iterations, missing memoization, N+1 queries
3. **Naming** - Are names clear and consistent?
4. **Dead code** - Anything that doesn't need to exist?
5. **Error handling** - Are errors caught and handled appropriately?
6. **Testing** - Are changes tested? Are tests meaningful?

For each finding, provide:
- File:line reference
- What the issue is
- Suggested fix (with code block)

Be direct. If code is fine, say so.
```

### Agent 2: Systems Reviewer

@gilfoyle.md

## Collecting Results

After both agents complete, present a unified review:

```markdown
## Code Review Summary

### Code Quality
[Agent 1 findings]

### Systems Review
[Agent 2 findings]

### Overall Assessment
- **Blocking issues:** <count>
- **Warnings:** <count>
- **Notes:** <count>
- **Verdict:** <APPROVE / REQUEST CHANGES / NEEDS DISCUSSION>
```

## Rules

- **Both agents get the full diff** and access to read the codebase.
- **No duplicates.** If both agents flag the same issue, deduplicate in the summary.
- **Actionable.** Every finding must have a concrete suggestion.
