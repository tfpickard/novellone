# CONTRIBUTING PLAYBOOK

This project uses a small cast of “agents” to keep work focused and humane.  
They’re roles, not processes — one person can wear multiple hats, but the hats matter.

Start here:
- [`AGENTS.md`](./AGENTS.md)
- [`README.md`](./README.md) (product + setup)
- [`ARCHITECTURE.md`](./ARCHITECTURE.md) (system boundaries, data flow)
- `schema.prisma` and `migrations/` (data model + evolution)
- `src/` (SolidStart app, simulation core, routes, UI)

────────────────────────
◆ Working With The Agents
────────────────────────

Before making any change, pick the relevant hat(s) and read the corresponding section in `AGENTS.md`.

At minimum:

- **Product Designer**
  - Clarify: What experience is this change trying to create or improve?
  - Check the journeys in `AGENTS.md`:
    - First-time visitor
    - Returning user
  - Write or refine copy to be:
    - Playful
    - Clear
    - Minimal

- **Software Architect**
  - Confirm the change fits the described architecture:
    - SolidStart + SolidJS + SSR
    - Simulation core as a pure TypeScript library
    - Prisma + Postgres
  - Keep module boundaries clean:
    - UI vs simulation logic vs data access vs auth
  - Update `ARCHITECTURE.md` when introducing:
    - New modules or layers
    - New request/response paths
    - New real-time or cross-service integrations

- **Frontend Developer**
  - Follow the routing, layout, and component patterns already in `src/`.
  - Use Solid idioms:
    - Signals, resources, and context, not ad-hoc global state.
  - Styling:
    - Use existing Tailwind config and design tokens.
    - Respect day/night theming and responsive breakpoints.
  - Accessibility:
    - Provide keyboard access.
    - Use ARIA attributes where needed.
    - Respect reduced-motion preferences.

- **Backend Developer**
  - Put server logic in SolidStart server routes / actions.
  - Keep:
    - Clear types for inputs and responses.
    - Service-style helpers around Prisma (e.g. `createSimulation`).
  - Enforce auth and authorization as described in `AGENTS.md` and `SECURITY.md` (if present).
  - Prefer small, composable functions over sprawling handlers.

- **Database Developer**
  - Evolve the Prisma schema deliberately:
    - Design for future features but avoid speculative complexity.
  - Every schema change:
    - Has a matching migration.
    - Is reversible or at least documented with tradeoffs.
  - Add indexes for real queries, not hypothetical ones.

────────────────────────
◆ Style And Tone
────────────────────────

**Comments and docs should sound like a calm, curious human.**

- Explain intent before implementation details.
- Prefer:
  - “This does X because Y” over “Do not change”.
  - “If this feels surprising, see Z” over “TODO: fix”.
- Use lightweight headings and ASCII maps when they help:
  - Page flows
  - Data flows
  - State diagrams

Monochrome symbols are welcome:
- Use them sparingly to structure text:
  - `◆` sections
  - `→` flows
  - `∙` bullets inside lists where helpful

Avoid:
- Overly formal, academic prose.
- Overly cute or sarcastic comments.
- Jargon without a one-line translation nearby.

────────────────────────
◆ Workflow: From Idea To Commit
────────────────────────

Think in **small, verifiable steps**:

1. **Clarify the change**
   - Which agent roles are active?
   - What user behavior or system property should change?
   - How will we know it worked? (A test, a log, a visual change, etc.)

2. **Plan the surface area**
   - Identify:
     - Routes and pages affected.
     - Components to touch or create.
     - Services, models, or migrations needed.
   - Sketch a quick checklist (inline in a comment, PR description, or notes):

     ```text
     [ ] Confirm Product/UX intent
     [ ] Identify affected modules
     [ ] Implement minimal vertical slice
     [ ] Add or update tests
     [ ] Update docs (README / ARCHITECTURE / AGENTS hooks)
     ```

3. **Implement a minimal vertical slice**
   - Prefer a thin, end-to-end thread:
     - DB → server → client → interaction → persistence
   - Keep the first version simple:
     - Fewer options and flags
     - Clear defaults
     - Obvious escape hatches

4. **Test**
   - Add or update:
     - Unit tests for logic and transformations.
     - Integration tests for routes and APIs.
   - For visual changes:
     - Consider small screenshots or descriptions of expected states.

5. **Document the non-obvious**
   - When you make a decision that might surprise a future reader:
     - Leave a short comment near the code.
     - Add a note in the relevant doc file, with a heading that can be grepped.

────────────────────────
◆ Commit And Author Information
────────────────────────

All code should be committed with the following author identity:

- Name: `Tom Pickard`
- Email: `tom@pickard.dev`

For example, configure your git user locally for this repository:

```bash
git config user.name "Tom Pickard"
git config user.email "tom@pickard.dev"
```

When creating branches for your work, use  the format `{type}/{short desc}`. For example:
```bash
git branch feature/add-authenticated-control-panel
```

If you are amending or fixing up commits, keep this author information consistent.

────────────────────────
◆ Code Conventions (High-Level)
────────────────────────

- **TypeScript**
  - Prefer explicit types for public functions and exported values.
  - Keep modules focused; avoid “misc” or “utils” dumping grounds.
  - When modeling domain concepts, create small type aliases or interfaces with meaningful names.

- **Solid / Frontend**
  - Use components that accept clear, typed props and emit well-defined events/callbacks.
  - Keep business logic out of JSX where possible; extract helpers.
  - Avoid clever reactivity; make data flow easy to follow.

- **Prisma / Backend**
  - Model relationships explicitly and name them after the domain (e.g. `Simulation`, `SimulationState`).
  - Keep database access behind service functions; do not scatter raw queries.
  - Be cautious with cascading deletes and migrations that rewrite large tables.

────────────────────────
◆ When In Doubt
────────────────────────

- Re-read the relevant sections of `AGENTS.md`.
- Ask:
  - Which agent would have the strongest opinion about this change?
  - What would they care about most: UX clarity, boundaries, performance, safety?
- Prefer making one small, shippable improvement over designing a perfect system on paper.

The goal is a playful, understandable project where:
- New contributors can find their way around.
- Decisions have visible reasoning.
- The system remains flexible as the toy grows more interesting.
