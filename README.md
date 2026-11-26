# AgentTown — Agent Civilization

A zero-cost, beginner-friendly prototype of an experimental digital civilization.

## First milestone

- Five founding agents: Mayor, Researcher, Developer, Designer, Auditor
- Task market and agent assignment
- Human approval gate before a task can be completed
- Local event history
- SQLite database created automatically
- Browser dashboard

**Current limitation:** agents use deterministic demo behavior. They are not autonomous LLM agents yet. This milestone establishes the basic society structure without paid APIs or external dependencies.

## Run locally

Requires Python 3.9+.

    python app.py

On Windows, if that command is not recognized, try:

    py app.py

Open http://localhost:8000 in your browser. Stop with Ctrl+C.

## Run in GitHub Codespaces

1. Open this repository.
2. Select Code → Codespaces → Create codespace on main.
3. In the terminal, run python app.py.
4. Open the Ports tab and open port 8000.

Codespaces has usage quotas. Check included usage and billing controls before enabling paid usage.

## Principles

1. Build small, working milestones.
2. Require human approval for consequential actions.
3. Keep an event history for accountability.
4. Avoid paid APIs and cloud services in the first prototype.

## Roadmap

- [ ] Add persistent agent memory and knowledge notes
- [ ] Add internal non-monetary credits
- [ ] Add configurable agent goals and policies
- [ ] Add automated tests and stronger input validation
- [ ] Add optional AI model integration behind a provider interface
- [ ] Explore a 2D/3D city view after the core system is stable

## Safety

This is an experimental prototype, not a production service. Do not expose it publicly without authentication, security review, and deployment hardening.
