BB Movies V2.2 FIXED

The previous V2.2 package had a database/query mismatch:
the query engine requested movie_people.character_name, but the existing
demo database did not contain that column. That caused POST /api/chat to
return HTTP 500 and the frontend showed the misleading "Backend is not running"
message.

This fixed package:
- removes that invalid column reference
- keeps the existing database/UI
- makes the frontend display the real HTTP error if one occurs

Run from the project root:
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8003

Then open:
http://127.0.0.1:8003

Test:
Aamir Khan ki movies
Aamir Khan aur Rajkumar Hirani ki movies
3 Idiots
