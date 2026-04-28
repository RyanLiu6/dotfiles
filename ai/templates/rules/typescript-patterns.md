---
description: Copy to .claude/rules/ — TypeScript patterns and type safety
paths:
  - "**/*.{ts,tsx}"
---

# TypeScript Patterns

Make illegal states unrepresentable. Let the compiler do the work.

## Derive, Don't Duplicate

If a type can be derived from a source of truth, it must be.

```typescript
// BAD: manual duplication — these will drift
type Status = 'active' | 'inactive' | 'pending';
const STATUS_OPTIONS = ['active', 'inactive', 'pending'];

// GOOD: single source of truth
const STATUS = { ACTIVE: 'active', INACTIVE: 'inactive', PENDING: 'pending' } as const;
type Status = (typeof STATUS)[keyof typeof STATUS];

// GOOD: derive from arrays
const ROLES = ['admin', 'editor', 'viewer'] as const;
type Role = (typeof ROLES)[number];

// GOOD: derive from functions
type UserData = Awaited<ReturnType<typeof fetchUser>>;
```

## `satisfies` Over Type Annotations

Annotations widen. `satisfies` validates the shape while preserving literal types.

```typescript
// BAD: annotation widens — loses literal types
const routes: Record<string, { path: string }> = { home: { path: '/' } };

// GOOD: satisfies validates but preserves literals
const routes = { home: { path: '/' } } as const satisfies Record<string, { path: string }>;
```

## Discriminated Unions Over Bags of Optionals

```typescript
// BAD: nothing stops error + data coexisting
type State = { status: string; data?: User[]; error?: string };

// GOOD: illegal states unrepresentable
type State =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: User[] }
  | { status: 'error'; error: string };
```

## Narrowing — Use What TypeScript Gives You

- **`in` operator** for object shape discrimination
- **Type predicates** (`value is T`) for reusable narrowing
- **Throw to narrow** — `if (!el) throw new Error('missing')` narrows from here on
- **Never use `as` when you can narrow** — assertions lie, narrowing proves

## Cardinal Rules

1. **Never `any`** — use `unknown` and narrow
2. **Never enums** — use `as const` objects with derived unions
3. **Never duplicate what you can derive** — `keyof typeof`, `ReturnType`, `Parameters`
4. **Never widen when you can `satisfies`** — validate without losing literals
5. **Never bag-of-optionals when you can discriminate** — model states explicitly
6. **Never `as` when you can narrow** — assertions lie, narrowing proves
