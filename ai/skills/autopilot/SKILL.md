---
name: autopilot
description: Full orchestrated workflow from spec through build, verify, and review
---

# Autopilot - Orchestrated Workflow

Single-session orchestration from specification through implementation, verification, and review.

## Triggers

- `/autopilot` - Start interactive spec session
- `/autopilot --skip-spec <spec-path>` - Skip to explore using an existing spec

## Session Artifacts

All artifacts are stored in a session directory:
- **Claude Code:** `.claude/autopilot/sessions/<timestamp>-<slug>/`
- **OpenCode:** `.opencode/autopilot/sessions/<timestamp>-<slug>/`

Create the directory at session start. `<timestamp>` is `YYYYMMDD-HHMM`, `<slug>` is a short kebab-case name derived from the feature.

## Phases

### Phase 1: Spec

**Goal:** Produce a clear specification.

- If `--skip-spec <path>` is provided, read the spec and proceed to Phase 2
- Otherwise, interview the user:
  - Ask up to 8 focused questions to understand requirements
  - After each answer, decide: enough to proceed, or ask another question
  - Stop early if requirements are clear
- Write `spec.md` to the session directory

### Phase 2: Explore

**Goal:** Map the codebase for the task.

Spawn an explore agent (using `/explore` skill prompt) with the spec as context. The agent should:
- Identify relevant files, patterns, and prior art
- Map architecture relevant to the feature

Write `exploration.md` to the session directory.

### Phase 3: Plan

**Goal:** Create an actionable implementation plan.

Using the spec and exploration results:
- Break work into ordered workstreams
- Assign file ownership per workstream (no overlapping files)
- Define test strategy
- Identify risks and dependencies

Write `plan.md` to the session directory. Present to user for approval before proceeding.

### Phase 4: Build

**Goal:** Implement the plan.

Spawn parallel workers based on workstreams from the plan:
- Each worker owns specific files — no overlap
- Workers implement their workstream and write tests
- Also spawn QA agent (`/qa` skill) and spec-check agent (`/spec-check` skill) early so they can review as code lands

Collect results from all workers.

### Phase 5: Simplify

**Goal:** Clean up implementation.

Run `/simplify` on all files touched during the build phase. Apply only improvements that don't change behavior.

### Phase 6: Verify

**Goal:** Ensure everything works.

Run in order:
1. Type checker (if applicable)
2. Linter
3. Test suite

If any step fails, fix the issue and re-run. Repeat until all pass or report what couldn't be fixed.

### Phase 7: Review

**Goal:** Final quality check.

Spawn review agents (using `/review` skill prompt):
- Code quality reviewer
- Gilfoyle systems reviewer

If reviewers flag blocking issues, fix them and re-run Phase 6.

### Phase 8: Finish

**Goal:** Wrap up the session.

Write `final-report.md` to the session directory containing:
- What was built
- Files changed
- Test coverage
- Review results
- Any remaining concerns

**Only commit or create a PR if the user explicitly requests it.**

## Rules

- **User controls the pace.** Always pause for approval after the plan phase.
- **File ownership is strict.** No two workers modify the same file.
- **Artifacts are persistent.** Every phase writes its output to the session directory.
- **No surprise commits.** Code changes are local until the user says otherwise.
