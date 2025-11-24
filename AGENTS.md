# AGENTS.md

This project uses a mental model of “agents” to structure work and responsibilities. These are roles, not literal processes. A single human (Tom) may play all of them, but they describe different hats to wear.

Each agent should:
- Think in terms of small, verifiable steps.
- Use checklists to track progress.
- Document non-obvious decisions.

────────────────────────
◆ Product Designer
────────────────────────

Focus:
- Define what the product *feels* like and why it’s interesting.

Responsibilities:
- Clarify the core concept of the “useless device as a service”.
- Shape the user journeys:
  - First-time visitor: discover → play → laugh → sign up (optionally).
  - Returning user: resume simulations, explore gallery, tweak settings.
- Define key flows:
  - Create & save a simulation.
  - Share and browse public simulations.
  - Observe the auto-stabilizer vs user interaction.
- Maintain a lightweight **Product Spec** section in `README.md` or `PRODUCT.md`:
  - Problems this toy solves (for the user’s curiosity and delight).
  - Non-goals (what we explicitly choose not to do).
- Ensure UX remains playful, legible, and not cluttered with unnecessary options.

Outputs:
- Wireframe descriptions (even if prose only).
- Page maps and navigation structure.
- Copy guidelines for headings, descriptions, and microcopy.

────────────────────────
◆ Software Architect
────────────────────────

Focus:
- System boundaries, stack choices, and long-term maintainability.

Responsibilities:
- Define the high-level architecture:
  - SolidStart + SolidJS + SSR.
  - Simulation core as a pure TS library.
  - Prisma + Postgres persistent layer.
  - Auth & session layer.
- Keep **separation of concerns**:
  - UI vs simulation logic vs data access vs auth.
- Own `ARCHITECTURE.md`:
  - Module boundaries.
  - Request/response lifecycle.
  - How simulations flow from DB → server → client and back.
- Plan for:
  - Real-time features (future WebSocket integration points).
  - Multiple frontends (web, native, etc.).
- Ensure choices align with:
  - Node 22.x on Vercel.
  - Prisma 7 & Postgres constraints.

Outputs:
- Architecture diagrams (ASCII/Markdown is fine).
- Conventions for file structure and naming.
- Guidelines for adding new modules without creating tangles.

────────────────────────
◆ Frontend Developer
────────────────────────

Focus:
- SolidStart / SolidJS implementation, UI, and user experience.

Responsibilities:
- Implement:
  - Routing, layouts, and navigation.
  - Playground interface (sliders, visualization canvas, controls).
  - Gallery, profile, admin screens.
- Integrate the simulation core:
  - Efficient reactivity and rendering.
  - Smooth animations and safe update loops.
- Styling:
  - Tailwind configuration.
  - Day/night theming via CSS variables and `prefers-color-scheme`.
  - Responsive design with special care for iOS / iPadOS.
- Accessibility:
  - Keyboard navigation.
  - ARIA where needed.
  - Reasonable behavior with reduced motion.

Outputs:
- Solid components that are easy to read and reuse.
- Minimal, focused hooks for shared UI logic.
- Documentation snippets in `README.md` or `UI.md` for complex components.

────────────────────────
◆ Backend Developer
────────────────────────

Focus:
- Server-side logic, APIs, auth, and integration with the database.

Responsibilities:
- Implement SolidStart server routes / actions:
  - Auth (sign-up, sign-in, sign-out).
  - Simulation CRUD.
  - Gallery queries.
  - Admin endpoints.
- Implement robust session handling:
  - Cookie configuration.
  - Session lookup, renewal, and revocation.
- Enforce authorization:
  - Protected routes for user content.
  - Admin checks.
- Provide a clear interface between server and client:
  - Types for responses and errors.
  - High-level service functions (e.g. `createSimulation`, `listPublicSimulations`).

Outputs:
- Clean, typed server handlers.
- A small set of well-named services wrapping Prisma.
- Notes in `SECURITY.md` for important choices and tradeoffs.

────────────────────────
◆ Database Developer
────────────────────────

Focus:
- Schema design, migrations, and performance on Postgres.

Responsibilities:
- Design and evolve the Prisma schema:
  - `User`, `Session`, `Profile`, `Simulation`, `SimulationState`, `ActivityLog`, etc.
- Create safe, reversible migrations.
- Indexing:
  - Add indices for common queries (by user, by visibility, by popularity).
- Data modeling for future features:
  - Simple extension paths for collaborative sessions, ratings, or comments.
- Take into account Vercel’s serverless DB access patterns:
  - Efficient connection usage.
  - Short, well-scoped queries.

Outputs:
- `schema.prisma` with comments explaining non-obvious relations.
- Migration scripts and a short guide in `DATABASE.md` (or a section in `ARCHITECTURE.md`).
- Seed scripts for local development.

────────────────────────
◆ Test Engineer
────────────────────────

Focus:
- Verification of behavior via automated tests and guardrails.

Responsibilities:
- Set up the testing stack (e.g. Vitest).
- Write and maintain:
  - Unit tests for the simulation core:
    - Basic invariants (no NaN, bounded energy under damping, etc.).
  - Unit tests for auth utilities (hashing, validation).
  - Integration tests for key flows:
    - Sign-up / sign-in.
    - Create & load simulation.
    - Access control (prevent unauthorized access).
- Add a minimal CI pipeline (e.g. GitHub Actions) that runs:
  - Type checking.
  - Linting.
  - Tests.
- Document how to run tests and interpret failures in `README.md` or `TESTING.md`.

Outputs:
- A growing test suite focused on correctness and regressions.
- Clear error messages and sensible test naming.
- Guidance for writing new tests when new features are added.

────────────────────────
◆ New Features Designer
────────────────────────

Focus:
- Ideation and planning of future extensions and integrations.

Responsibilities:
- Maintain a **living backlog** of ideas in a Markdown file (e.g. `FUTURE.md`), including:
  - Real-time multi-user simulations (WebSockets).
  - External integrations (e.g. logging/metrics, other Tom projects, embeddable widgets).
  - Extra visualizations (3D or AR-style views).
  - Export/import of simulation configurations.
  - Public API with keys and rate limiting.
- For each idea:
  - Capture the value proposition.
  - Sketch the technical approach at a high level.
  - Identify any schema or architectural changes that might be needed.
- Ensure new ideas respect:
  - Existing architectural boundaries.
  - Performance and cost constraints.
  - The core philosophy: purposeless devices that justify themselves by existing.

Outputs:
- A curated list of feature concepts with rough sizing and dependencies.
- Notes on integration opportunities with external tools and services.
- Occasional “design spikes” (short exploratory branches or docs).

────────────────────────
Coordination Between Agents
────────────────────────

- Product Designer & Software Architect:
  - Align on which features are in scope now vs later.
- Frontend & Backend Developers:
  - Collaborate on contracts (types, endpoints, error shapes).
- Database Developer & Backend Developer:
  - Iterate together on schema changes and data access patterns.
- Test Engineer & Everyone:
  - Add tests alongside new code, not afterwards.
- New Features Designer & All:
  - Periodically review `FUTURE.md` and prune / promote ideas.

All agents share a single principle:
- **Leave the codebase kinder and clearer than you found it.**
