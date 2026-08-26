import csv
import sqlite3
from pathlib import Path

TIMDB = Path(r"C:\Users\solan\Downloads\TIMDB-master\1950-2019")
DB = Path(r"C:\Users\solan\Downloads\BB_Movies_V2_2_Fixed\backend\data\bb_movies.db")

def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

print("Reading TIMDB files...")

movies = read_csv(TIMDB / "bollywood_full.csv")
crew = read_csv(TIMDB / "bollywood_crew.csv")
crew_data = read_csv(TIMDB / "bollywood_crew_data.csv")

# IMDb crew ID -> person information
people_by_id = {}
for r in crew_data:
    cid = (r.get("crew_id") or "").strip()
    name = (r.get("name") or "").strip()
    profession = (r.get("profession") or "").strip()
    if cid and name:
        people_by_id[cid] = (name, profession)

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

try:
    con.execute("BEGIN")

    movie_count = 0
    person_count = 0
    genre_count = 0
    credit_count = 0
    genre_link_count = 0

    # -------------------------------------------------
    # 1. MOVIES + ACTORS + GENRES
    # -------------------------------------------------
    for r in movies:
        title = (r.get("title_x") or r.get("title_y") or "").strip()
        if not title:
            continue

        year_raw = (r.get("year_of_release") or "").strip()
        try:
            year = int(year_raw) if year_raw else None
        except ValueError:
            year = None

        rating_raw = (r.get("imdb_rating") or "").strip()
        try:
            rating = float(rating_raw) if rating_raw else None
        except ValueError:
            rating = None

        synopsis = (r.get("story") or r.get("summary") or "").strip() or None
        source = (r.get("wiki_link") or "").strip() or None
        director = None

        # Movie
        existing = con.execute(
            "SELECT id FROM movies WHERE lower(title)=lower(?) AND (year=? OR year IS NULL OR ? IS NULL)",
            (title, year, year)
        ).fetchone()

        if existing:
            movie_id = existing["id"]
        else:
            con.execute(
                """
                INSERT INTO movies
                (title, year, director, rating, synopsis, source)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (title, year, director, rating, synopsis, source)
            )
            movie_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
            movie_count += 1

        # Genres
        for genre in (r.get("genres") or "").split("|"):
            genre = genre.strip()
            if not genre:
                continue

            con.execute(
                "INSERT OR IGNORE INTO genres(name) VALUES(?)",
                (genre,)
            )

            genre_row = con.execute(
                "SELECT id FROM genres WHERE lower(name)=lower(?)",
                (genre,)
            ).fetchone()

            if genre_row:
                before = con.total_changes
                con.execute(
                    "INSERT OR IGNORE INTO movie_genres(movie_id, genre_id) VALUES(?, ?)",
                    (movie_id, genre_row["id"])
                )
                if con.total_changes > before:
                    genre_link_count += 1

        # Actors
        for actor in (r.get("actors") or "").split("|"):
            actor = actor.strip().strip(",")
            if not actor:
                continue

            con.execute(
                "INSERT OR IGNORE INTO people(name, profession) VALUES(?, ?)",
                (actor, "Actor")
            )

            person = con.execute(
                "SELECT id FROM people WHERE lower(name)=lower(?)",
                (actor,)
            ).fetchone()

            if person:
                before = con.total_changes
                con.execute(
                    """
                    INSERT OR IGNORE INTO movie_people
                    (movie_id, person_id, role)
                    VALUES (?, ?, ?)
                    """,
                    (movie_id, person["id"], "Actor")
                )
                if con.total_changes > before:
                    credit_count += 1

    # -------------------------------------------------
    # 2. DIRECTORS + WRITERS
    # -------------------------------------------------
    imdb_to_movie = {}

    for r in movies:
        imdb_id = (r.get("imdb_id") or "").strip()
        title = (r.get("title_x") or r.get("title_y") or "").strip()
        year_raw = (r.get("year_of_release") or "").strip()

        if not imdb_id or not title:
            continue

        try:
            year = int(year_raw) if year_raw else None
        except ValueError:
            year = None

        movie = con.execute(
            """
            SELECT id FROM movies
            WHERE lower(title)=lower(?) AND (year=? OR year IS NULL OR ? IS NULL)
            LIMIT 1
            """,
            (title, year, year)
        ).fetchone()

        if movie:
            imdb_to_movie[imdb_id] = movie["id"]

    for r in crew:
        imdb_id = (r.get("imdb_id") or "").strip()
        movie_id = imdb_to_movie.get(imdb_id)

        if not movie_id:
            continue

        # Directors
        for cid in (r.get("directors") or "").split("|"):
            cid = cid.strip()
            if not cid:
                continue

            person_info = people_by_id.get(cid)
            if not person_info:
                continue

            name, profession = person_info

            con.execute(
                """
                INSERT OR IGNORE INTO people(name, profession)
                VALUES (?, ?)
                """,
                (name, profession or "Director")
            )

            person = con.execute(
                "SELECT id FROM people WHERE lower(name)=lower(?) LIMIT 1",
                (name,)
            ).fetchone()

            if person:
                # Make director visible in movie's director column too.
                current = con.execute(
                    "SELECT director FROM movies WHERE id=?",
                    (movie_id,)
                ).fetchone()

                if current and not current["director"]:
                    con.execute(
                        "UPDATE movies SET director=? WHERE id=?",
                        (name, movie_id)
                    )

                before = con.total_changes
                con.execute(
                    """
                    INSERT OR IGNORE INTO movie_people
                    (movie_id, person_id, role)
                    VALUES (?, ?, ?)
                    """,
                    (movie_id, person["id"], "Director")
                )
                if con.total_changes > before:
                    credit_count += 1

        # Writers
        for cid in (r.get("writers") or "").split("|"):
            cid = cid.strip()
            if not cid:
                continue

            person_info = people_by_id.get(cid)
            if not person_info:
                continue

            name, profession = person_info

            con.execute(
                """
                INSERT OR IGNORE INTO people(name, profession)
                VALUES (?, ?)
                """,
                (name, profession or "Writer")
            )

            person = con.execute(
                "SELECT id FROM people WHERE lower(name)=lower(?) LIMIT 1",
                (name,)
            ).fetchone()

            if person:
                before = con.total_changes
                con.execute(
                    """
                    INSERT OR IGNORE INTO movie_people
                    (movie_id, person_id, role)
                    VALUES (?, ?, ?)
                    """,
                    (movie_id, person["id"], "Writer")
                )
                if con.total_changes > before:
                    credit_count += 1

    con.commit()

    print()
    print("======================================")
    print("TIMDB IMPORT COMPLETE")
    print("======================================")
    print("New movies:", movie_count)
    print("Movie-genre links:", genre_link_count)
    print("Credits added:", credit_count)
    print()
    print("TOTAL MOVIES:", con.execute("SELECT COUNT(*) FROM movies").fetchone()[0])
    print("TOTAL PEOPLE:", con.execute("SELECT COUNT(*) FROM people").fetchone()[0])
    print("TOTAL GENRES:", con.execute("SELECT COUNT(*) FROM genres").fetchone()[0])
    print("TOTAL CREDITS:", con.execute("SELECT COUNT(*) FROM movie_people").fetchone()[0])
    print("TOTAL GENRE LINKS:", con.execute("SELECT COUNT(*) FROM movie_genres").fetchone()[0])

except Exception as e:
    con.rollback()
    print()
    print("IMPORT FAILED")
    print("Database changes were rolled back.")
    print(type(e).__name__ + ":", e)
    raise

finally:
    con.close()
