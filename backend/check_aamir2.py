import sqlite3

c = sqlite3.connect(r".\backend\data\bb_movies.db")
c.row_factory = sqlite3.Row

people = c.execute(
    "SELECT id, name, profession FROM people WHERE lower(name)=lower(?)",
    ("Aamir Khan",)
).fetchall()

print("AAMIR RECORDS:", len(people))

for p in people:
    print("PERSON:", dict(p))

    rows = c.execute("""
        SELECT m.title, m.year, mp.role
        FROM movies m
        JOIN movie_people mp ON mp.movie_id = m.id
        WHERE mp.person_id = ?
        ORDER BY m.year DESC
    """, (p["id"],)).fetchall()

    print("CREDITS:", len(rows))

    for r in rows[:10]:
        print(" -", r["title"], r["year"], r["role"])

c.close()
