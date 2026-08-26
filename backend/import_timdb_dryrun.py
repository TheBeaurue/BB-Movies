import csv
from pathlib import Path

TIMDB = Path(r"C:\Users\solan\Downloads\TIMDB-master\1950-2019")

def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

movies = read_csv(TIMDB / "bollywood_full.csv")
crew = read_csv(TIMDB / "bollywood_crew.csv")
crew_data = read_csv(TIMDB / "bollywood_crew_data.csv")
writers = read_csv(TIMDB / "bollywood_writers_data.csv")

print("DRY RUN - DATABASE WILL NOT BE CHANGED")
print("--------------------------------------")
print("Movies:", len(movies))
print("Crew mappings:", len(crew))
print("Crew people:", len(crew_data))
print("Writer records:", len(writers))

genres = set()
actors = set()

for row in movies:
    for g in (row.get("genres") or "").split("|"):
        if g.strip():
            genres.add(g.strip())

    for actor in (row.get("actors") or "").split("|"):
        if actor.strip():
            actors.add(actor.strip())

print("Unique genres:", len(genres))
print("Unique actors:", len(actors))

director_links = 0
writer_links = 0

for row in crew:
    director_links += len([x for x in (row.get("directors") or "").split("|") if x])
    writer_links += len([x for x in (row.get("writers") or "").split("|") if x])

print("Director links:", director_links)
print("Writer links:", writer_links)

print()
print("TIMDB DATA READ SUCCESSFULLY")
print("No database changes were made.")
