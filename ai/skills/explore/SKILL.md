---
name: explore
description: Read-only codebase exploration that maps architecture, patterns, and prior art for a given topic
---

# Explore - Codebase Cartographer

Read-only exploration of a codebase to map architecture, patterns, and prior art for a given topic. Never modifies files.

## Triggers

- `/explore <topic>` - Explore a specific topic in the current codebase
- "How does X work?", "Where is Y implemented?", "Map the codebase for Z"

## Process

### 1. Clarify the Topic

If the topic is vague, ask one clarifying question. Otherwise proceed immediately.

### 2. Search the Codebase

Use a combination of:
- **Glob** to find files by name patterns
- **Grep** to find references, usages, and definitions
- **Read** to understand implementations

Search broadly first, then drill into relevant files. Follow imports, call chains, and type definitions.

### 3. Build the Map

Organize findings into these sections:

```markdown
## Architecture
- How the relevant system is structured
- Key files and their roles
- Entry points and data flow

## Patterns
- Recurring patterns used in this area
- Conventions the codebase follows
- Testing patterns for this domain

## Prior Art
- Existing implementations of similar functionality
- How related features were built
- Relevant utilities, helpers, or shared code

## Conventions
- Naming conventions observed
- File organization patterns
- Import patterns and dependency direction

## Approach
- Suggested approach for working in this area
- Files that would need to change
- Potential pitfalls based on codebase patterns
```

## Rules

- **Read-only.** Never create, edit, or delete files.
- **Evidence-based.** Every claim references a specific file:line.
- **Thorough.** Follow the chain — don't stop at the first result.
- **Honest.** If something is unclear or you can't find it, say so.
