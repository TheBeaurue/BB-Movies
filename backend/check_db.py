import sqlite3

db = r".\backend\data\bb_movies.db"

c = sqlite3.connect(db)

print("Aamir Khan:")
print(c.execute(
    "SELECT id, name, profession FROM people WHERE lower(name)=lower(?)",
    ("Aamir Khan",)
).fetchall())

print("Movies:", c.execute("SELECT COUNT(*) FROM movies").fetchone()[0])
print("Credits:", c.execute("SELECT COUNT(*) FROM movie_people").fetchone()[0])

c.close()
