# Architecture Decision Records (ADRs)

This document records significant architectural decisions made during the development of Narratix.

## ADR Template

**Title:** [Short descriptive title]

**Status:** [Proposed | Accepted | Rejected | Deprecated | Superseded]

**Context:** [What is the issue we're seeing that is motivating this decision or change?]

**Decision:** [What is the change that we're proposing and/or doing?]

**Consequences:** [What becomes easier or more difficult to do because of this change?]

---

## ADR-001: Initial Project Structure

**Status:** Accepted

**Context:** Need a clear, scalable layout for the codebase from the beginning.

**Decision:** Adopt a structure with top-level `src/narratix`, `tests`, `docs`, `scripts`. Use submodules like `core`, `services`, `infrastructure`, `cli` within `src/narratix`.

**Consequences:** Clear separation of concerns. Easier navigation. Standard Python packaging practices.

--- 