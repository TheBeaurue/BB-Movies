# BB Movies V2.2 — Query Engine

This version keeps the retro UI and SQLite database and adds a deterministic natural-language query engine.

Run:
```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8003
```

Open:
- UI: http://127.0.0.1:8003
- Health: http://127.0.0.1:8003/api/health
- Docs: http://127.0.0.1:8003/docs

Test:
- `3 Idiots`
- `Aamir Khan ki movies`
- `Aamir Khan aur Rajkumar Hirani ki movies`
- `90s romantic movies`
- `Arijit Singh songs`

Next milestone: populate verified data, then add a stronger semantic/AI layer.
