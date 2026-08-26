
from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).resolve().parent / "data" / "bb_movies.db"

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

def init_db():
    c = connect()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS movies(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT UNIQUE NOT NULL,
        original_title TEXT,
        year INTEGER,
        release_date TEXT,
        language TEXT DEFAULT 'Hindi',
        runtime_minutes INTEGER,
        director TEXT,
        producer TEXT,
        production_house TEXT,
        writer TEXT,
        cinematographer TEXT,
        music_director TEXT,
        rating REAL,
        synopsis TEXT,
        box_office TEXT,
        source TEXT,
        last_verified TEXT
    );

    CREATE TABLE IF NOT EXISTS people(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        profession TEXT,
        date_of_birth TEXT,
        biography TEXT,
        debut TEXT,
        source TEXT,
        last_verified TEXT
    );

    CREATE TABLE IF NOT EXISTS genres(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    );

    CREATE TABLE IF NOT EXISTS movie_genres(
        movie_id INTEGER NOT NULL,
        genre_id INTEGER NOT NULL,
        PRIMARY KEY(movie_id, genre_id),
        FOREIGN KEY(movie_id) REFERENCES movies(id) ON DELETE CASCADE,
        FOREIGN KEY(genre_id) REFERENCES genres(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS movie_people(
        movie_id INTEGER NOT NULL,
        person_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        character_name TEXT,
        billing_order INTEGER,
        PRIMARY KEY(movie_id, person_id, role),
        FOREIGN KEY(movie_id) REFERENCES movies(id) ON DELETE CASCADE,
        FOREIGN KEY(person_id) REFERENCES people(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS songs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT UNIQUE NOT NULL,
        movie_id INTEGER,
        singer TEXT,
        music_director TEXT,
        lyricist TEXT,
        year INTEGER,
        language TEXT DEFAULT 'Hindi',
        source TEXT,
        last_verified TEXT,
        FOREIGN KEY(movie_id) REFERENCES movies(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS song_people(
        song_id INTEGER NOT NULL,
        person_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        PRIMARY KEY(song_id, person_id, role),
        FOREIGN KEY(song_id) REFERENCES songs(id) ON DELETE CASCADE,
        FOREIGN KEY(person_id) REFERENCES people(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS awards(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        year INTEGER,
        category TEXT,
        result TEXT,
        movie_id INTEGER,
        person_id INTEGER,
        source TEXT,
        FOREIGN KEY(movie_id) REFERENCES movies(id) ON DELETE CASCADE,
        FOREIGN KEY(person_id) REFERENCES people(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_movies_title ON movies(title);
    CREATE INDEX IF NOT EXISTS idx_movies_year ON movies(year);
    CREATE INDEX IF NOT EXISTS idx_people_name ON people(name);
    CREATE INDEX IF NOT EXISTS idx_songs_title ON songs(title);
    """)
    c.commit()
    c.close()

def seed():
    init_db()
    c = connect()
    if c.execute("SELECT COUNT(*) FROM movies").fetchone()[0]:
        c.close()
        return

    movies = [
        ("3 Idiots", "3 Idiots", 2009, "2009-12-25", "Hindi", "Rajkumar Hirani",
         "Demo dataset", 8.4, "A comedy-drama about friendship, education and following one's passion."),
        ("Dangal", "Dangal", 2016, "2016-12-23", "Hindi", "Nitesh Tiwari",
         "Demo dataset", 8.3, "A sports drama centered on a father training his daughters in wrestling."),
        ("Zindagi Na Milegi Dobara", "Zindagi Na Milegi Dobara", 2011, "2011-07-15", "Hindi", "Zoya Akhtar",
         "Demo dataset", 8.2, "Three friends rediscover life and friendship during a road trip."),
        ("Dilwale Dulhania Le Jayenge", "Dilwale Dulhania Le Jayenge", 1995, "1995-10-20", "Hindi", "Aditya Chopra",
         "Demo dataset", 8.0, "A classic romantic drama about love, family and tradition.")
    ]
    for title, original, year, release, lang, director, producer, rating, synopsis in movies:
        c.execute("""INSERT INTO movies(title,original_title,year,release_date,language,director,
                     producer,rating,synopsis,source) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                  (title, original, year, release, lang, director, producer, rating, synopsis, "Demo dataset"))

    for g in ["Comedy", "Drama", "Biography", "Sport", "Romance"]:
        c.execute("INSERT INTO genres(name) VALUES(?)", (g,))

    people = [
        ("Rajkumar Hirani", "Director"), ("Nitesh Tiwari", "Director"),
        ("Zoya Akhtar", "Director"), ("Aditya Chopra", "Director"),
        ("Aamir Khan", "Actor"), ("Shah Rukh Khan", "Actor"),
        ("Kajol", "Actor"), ("Arijit Singh", "Singer")
    ]
    c.executemany("INSERT INTO people(name,profession) VALUES(?,?)", people)

    genre_map = {
        "3 Idiots": ["Comedy","Drama"],
        "Dangal": ["Biography","Drama","Sport"],
        "Zindagi Na Milegi Dobara": ["Comedy","Drama"],
        "Dilwale Dulhania Le Jayenge": ["Romance","Drama"]
    }
    for title, genres in genre_map.items():
        mid = c.execute("SELECT id FROM movies WHERE title=?", (title,)).fetchone()[0]
        for g in genres:
            gid = c.execute("SELECT id FROM genres WHERE name=?", (g,)).fetchone()[0]
            c.execute("INSERT INTO movie_genres VALUES(?,?)", (mid, gid))

    credits = [
        ("3 Idiots","Rajkumar Hirani","Director",None), ("3 Idiots","Aamir Khan","Actor","Rancho"),
        ("Dangal","Nitesh Tiwari","Director",None), ("Dangal","Aamir Khan","Actor","Mahavir Singh Phogat"),
        ("Zindagi Na Milegi Dobara","Zoya Akhtar","Director",None),
        ("Dilwale Dulhania Le Jayenge","Aditya Chopra","Director",None),
        ("Dilwale Dulhania Le Jayenge","Shah Rukh Khan","Actor","Raj"),
        ("Dilwale Dulhania Le Jayenge","Kajol","Actor","Simran")
    ]
    for title, person, role, character in credits:
        mid = c.execute("SELECT id FROM movies WHERE title=?", (title,)).fetchone()[0]
        pid = c.execute("SELECT id FROM people WHERE name=?", (person,)).fetchone()[0]
        c.execute("INSERT INTO movie_people(movie_id,person_id,role,character_name) VALUES(?,?,?,?)",
                  (mid,pid,role,character))

    songs = [
        ("Tum Hi Ho", None, "Arijit Singh", 2013),
        ("Channa Mereya", None, "Arijit Singh", 2016)
    ]
    for title, movie_id, singer, year in songs:
        c.execute("""INSERT INTO songs(title,movie_id,singer,year,source)
                     VALUES(?,?,?,?,?)""", (title,movie_id,singer,year,"Demo dataset"))
    c.commit()
    c.close()

if __name__ == "__main__":
    init_db()
    seed()
    print(DB_PATH)
