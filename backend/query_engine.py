import json
import os
import re

from .db import connect

STOP = {
    "the", "a", "an", "is", "are", "was", "were",
    "ki", "ke", "ka", "mein", "me", "par", "aur", "and",
    "movie", "movies", "film", "films",
    "batao", "bata", "show", "tell", "about",
    "wali", "wale", "hai", "hain", "mujhe", "do", "karo",
    "with", "of", "in", "from", "to", "for",
}


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def extract_year_range(q):
    m = re.search(
        r"\b(19\d{2}|20\d{2})\s*(?:-|to|se|â€“|–)\s*(19\d{2}|20\d{2})\b",
        q,
    )
    if m:
        return int(m.group(1)), int(m.group(2))

    m = re.search(r"\b(19\d{2}|20\d{2})s\b", q)
    if m:
        y = int(m.group(1))
        return y, y + 9

    return None


def people(q, c):
    """
    Match people using word boundaries instead of substring matching.

    This prevents:
        Aamir Khan
    from accidentally matching:
        Amir Khan
    """
    rows = c.execute(
        "SELECT id,name,profession FROM people ORDER BY length(name) DESC"
    ).fetchall()

    result = []

    for r in rows:
        name = norm(r["name"])

        if not name:
            continue

        pattern = r"(?<!\w)" + re.escape(name) + r"(?!\w)"

        if re.search(pattern, q):
            result.append(dict(r))

    return result


def genres(q, c):
    rows = c.execute(
        "SELECT id,name FROM genres ORDER BY length(name) DESC"
    ).fetchall()

    result = []

    for r in rows:
        name = norm(r["name"])

        if not name:
            continue

        pattern = r"(?<!\w)" + re.escape(name) + r"(?!\w)"

        if re.search(pattern, q):
            result.append(dict(r))

    return result


def movie_lookup(q, c):
    rows = c.execute(
        "SELECT id,title,year FROM movies ORDER BY length(title) DESC"
    ).fetchall()

    for r in rows:
        title = norm(r["title"])

        if not title:
            continue

        pattern = r"(?<!\w)" + re.escape(title) + r"(?!\w)"

        if re.search(pattern, q):
            return dict(r)

    return None


def gemini_parse(original_query, c):
    """
    Optional Gemini language-understanding layer.

    Gemini does NOT provide movie data.
    It only converts natural-language input into structured intent.
    """

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        return None

    try:
        from google import genai

        client = genai.Client(api_key=api_key)

        rows = c.execute(
            "SELECT name FROM people ORDER BY length(name) DESC"
        ).fetchall()

        known_people = [r["name"] for r in rows]

        genre_rows = c.execute(
            "SELECT name FROM genres ORDER BY length(name) DESC"
        ).fetchall()

        known_genres = [r["name"] for r in genre_rows]

        prompt = f"""
You are the query parser for a Bollywood movie database.

Convert the user's query into JSON only.

Do NOT answer the user.
Do NOT invent database results.
Only identify the requested intent and entities.

Allowed intents:
- person_movies
- movie_detail
- collaboration
- songs
- filtered_movies
- unknown

JSON fields:
{{
  "intent": "...",
  "people": [],
  "movie": null,
  "genre": null,
  "year_from": null,
  "year_to": null
}}

Rules:
- Use exact person names from the supplied database list whenever possible.
- Do not confuse similar names.
- "Aamir Khan" and "Amir Khan" are different people.
- If one person is asking for their movies, use person_movies.
- If two or more people are being asked about together, use collaboration.
- "ki movies", "ke films", "ki filmein", "movie list", "filmography" can indicate person_movies.
- A decade such as 1990s means 1990 through 1999.
- If a movie title is clearly mentioned, use movie_detail when the user asks about that movie.
- If a genre/year filter is requested, use filtered_movies.
- If songs/music/gaane are requested, use songs.
- If uncertain, use unknown.

Known people:
{known_people[:3000]}

Known genres:
{known_genres}

User query:
{original_query}
"""

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
        )

        text = (response.text or "").strip()

        # Remove Markdown JSON fences if Gemini adds them.
        text = re.sub(r"^```json\s*", "", text, flags=re.I)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        data = json.loads(text)

        if not isinstance(data, dict):
            return None

        return data

    except Exception:
        # Gemini is optional. Existing rule-based engine remains fallback.
        return None


def person_movies(p, c, yr=None):
    if yr:
        rows = c.execute(
            """
            SELECT DISTINCT m.title,m.year,m.rating,mp.role
            FROM movies m
            JOIN movie_people mp ON mp.movie_id=m.id
            WHERE mp.person_id=?
              AND m.year >= ?
              AND m.year <= ?
            ORDER BY m.year DESC
            """,
            (p["id"], yr[0], yr[1]),
        ).fetchall()
    else:
        rows = c.execute(
            """
            SELECT DISTINCT m.title,m.year,m.rating,mp.role
            FROM movies m
            JOIN movie_people mp ON mp.movie_id=m.id
            WHERE mp.person_id=?
            ORDER BY m.year DESC
            """,
            (p["id"],),
        ).fetchall()

    return rows


def collaboration(p1, p2, c, yr=None):
    if yr:
        rows = c.execute(
            """
            SELECT DISTINCT m.title,m.year,m.rating
            FROM movies m
            JOIN movie_people mp1 ON mp1.movie_id=m.id
            JOIN movie_people mp2 ON mp2.movie_id=m.id
            WHERE mp1.person_id=?
              AND mp2.person_id=?
              AND m.year >= ?
              AND m.year <= ?
            ORDER BY m.year DESC
            """,
            (p1["id"], p2["id"], yr[0], yr[1]),
        ).fetchall()
    else:
        rows = c.execute(
            """
            SELECT DISTINCT m.title,m.year,m.rating
            FROM movies m
            JOIN movie_people mp1 ON mp1.movie_id=m.id
            JOIN movie_people mp2 ON mp2.movie_id=m.id
            WHERE mp1.person_id=?
              AND mp2.person_id=?
            ORDER BY m.year DESC
            """,
            (p1["id"], p2["id"]),
        ).fetchall()

    return rows


def query_rule_based(q):
    """
    Original BB query logic, improved with exact person matching.
    Used when Gemini is unavailable or cannot parse the query.
    """

    q = norm(q)
    c = connect()

    ps = people(q, c)
    gs = genres(q, c)
    yr = extract_year_range(q)

    # Two-person collaboration.
    if len(ps) >= 2:
        a, b = ps[0], ps[1]
        rows = collaboration(a, b, c, yr)

        c.close()

        names = f"{a['name']} + {b['name']}"

        if rows:
            return {
                "intent": "collaboration",
                "text": (
                    f"<strong>🎬 {names}</strong><br>"
                    + "<br>".join(
                        f"• {r['title']} ({r['year']})" for r in rows
                    )
                ),
            }

        return {
            "intent": "collaboration",
            "text": (
                f"<strong>🎬 {names}</strong><br>"
                "No matching movie found in BB's current database."
            ),
        }

    # Person filmography.
    if len(ps) == 1 and (
        any(
            x in q
            for x in [
                "movie",
                "movies",
                "film",
                "films",
                "kaam",
                "ki film",
                "ke film",
                "filme",
                "filmography",
                "career",
            ]
        )
        or yr
    ):
        p = ps[0]
        rows = person_movies(p, c, yr)

        c.close()

        period = f" ({yr[0]}–{yr[1]})" if yr else ""

        if rows:
            return {
                "intent": "person_filmography",
                "text": (
                    f"<strong>🎭 {p['name']}{period}</strong><br>"
                    + "<br>".join(
                        f"• {r['title']} ({r['year']})" for r in rows
                    )
                ),
            }

        return {
            "intent": "person_filmography",
            "text": (
                f"<strong>🎭 {p['name']}{period}</strong><br>"
                "No filmography found in the current database."
            ),
        }

    # Genre + year/range.
    if gs or yr:
        clauses = []
        params = []

        if gs:
            clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM movie_genres mg
                    JOIN genres g ON g.id=mg.genre_id
                    WHERE mg.movie_id=m.id
                      AND lower(g.name)=?
                )
                """
            )
            params.append(norm(gs[0]["name"]))

        if yr:
            clauses += ["m.year >= ?", "m.year <= ?"]
            params += [yr[0], yr[1]]

        sql = f"""
            SELECT DISTINCT m.title,m.year,m.rating
            FROM movies m
            WHERE {' AND '.join(clauses)}
            ORDER BY m.rating DESC, m.year DESC
        """

        rows = c.execute(sql, params).fetchall()
        c.close()

        label = gs[0]["name"] if gs else "Bollywood"
        period = f" ({yr[0]}–{yr[1]})" if yr else ""

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
                    else "No matching movies in the current database."
                )
            ),
        }

    # Song queries.
    if any(x in q for x in ["song", "songs", "gaana", "gane", "music", "गीत"]):
        singer = (
            ps[0]["name"]
            if ps and norm(ps[0]["profession"]) == "singer"
            else None
        )

        if singer:
            rows = c.execute(
                """
                SELECT title,year
                FROM songs
                WHERE lower(singer)=?
                ORDER BY year DESC
                """,
                (norm(singer),),
            ).fetchall()
        else:
            rows = c.execute(
                """
                SELECT title,movie_id,singer,year
                FROM songs
                ORDER BY year DESC
                """
            ).fetchall()

        c.close()

        return {
            "intent": "songs",
            "text": (
                "<strong>🎵 Songs</strong><br>"
                + (
                    "<br>".join(
                        f"• {r['title']} ({r['year']})" for r in rows
                    )
                    if rows
                    else "No matching songs in the current database."
                )
            ),
        }

    # Direct movie lookup.
    m = movie_lookup(q, c)

    if m:
        row = c.execute(
            """
            SELECT m.title,m.year,m.director,m.rating,m.synopsis,
                   GROUP_CONCAT(g.name, ', ') genres
            FROM movies m
            LEFT JOIN movie_genres mg ON mg.movie_id=m.id
            LEFT JOIN genres g ON g.id=mg.genre_id
            WHERE m.id=?
            GROUP BY m.id
            """,
            (m["id"],),
        ).fetchone()

        c.close()

        return {
            "intent": "movie_detail",
            "text": (
                f"<strong>🎬 {row['title']}</strong><br>"
                f"{row['year']} · {row['genres'] or '—'}<br>"
                f"★ {row['rating']}<br>"
                f"Director: {row['director']}<br>"
                f"<small>{row['synopsis'] or 'No synopsis available.'}</small>"
            ),
        }

    c.close()

    return {
        "intent": "fallback",
        "text": (
            "Namaste! 🎬 Try a movie name, a person + movies, "
            "two people together, a genre, a year range, or songs."
        ),
    }


def query(q):
    """
    Main BB query entry point.

    Gemini first tries to understand natural language.
    Existing deterministic BB logic remains the safety fallback.
    """

    original_query = (q or "").strip()

    if not original_query:
        return {
            "intent": "fallback",
            "text": "Namaste! 🎬 Ask me anything about Bollywood.",
        }

    c = connect()

    parsed = gemini_parse(original_query, c)

    if parsed:
        intent = parsed.get("intent")
        people_names = parsed.get("people") or []

        if not people_names and parsed.get("person"):
            people_names = [parsed.get("person")]

        year_from = parsed.get("year_from")
        year_to = parsed.get("year_to")

        yr = None

        try:
            if year_from is not None and year_to is not None:
                yr = (int(year_from), int(year_to))
        except (TypeError, ValueError):
            yr = None

        # Resolve Gemini's names against the actual database.
        resolved_people = []

        for name in people_names:
            if not name:
                continue

            exact = c.execute(
                """
                SELECT id,name,profession
                FROM people
                WHERE lower(name)=lower(?)
                LIMIT 1
                """,
                (str(name).strip(),),
            ).fetchone()

            if exact:
                resolved_people.append(dict(exact))

        # Person filmography.
        if intent == "person_movies" and len(resolved_people) >= 1:
            p = resolved_people[0]
            rows = person_movies(p, c, yr)

            c.close()

            period = f" ({yr[0]}–{yr[1]})" if yr else ""

            if rows:
                return {
                    "intent": "person_filmography",
                    "text": (
                        f"<strong>🎭 {p['name']}{period}</strong><br>"
                        + "<br>".join(
                            f"• {r['title']} ({r['year']})"
                            for r in rows
                        )
                    ),
                }

            return {
                "intent": "person_filmography",
                "text": (
                    f"<strong>🎭 {p['name']}{period}</strong><br>"
                    "No filmography found in the current database."
                ),
            }

        # Collaboration.
        if intent == "collaboration" and len(resolved_people) >= 2:
            a, b = resolved_people[0], resolved_people[1]
            rows = collaboration(a, b, c, yr)

            c.close()

            names = f"{a['name']} + {b['name']}"
            period = f" ({yr[0]}–{yr[1]})" if yr else ""

            if rows:
                return {
                    "intent": "collaboration",
                    "text": (
                        f"<strong>🎬 {names}{period}</strong><br>"
                        + "<br>".join(
                            f"• {r['title']} ({r['year']})"
                            for r in rows
                        )
                    ),
                }

            return {
                "intent": "collaboration",
                "text": (
                    f"<strong>🎬 {names}{period}</strong><br>"
                    "No matching movie found in BB's current database."
                ),
            }

    c.close()

    # Gemini unavailable/uncertain → original BB logic.
    return query_rule_based(original_query)