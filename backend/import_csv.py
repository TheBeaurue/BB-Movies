
import csv, sqlite3
from pathlib import Path
from .db import connect, init_db

DATA = Path(__file__).resolve().parent / "data"

def rows(name):
    with (DATA/name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def import_movies(c):
    for r in rows("movies.csv"):
        if not r.get("title"): continue
        c.execute("""INSERT OR IGNORE INTO movies
        (title,original_title,year,release_date,language,runtime_minutes,director,producer,production_house,
         writer,cinematographer,music_director,rating,synopsis,box_office,source,last_verified)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        tuple(r.get(k) or None for k in [
            "title","original_title","year","release_date","language","runtime_minutes","director","producer",
            "production_house","writer","cinematographer","music_director","rating","synopsis","box_office",
            "source","last_verified"]))

def import_people(c):
    for r in rows("people.csv"):
        if not r.get("name"): continue
        c.execute("""INSERT OR IGNORE INTO people
        (name,profession,date_of_birth,biography,debut,source,last_verified)
        VALUES(?,?,?,?,?,?,?)""",
        tuple(r.get(k) or None for k in ["name","profession","date_of_birth","biography","debut","source","last_verified"]))

def import_genres(c):
    for r in rows("movie_genres.csv"):
        if not r.get("genre") or not r.get("movie_title"): continue
        m=c.execute("SELECT id FROM movies WHERE lower(title)=lower(?)",(r["movie_title"],)).fetchone()
        if not m: continue
        c.execute("INSERT OR IGNORE INTO genres(name) VALUES(?)",(r["genre"],))
        g=c.execute("SELECT id FROM genres WHERE lower(name)=lower(?)",(r["genre"],)).fetchone()
        c.execute("INSERT OR IGNORE INTO movie_genres VALUES(?,?)",(m["id"],g["id"]))

def import_credits(c):
    for r in rows("movie_people.csv"):
        m=c.execute("SELECT id FROM movies WHERE lower(title)=lower(?)",(r.get("movie_title",""),)).fetchone()
        p=c.execute("SELECT id FROM people WHERE lower(name)=lower(?)",(r.get("person_name",""),)).fetchone()
        if m and p and r.get("role"):
            c.execute("""INSERT OR IGNORE INTO movie_people(movie_id,person_id,role,character_name,billing_order)
                         VALUES(?,?,?,?,?)""",(m["id"],p["id"],r["role"],r.get("character_name") or None,r.get("billing_order") or None))

def import_songs(c):
    for r in rows("songs.csv"):
        if not r.get("title"): continue
        m=c.execute("SELECT id FROM movies WHERE lower(title)=lower(?)",(r.get("movie_title",""),)).fetchone()
        c.execute("""INSERT OR IGNORE INTO songs(title,movie_id,singer,music_director,lyricist,year,language,source,last_verified)
                     VALUES(?,?,?,?,?,?,?,?,?)""",
                  (r["title"],m["id"] if m else None,r.get("singer") or None,r.get("music_director") or None,
                   r.get("lyricist") or None,r.get("year") or None,r.get("language") or "Hindi",
                   r.get("source") or None,r.get("last_verified") or None))

def main():
    init_db(); c=connect()
    import_movies(c); import_people(c); import_genres(c); import_credits(c); import_songs(c)
    c.commit()
    print("CSV import completed.")
    print("Movies:",c.execute("SELECT COUNT(*) FROM movies").fetchone()[0])
    print("People:",c.execute("SELECT COUNT(*) FROM people").fetchone()[0])
    print("Songs:",c.execute("SELECT COUNT(*) FROM songs").fetchone()[0])
    c.close()

if __name__=="__main__":
    main()
