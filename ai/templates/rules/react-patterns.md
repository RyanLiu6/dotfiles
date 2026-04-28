---
description: Copy to .claude/rules/ — React patterns and useEffect anti-patterns
paths:
  - "**/*.{ts,tsx,jsx}"
---

# React Patterns

Before writing or preserving any `useEffect`, ask: "Is this synchronizing with an external system?" If not, remove it.

## Derived State — Just Calculate It

If a value can be computed from props or state, it's not state.

```typescript
// BAD: effect syncing derived state
const [fullName, setFullName] = useState('');
useEffect(() => { setFullName(firstName + ' ' + lastName); }, [firstName, lastName]);

// GOOD: derive during render
const fullName = firstName + ' ' + lastName;

// GOOD: expensive? useMemo, not useEffect
const filtered = useMemo(() => expensiveFilter(items, query), [items, query]);
```

## Reset State — Use `key`, Not Effects

```typescript
// BAD: effect clears state on prop change
useEffect(() => { setComment(''); }, [userId]);

// GOOD: key forces remount
<Profile userId={userId} key={userId} />
```

## Event Logic — Keep It in Handlers

```typescript
// BAD: effect watches state set by handler
useEffect(() => { if (data) post('/api', data); }, [data]);
function handleSubmit() { setData({ name }); }

// GOOD: just do it in the handler
function handleSubmit() { post('/api', { name }); }
```

## When Effects ARE Correct

- Data fetching (prefer React Query / SWR)
- Subscriptions to external systems (prefer `useSyncExternalStore`)
- Analytics on mount
- Direct DOM manipulation (focus, scroll, measure)

## Simplification Defaults

- Clarity over cleverness — three explicit lines beat one dense expression
- No nested ternaries — use if/else, switch, or lookup objects
- No redundant abstractions — if a wrapper adds nothing, don't create it
- Remove dead code — don't comment it out
- Use existing libraries before hand-rolling
