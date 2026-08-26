import re
from .db import connect

STOP = {"the","a","an","is","are","was","were","ki","ke","ka","mein","me","par","aur","and",
        "movie","movies","film","films","batao","bata","show","tell","about","wali","wale","hai",
        "hain","mujhe","do","karo","with","of","in","from","to","for"}

def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())

def extract_year_range(q):
    m = re.search(r"\b(19\d{2}|20\d{2})\s*(?:-|to|se|â€“)\s*(19\d{2}|20\d{2})\b", q)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"\b(19\d{2}|20\d{2})s\b", q)
    if m:
        y=int(m.group(1)); return y,y+9
    return None

def people(q, c):
    rows = c.execute(
        "SELECT id,name,profession FROM people ORDER BY length(name) DESC"
    ).fetchall()

    q = norm(q)

    # Prefer exact person-name matches.
    exact = [dict(r) for r in rows if norm(r["name"]) == q]
    if exact:
        return exact

    # Otherwise match the longest name contained in the query.
    matches = [dict(r) for r in rows if norm(r["name"]) in q]
    if not matches:
        return []

    max_len = max(len(norm(r["name"])) for r in matches)
    return [r for r in matches if len(norm(r["name"])) == max_len]

def genres(q, c):
    rows=c.execute("SELECT id,name FROM genres ORDER BY length(name) DESC").fetchall()
    return [dict(r) for r in rows if norm(r["name"]) in q]

def movie_lookup(q, c):
    rows=c.execute("SELECT id,title,year FROM movies ORDER BY length(title) DESC").fetchall()
    for r in rows:
        if norm(r["title"]) in q:
            return dict(r)
    return None
