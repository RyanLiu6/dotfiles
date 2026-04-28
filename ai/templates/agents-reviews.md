---
description: Copy to repo root as AGENTS.reviews.md — review standards for local skills and CI reviewers
---

# Review Standards

Use this file for PR review agents. It provides shared standards so local skills and CI reviewers apply the same guidance.

If this file and `AGENTS.md` conflict, `AGENTS.md` wins.

## Review Contract

- Be direct.
- If code is fine, say so plainly.
- If something needs work, call it out with a concrete suggestion.
- Reference specific `file:line` locations.
- Bias toward correctness, safety, and maintainability over style.
- Skip style nits the linter already handles.
- If rollout order, rollback steps, observability, or test coverage are not proven by the PR, call that out under **Evidence Missing** instead of assuming it is fine.
- Review the supplied PR scope as the source of truth. Do not invent a broader scope.

## Review Lanes

### 1. Code Quality

Look for:

1. **Unnecessary complexity** — code that can be deleted or simplified.
2. **Wrong abstraction level** — logic living in the wrong layer.
3. **Performance issues** — N+1s, repeated work, import-time side effects, needless loops.
4. **Existing helpers** — reuse existing patterns before inventing more code.
5. **Test gaps** — exact changed path, especially negative and boundary cases.
6. **Behavior mismatch** — names, logs, and messages that don't match what the code does.

### 2. Systems & Reliability

Look for:

1. **Blast radius** — shared components, critical paths, hot code paths, auth paths.
2. **Failure modes** — timeouts, retries, partial failure, missing cleanup.
3. **Abstraction theater** — wrappers that add nothing, interfaces with one implementation.
4. **Data flow integrity** — inputs validated at boundaries, race conditions, ordering assumptions.
5. **Rollback safety** — migrations, state mutations, schema changes that make rollback dangerous.
6. **Observability** — no clear signal that a risky change is failing beyond manual log-diving.

### 3. Security

Look for:

1. **Auth and permissions** — accidental access expansion, missing deny paths.
2. **Secret leakage** — logs, responses, fixtures, query params, raw error bodies.
3. **Input validation** — injection, XSS, command injection at system boundaries.
4. **Audit trails** — risky actions should be observable and traceable.

### 4. Repo Practices

Check compliance with documented conventions in CLAUDE.md, AGENTS.md, .claude/rules/.
If no conventions are documented, skip this lane.

## Output Format

```markdown
## PR Review Summary

### Blocking
- [finding with `path:line` and reason]

### Major
- [finding with `path:line` and reason]

### Minor
- [finding with `path:line` and reason]

### Evidence Missing
- [what the PR does not prove and why that matters]

### What Looks Good
- [brief positive notes]

## Overall Verdict
- Risk: low | medium | high
- Recommendation: SHIP IT | FIX THEN SHIP | NOPE
```
