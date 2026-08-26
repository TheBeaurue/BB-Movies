import sqlite3

c = sqlite3.connect(r".\backend\data\bb_movies.db")
c.row_factory = sqlite3.Row

p = c.execute(
    "SELECT id, name, profession FROM people WHERE lower(name)=lower(?)",
    ("Aamir Khan",)
).fetchone()

print("PERSON:", dict(p) if p else None)

if p:
    rows = c.execute("""
        SELECT m.title, m.year, mp.role
        FROM movies m
        JOIN movie_people mp ON mp.movie_id = m.id
        WHERE mp.person_id = ?
        ORDER BY m.year DESC
    """, (p["id"],)).fetchall()

    print("CREDITS:", len(rows))
    for r in rows[:20]:
        print("-", r["title"], r["year"], r["role"])

c.close()
