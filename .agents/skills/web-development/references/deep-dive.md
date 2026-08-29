# Architecture & Patterns Deep Dive

## Feature-First Organization

Your folder structure should tell you what the application does, not what framework it uses (**Screaming Architecture**).

```
# Anti-pattern: organization by type
src/
  components/     <- 200 files, no context
  hooks/          <- 80 files, mixed concerns
  services/       <- global grab bag
  utils/          <- graveyard of homeless functions

# Pattern: organization by feature
src/
  features/
    recipes/      <- everything for recipes lives here
    auth/         <- everything for auth lives here
  shared/         <- truly cross-cutting only
```

Each feature is self-contained. Adding a feature = adding a folder. Deleting a feature = deleting a folder.

---

## The 4-Layer Feature Structure

```
features/recipes/
  domain/
    recipe.ts              # Entity types, value objects
    recipe.repository.ts   # Repository interface (port)
    recipe.errors.ts       # Domain-specific error types

  application/
    get-recipes.use-case.ts    # Orchestrates domain logic
    save-recipe.use-case.ts    # Calls ports, returns results

  infrastructure/
    recipe-api.repository.ts   # Repository implementation (adapter)
    recipe-dto.ts              # API response shape + Zod schema
    recipe-mappers.ts          # DTO <-> Domain <-> ViewModel

  components/
    RecipeList.tsx         # Presentational — receives ViewModels
    RecipeCard.tsx         # Presentational — no data fetching
    RecipeEditorClient.tsx # Client Component — forms, interaction

  hooks/
    use-recipe-filters.ts # UI coordination only

  tests/
    get-recipes.use-case.test.ts
    recipe-mappers.test.ts
    RecipeCard.test.tsx
```

### What Goes in Each Layer

| Layer | Contains | Never contains |
|-------|----------|----------------|
| **domain/** | Entity types, value objects, business rules as pure functions, repository interfaces (ports), domain error types | Fetch calls, JSX, React imports, framework code |
| **application/** | Use cases that coordinate domain logic, call repository ports, return typed results | JSX, hooks, direct HTTP calls, UI logic |
| **infrastructure/** | Repository implementations (adapters), DTOs, mappers (DTO <-> Domain <-> ViewModel), SDK clients, localStorage | Business rules, React components |
| **components/** | Presentational components receiving ViewModels via props, Client Components for interactivity | Data fetching, business logic, direct repository calls |

---

## Ports & Adapters Code Walkthrough

### 1. Define the Port (Interface)

```tsx
// features/recipes/domain/recipe.repository.ts
import type { Recipe } from './recipe';

export interface RecipeRepository {
  list(): Promise<Recipe[]>;
  getById(id: string): Promise<Recipe | null>;
  save(recipe: Omit<Recipe, 'id' | 'createdAt' | 'updatedAt'>): Promise<Recipe>;
  delete(id: string): Promise<void>;
}
```

### 2. Implement the Adapter

```tsx
// features/recipes/infrastructure/recipe-api.repository.ts
import type { RecipeRepository } from '../domain/recipe.repository';
import { RecipeDtoSchema } from './recipe-dto';
import { toRecipe } from './recipe-mappers';
import { z } from 'zod';

export class RecipeApiRepository implements RecipeRepository {
  constructor(private readonly baseUrl = '/api') {}

  async list(): Promise<Recipe[]> {
    const res = await fetch(`${this.baseUrl}/recipes`);
    if (!res.ok) throw new Error(`Failed to fetch recipes: ${res.status}`);
    const json = await res.json();
    const dtos = z.array(RecipeDtoSchema).parse(json.items); // validate at boundary
    return dtos.map(toRecipe);
  }

  async getById(id: string): Promise<Recipe | null> {
    const res = await fetch(`${this.baseUrl}/recipes/${id}`);
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`Failed to fetch recipe: ${res.status}`);
    return toRecipe(RecipeDtoSchema.parse(await res.json()));
  }
  // save() and delete() follow the same pattern
}
```

### 3. Write the Use Case

```tsx
// features/recipes/application/get-recipes.use-case.ts
import type { RecipeRepository } from '../domain/recipe.repository';

type Dependencies = { recipeRepository: RecipeRepository };

export function makeGetRecipesUseCase({ recipeRepository }: Dependencies) {
  return {
    execute: (): Promise<Recipe[]> => recipeRepository.list(),
  };
}
```

### 4. Wire in a Page (Composition Root)

```tsx
// app/dashboard/recipes/page.tsx (Server Component)
import { RecipeApiRepository } from '@/features/recipes/infrastructure/recipe-api.repository';
import { makeGetRecipesUseCase } from '@/features/recipes/application/get-recipes.use-case';
import { toRecipeCardViewModel } from '@/features/recipes/infrastructure/recipe-mappers';
import { RecipeList } from '@/features/recipes/components/RecipeList';

export default async function RecipesPage() {
  const recipeRepository = new RecipeApiRepository();
  const getRecipes = makeGetRecipesUseCase({ recipeRepository });
  const recipes = await getRecipes.execute();
  const viewModels = recipes.map(toRecipeCardViewModel);
  return <RecipeList recipes={viewModels} />;
}
```

### Switching Adapters

When the data source changes, only `infrastructure/` is affected:

```tsx
// Same interface, different adapter
export class RecipeGraphQLRepository implements RecipeRepository { /* ... */ }
export class RecipeLocalStorageRepository implements RecipeRepository { /* ... */ }
```

Use cases, domain, and components are untouched.

### When NOT to Use This Pattern

- Simple CRUD with no business logic -- direct fetch in a Server Component is fine
- Prototypes and throwaway features -- speed over architecture
- Very small projects (3-4 features, one developer)

---

## Server vs Client Components

Every component is a **Server Component** by default in Next.js App Router.

| Use Server Components for | Use Client Components only for |
|--------------------------|-------------------------------|
| Initial data fetching | `useState`, `useEffect`, `useRef` |
| Page composition and layout | Event handlers (`onClick`, `onChange`, `onSubmit`) |
| Server-side auth checks | Rich forms with validation |
| SEO metadata | Drag and drop, modals, tooltips |
| Backend resources (DB, file system) | Browser APIs (localStorage, geolocation) |
| Heavy deps that shouldn't ship to client | Third-party client libraries (maps, charts) |

**Naming:** Use `Client` suffix for `"use client"` components: `RecipeEditorClient.tsx`.

### Pattern: Server Page + Client Island

```tsx
// app/dashboard/recipes/page.tsx — Server Component
export default async function RecipesPage() {
  const recipes = await getRecipes();
  return (
    <div>
      <h1>Recipes</h1>
      <RecipeFiltersClient />          {/* Client: interactive */}
      <RecipeList recipes={recipes} />  {/* Server: static */}
    </div>
  );
}
```

Keep the Client Component boundary as small as possible. Fetch on the server; push interactivity to leaf components.

---

## State Management Hierarchy

Escalate only when the simpler option creates pain:

1. **Component state** (`useState`) -- toggles, form inputs, UI visibility. Most state stays here.
2. **Props** -- passing data parent to child. 2-3 levels of drilling is normal.
3. **Context** -- cross-cutting concerns (theme, locale, auth user, toasts). Keep small and focused. Do NOT use as general state management.
4. **Server state** -- Server Components for read-only data. TanStack Query for client-side mutations, optimistic updates, polling.
5. **Global store** (Zustand/Redux) -- only when multiple unrelated components across features share non-server state (cart, wizard, real-time collab).

| Symptom | Actual problem | Real fix |
|---------|---------------|----------|
| "Too many props" | Components too deeply nested | Flatten tree, use composition |
| "Multiple components need this data" | Data fetched in wrong place | Lift fetch to shared parent |
| "State changes here, UI updates there" | Tight coupling | Each feature owns its state |

---

## View Models and Mappers

### The Problem

```tsx
// Bad: component depends on exact API shape
<p>{recipe.owner.first_name} {recipe.owner.last_name}</p>
<img src={recipe.main_image_url ?? '/placeholder.png'} />
```

### The Solution

```tsx
// infrastructure/recipe-mappers.ts
export type RecipeCardViewModel = {
  id: string;
  title: string;
  authorName: string;
  imageUrl: string;
  cookingTime: string;
};

export function toRecipeCardViewModel(recipe: Recipe): RecipeCardViewModel {
  return {
    id: recipe.id,
    title: recipe.title,
    authorName: recipe.authorName,
    imageUrl: recipe.imageUrl ?? '/placeholder-recipe.png',
    cookingTime: formatCookingTime(recipe.cookingTimeMinutes),
  };
}
```

Components receive stable, pre-formatted data. When the API changes, only the mapper changes.

### Mapper Chain

```
API Response (RecipeDto)
    -> toRecipe()              -> Recipe (domain entity)
    -> toRecipeCardViewModel() -> RecipeCardViewModel (component props)
```

Different components may need different ViewModels from the same entity: `RecipeCardViewModel` (list), `RecipeDetailViewModel` (detail page), `RecipeEditorViewModel` (form).

---

## Composition Patterns

### Children

```tsx
function Card({ children }: { children: React.ReactNode }) {
  return <div className="card">{children}</div>;
}
```

### Compound Components

```tsx
function Tabs({ children }: { children: React.ReactNode }) {
  const [active, setActive] = useState(0);
  return (
    <TabsContext.Provider value={{ active, setActive }}>
      {children}
    </TabsContext.Provider>
  );
}
Tabs.Tab = function Tab({ index, children }) { /* uses context */ };
Tabs.Panel = function Panel({ index, children }) { /* uses context */ };
```

### Render Props / Slots

```tsx
function DataTable<T>({ data, renderRow }: { data: T[]; renderRow: (item: T) => React.ReactNode }) {
  return <table><tbody>{data.map(renderRow)}</tbody></table>;
}
```

---

## Custom Hooks Discipline

Hooks are for **UI coordination**, not business logic.

- **Good:** local state, debounce, router sync, form coordination, media queries
- **Bad:** data transformation, auth decisions, analytics, business rules

If the logic makes sense without React, it belongs in `application/` as a use case.

---

## Right-Sizing Components

A component should have **one clear visual responsibility**.

| Problem | Example |
|---------|---------|
| Too fragmented | `ButtonLabel.tsx`, `CardHeaderTitleWrapper.tsx` -- 4 files to understand one card |
| Too monolithic | Single component that fetches, transforms, validates, navigates, and renders |
| Right-sized | `RecipeCard.tsx` (one card), `RecipeList.tsx` (maps cards), `RecipeEditorClient.tsx` (form) |

---

## Naming Conventions

| Type | Convention | Example |
|------|-----------|---------|
| Domain entities | `kebab.ts` | `recipe.ts`, `recipe.repository.ts`, `recipe.errors.ts` |
| Use cases | `kebab.use-case.ts` | `get-recipes.use-case.ts` |
| Infrastructure | `kebab.ts` | `recipe-api.repository.ts`, `recipe-dto.ts`, `recipe-mappers.ts` |
| Components | `PascalCase.tsx` | `RecipeCard.tsx`, `RecipeList.tsx` |
| Hooks | `use-kebab.ts` | `use-recipe-filters.ts` |
| Tests | mirror source | `get-recipes.use-case.test.ts`, `RecipeCard.test.tsx` |

No generic names: `utils.ts` -> `recipe-title.formatter.ts`, `helpers.ts` -> `price-display.ts`.

---

## Accessibility as Architecture

Build accessible components from the start -- it changes component interfaces.

- Use semantic HTML (`button`, `input`, `dialog`) not `div` with `onClick`
- Expose `aria-label`/`aria-labelledby` when visible text is insufficient
- Handle keyboard events (Enter/Escape/Arrow keys)
- Manage focus (auto-focus on modal open, return focus on close)

Testing Library's `getByRole` queries enforce this: components hard to query by role are usually inaccessible.

---

## When to Use `shared/`

`shared/` is for genuinely cross-cutting concerns:

- UI primitives (Button, Input, Card, Dialog)
- Environment config (`env.ts`)
- HTTP client (`fetcher.ts`)
- Test utilities (builders, mocks, custom render)
- Generic utility types

**If only two features use something, it belongs in one of them.** Move to `shared/` when three or more features need it.
