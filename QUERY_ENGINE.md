# BB Movies V2.2 — Query Engine

BB now has a rule-based natural-language query layer before we add an AI model.

Examples it is designed to understand:
- `Aamir Khan ki movies`
- `Aamir Khan aur Rajkumar Hirani ki movies`
- `90s romantic movies`
- `1990-1999 drama movies`
- `Arijit Singh songs`
- `Dangal`

Architecture:
User → Query Engine → Entity/Filter extraction → SQLite → Response

This stage is intentionally deterministic. It makes debugging and verification easier before adding an LLM/RAG layer.
