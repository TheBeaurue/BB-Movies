import json
import os
import re

from .db import connect


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def extract_year_range(q):
    m = re.search(
        r"\b(19\d{2}|20\d{2})\s*(?:-|to|se|–|â€“)\s*(19\d{2}|20\d{2})\b",
        q,
    )
    if m:
        return int(m.group(1)), int(m.group(2))

    m = re.search(r"\b(19\d{2}|20\d{2})s\b", q)
    if m:
        y = int(m.group(1))
        return y, y + 9

    return None


def exact_person(name, c):
    if not name:
        return None

    row = c.execute(
        """
        SELECT id,name,profession
        FROM people
        WHERE lower(name)=lower(?)
        LIMIT 1
        """,
        (str(name).strip(),),
    ).fetchone()

    return dict(row) if row else None


def exact_movie(title, c):
    if not title:
        return None

    row = c.execute(
        """
        SELECT id,title,year
        FROM movies
        WHERE lower(title)=lower(?)
        LIMIT 1
        """,
        (str(title).strip(),),
    ).fetchone()

    return dict(row) if row else None


def exact_genre(name, c):
    if not name:
        return None

    row = c.execute(
        """
        SELECT id,name
        FROM genres
        WHERE lower(name)=lower(?)
        LIMIT 1
        """,
        (str(name).strip(),),
    ).fetchone()

    return dict(row) if row else None

GENRE_ALIASES = {
    "romantic": "Romance",
    "love": "Romance",
    "love story": "Romance",
    "romance": "Romance",
    "funny": "Comedy",
    "comedy": "Comedy",
    "scary": "Horror",
    "horror": "Horror",
    "action": "Action",
    "adventure": "Adventure",
    "animation": "Animation",
    "biography": "Biography",
    "crime": "Crime",
    "documentary": "Documentary",
    "drama": "Drama",
    "family": "Family",
    "fantasy": "Fantasy",
    "history": "History",
    "music": "Music",
    "musical": "Musical",
    "mystery": "Mystery",
    "sci-fi": "Sci-Fi",
    "science fiction": "Sci-Fi",
    "short": "Short",
    "sport": "Sport",
    "sports": "Sport",
    "thriller": "Thriller",
    "war": "War",
    "western": "Western",
}


def normalize_genre(name):
    if not name:
        return None

    cleaned = norm(name)

    return GENRE_ALIASES.get(cleaned, name.strip())

def groq_parse(user_query, c):
    """
    Groq is ONLY the language/intent parser.
    It does not provide movie data.
    """

    api_key = os.environ.get("GROQ_API_KEY")

    if not api_key:
        return None

    try:
        from groq import Groq

        client = Groq(api_key=api_key)

        prompt = f"""
You are BB, a Bollywood database query parser.

Convert the user's query into JSON ONLY.
Never answer the query yourself.
Never invent movies, people, songs, years or facts.

Allowed intents:
- person_movies
- collaboration
- movie_detail
- songs
- filtered_movies
- person_detail
- unknown

Return EXACTLY this structure:

{{
  "intent": "...",
  "people": [],
  "movie": null,
  "genre": null,
  "year_from": null,
  "year_to": null,
  "singer": null,
  "limit": 20
}}

Rules:

1. Complete person names only.
2. Never shorten a name.
3. "Aamir Khan" is NOT "Khan".
4. "Amir Khan" and "Aamir Khan" are different names.
5. "Aamir Khan ki movies" -> person_movies.
6. "Aamir Khan ki 1990s movies" ->
   person_movies + year_from 1990 + year_to 1999.
7. "Aamir Khan aur Salman Khan ki movies" ->
   collaboration + both people.
8. "Dangal ke director" ->
   movie_detail + movie Dangal.
9. "1990s ki romantic movies" ->
   filtered_movies + genre Romantic + 1990-1999.
10. "KK ke songs" ->
    songs + singer KK.
11. If uncertain, use unknown.
12. limit should normally be 20.

User query:
{user_query}
"""

        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0
        )

        text = (
            response.choices[0].message.content or ""
        ).strip()

        text = re.sub(
            r"^```json\s*",
            "",
            text,
            flags=re.I
        )

        text = re.sub(
            r"^```\s*",
            "",
            text
        )

        text = re.sub(
            r"\s*```$",
            "",
            text
        )

        data = json.loads(text)

        if not isinstance(data, dict):
            return None

        return data

    except Exception as e:
        print("Groq parser error:", e)
        return None


def run_database_query(parsed, c):
    """
    Converts Gemini's structured query into deterministic SQL.
    """

    intent = parsed.get("intent")
    people_names = parsed.get("people") or []
    movie_name = parsed.get("movie")
    genre_name = normalize_genre(parsed.get("genre"))
    singer = parsed.get("singer")

    year_from = parsed.get("year_from")
    year_to = parsed.get("year_to")

    try:
        year_from = int(year_from) if year_from is not None else None
        year_to = int(year_to) if year_to is not None else None
    except (TypeError, ValueError):
        year_from = year_to = None

    try:
        limit = int(parsed.get("limit") or 20)
    except (TypeError, ValueError):
        limit = 20

    limit = max(1, min(limit, 50))

    # ---------------------------------------------------------
    # PERSON MOVIES
    # ---------------------------------------------------------

    if intent == "person_movies" and people_names:
        person = exact_person(people_names[0], c)

        if not person:
            return None

        if year_from is not None and year_to is not None:
            rows = c.execute(
                """
                SELECT DISTINCT m.title,m.year,m.rating
                FROM movies m
                JOIN movie_people mp ON mp.movie_id=m.id
                WHERE mp.person_id=?
                  AND m.year BETWEEN ? AND ?
                ORDER BY m.year DESC
                LIMIT ?
                """,
                (
                    person["id"],
                    year_from,
                    year_to,
                    limit,
                ),
            ).fetchall()
        else:
            rows = c.execute(
                """
                SELECT DISTINCT m.title,m.year,m.rating
                FROM movies m
                JOIN movie_people mp ON mp.movie_id=m.id
                WHERE mp.person_id=?
                ORDER BY m.year DESC
                LIMIT ?
                """,
                (person["id"], limit),
            ).fetchall()

        period = (
            f" ({year_from}–{year_to})"
            if year_from is not None and year_to is not None
            else ""
        )

        if not rows:
            return {
                "intent": "person_filmography",
                "text": (
                    f"<strong>🎭 {person['name']}{period}</strong><br>"
                    "No matching movies found in BB's database."
                ),
            }

        return {
            "intent": "person_filmography",
            "text": (
                f"<strong>🎭 {person['name']}{period}</strong><br>"
                + "<br>".join(
                    f"• {r['title']} ({r['year']})"
                    for r in rows
                )
            ),
        }

    # ---------------------------------------------------------
    # COLLABORATION
    # ---------------------------------------------------------

    if intent == "collaboration" and len(people_names) >= 2:
        p1 = exact_person(people_names[0], c)
        p2 = exact_person(people_names[1], c)

        if not p1 or not p2:
            return None

        rows = c.execute(
            """
            SELECT DISTINCT m.title,m.year,m.rating
            FROM movies m
            JOIN movie_people mp1 ON mp1.movie_id=m.id
            JOIN movie_people mp2 ON mp2.movie_id=m.id
            WHERE mp1.person_id=?
              AND mp2.person_id=?
              AND (
                    ? IS NULL
                    OR m.year BETWEEN ? AND ?
                  )
            ORDER BY m.year DESC
            LIMIT ?
            """,
            (
                p1["id"],
                p2["id"],
                year_from,
                year_from,
                year_to,
                limit,
            ),
        ).fetchall()

        names = f"{p1['name']} + {p2['name']}"

        if not rows:
            return {
                "intent": "collaboration",
                "text": (
                    f"<strong>🎬 {names}</strong><br>"
                    "No matching movie found in BB's current database."
                ),
            }

        return {
            "intent": "collaboration",
            "text": (
                f"<strong>🎬 {names}</strong><br>"
                + "<br>".join(
                    f"• {r['title']} ({r['year']})"
                    for r in rows
                )
            ),
        }

    # ---------------------------------------------------------
    # MOVIE DETAIL
    # ---------------------------------------------------------

    if intent == "movie_detail" and movie_name:
        movie = exact_movie(movie_name, c)

        if not movie:
            return None

        row = c.execute(
            """
            SELECT
                m.title,
                m.year,
                m.director,
                m.rating,
                m.synopsis,
                GROUP_CONCAT(g.name, ', ') genres
            FROM movies m
            LEFT JOIN movie_genres mg
                ON mg.movie_id=m.id
            LEFT JOIN genres g
                ON g.id=mg.genre_id
            WHERE m.id=?
            GROUP BY m.id
            """,
            (movie["id"],),
        ).fetchone()

        return {
            "intent": "movie_detail",
            "text": (
                f"<strong>🎬 {row['title']}</strong><br>"
                f"{row['year']} · {row['genres'] or '—'}<br>"
                f"★ {row['rating']}<br>"
                f"Director: {row['director'] or '—'}<br>"
                f"<small>"
                f"{row['synopsis'] or 'No synopsis available.'}"
                f"</small>"
            ),
        }

    # ---------------------------------------------------------
    # FILTERED MOVIES
    # ---------------------------------------------------------

    if intent == "filtered_movies":
        clauses = []
        params = []

        if genre_name:
            genre = exact_genre(genre_name, c)

            if not genre:
                return None

            clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM movie_genres mg
                    WHERE mg.movie_id=m.id
                      AND mg.genre_id=?
                )
                """
            )
            params.append(genre["id"])

        if year_from is not None:
            clauses.append("m.year >= ?")
            params.append(year_from)

        if year_to is not None:
            clauses.append("m.year <= ?")
            params.append(year_to)

        if not clauses:
            return None

        sql = f"""
            SELECT DISTINCT m.title,m.year,m.rating
            FROM movies m
            WHERE {' AND '.join(clauses)}
            ORDER BY m.rating DESC,m.year DESC
            LIMIT ?
        """

        params.append(limit)

        rows = c.execute(sql, params).fetchall()

        label = genre_name or "Bollywood"

        period = ""
        if year_from is not None and year_to is not None:
            period = f" ({year_from}–{year_to})"

        return {
            "intent": "filtered_movies",
            "text": (
                f"<strong>🎬 {label}{period}</strong><br>"
                + (
                    "<br>".join(
                        f"• {r['title']} ({r['year']}) ★ {r['rating']}"
                        for r in rows
                    )
                    if rows
                    else "No matching movies in BB's database."
                )
            ),
        }

    # ---------------------------------------------------------
    # SONGS
    # ---------------------------------------------------------

    if intent == "songs":
        if singer:
            rows = c.execute(
                """
                SELECT title,year,music_director,lyricist
                FROM songs
                WHERE lower(singer)=lower(?)
                ORDER BY year DESC
                LIMIT ?
                """,
                (singer, limit),
            ).fetchall()
        else:
            rows = c.execute(
                """
                SELECT title,year,singer,music_director,lyricist
                FROM songs
                ORDER BY year DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        if not rows:
            return {
                "intent": "songs",
                "text": (
                    "<strong>🎵 Songs</strong><br>"
                    "No matching songs found in BB's database."
                ),
            }

        return {
            "intent": "songs",
            "text": (
                "<strong>🎵 Songs</strong><br>"
                + "<br>".join(
                    f"• {r['title']} ({r['year']})"
                    + (
                        f" — {r['singer']}"
                        if r['singer']
                        else ""
                    )
                    for r in rows
                )
            ),
        }

    return None


def query(q):
    """
    Main BB query.

    Gemini understands the user's language.
    BB's SQLite database supplies the actual facts.
    """

    original_query = (q or "").strip()

    if not original_query:
        return {
            "intent": "fallback",
            "text": "Namaste! 🎬 Ask me anything about Bollywood.",
        }

    c = connect()

    parsed = groq_parse(original_query, c)

    if parsed:
        result = run_database_query(parsed, c)

        if result:
            c.close()
            return result

    c.close()

    return {
        "intent": "fallback",
        "text": (
            "Namaste! 🎬 I couldn't find a matching result "
            "in BB's current database."
        ),
    }