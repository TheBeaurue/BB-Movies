
import re
from .db import connect

STOP = {"the","a","an","is","are","was","were","ki","ke","ka","mein","me","par","aur","and",
        "movie","movies","film","films","batao","bata","show","tell","about","wali","wale","hai",
        "hain","mujhe","do","karo","with","of","in","from","to","for"}

def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())

def extract_year_range(q):
    m = re.search(r"\b(19\d{2}|20\d{2})\s*(?:-|to|se|–)\s*(19\d{2}|20\d{2})\b", q)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"\b(19\d{2}|20\d{2})s\b", q)
    if m:
        y=int(m.group(1)); return y,y+9
    return None

def people(q, c):
    # Match known people in DB, longest names first.
    rows=c.execute("SELECT id,name,profession FROM people ORDER BY length(name) DESC").fetchall()
    return [dict(r) for r in rows if norm(r["name"]) in q]

def genres(q, c):
    rows=c.execute("SELECT id,name FROM genres ORDER BY length(name) DESC").fetchall()
    return [dict(r) for r in rows if norm(r["name"]) in q]

def movie_lookup(q, c):
    rows=c.execute("SELECT id,title,year FROM movies ORDER BY length(title) DESC").fetchall()
    for r in rows:
        if norm(r["title"]) in q:
            return dict(r)
    return None

def query(q):
    q=norm(q)
    c=connect()

    ps=people(q,c)
    gs=genres(q,c)
    yr=extract_year_range(q)

    # Two-person collaboration query.
    if len(ps)>=2:
        a,b=ps[0],ps[1]
        rows=c.execute("""
          SELECT DISTINCT m.title,m.year,m.rating
          FROM movies m
          JOIN movie_people mp1 ON mp1.movie_id=m.id
          JOIN movie_people mp2 ON mp2.movie_id=m.id
          WHERE mp1.person_id=? AND mp2.person_id=?
          ORDER BY m.year DESC
        """,(a["id"],b["id"])).fetchall()
        c.close()
        names=f"{a['name']} + {b['name']}"
        if rows:
            return {"intent":"collaboration","text":f"<strong>🎬 {names}</strong><br>" +
                    "<br>".join(f"• {r['title']} ({r['year']})" for r in rows)}
        return {"intent":"collaboration","text":f"<strong>🎬 {names}</strong><br>No matching movie found in BB's current database."}

    # Person filmography.
    if len(ps)==1 and any(x in q for x in ["movie","movies","film","films","films","kaam","ki film","ke film"]):
        p=ps[0]
        rows=c.execute("""
          SELECT DISTINCT m.title,m.year,m.rating,mp.role
          FROM movies m JOIN movie_people mp ON mp.movie_id=m.id
          WHERE mp.person_id=? ORDER BY m.year DESC
        """,(p["id"],)).fetchall()
        c.close()
        if rows:
            return {"intent":"person_filmography","text":f"<strong>🎭 {p['name']}</strong><br>" +
                    "<br>".join(f"• {r['title']} ({r['year']})" for r in rows)}
        return {"intent":"person_filmography","text":f"<strong>🎭 {p['name']}</strong><br>No filmography found in the current database."}

    # Genre + decade/range.
    if gs or yr:
        clauses=[]; params=[]
        if gs:
            clauses.append("EXISTS (SELECT 1 FROM movie_genres mg JOIN genres g ON g.id=mg.genre_id WHERE mg.movie_id=m.id AND lower(g.name)=?)")
            params.append(norm(gs[0]["name"]))
        if yr:
            clauses += ["m.year >= ?","m.year <= ?"]; params += [yr[0],yr[1]]
        sql=f"""SELECT DISTINCT m.title,m.year,m.rating FROM movies m
                WHERE {' AND '.join(clauses)}
                ORDER BY m.rating DESC, m.year DESC"""
        rows=c.execute(sql,params).fetchall()
        c.close()
        label = gs[0]["name"] if gs else "Bollywood"
        period = f" ({yr[0]}–{yr[1]})" if yr else ""
        return {"intent":"filtered_movies","text":f"<strong>🎬 {label}{period}</strong><br>" +
                ("<br>".join(f"• {r['title']} ({r['year']}) ★ {r['rating']}" for r in rows)
                 if rows else "No matching movies in the current database.")}

    # Song queries by singer or movie.
    if any(x in q for x in ["song","songs","gaana","gane","music"]):
        singer = ps[0]["name"] if ps and ps[0]["profession"]=="Singer" else None
        if singer:
            rows=c.execute("SELECT title,year FROM songs WHERE lower(singer)=? ORDER BY year DESC",(norm(singer),)).fetchall()
        else:
            rows=c.execute("SELECT title,movie_id,singer,year FROM songs ORDER BY year DESC").fetchall()
        c.close()
        return {"intent":"songs","text":"<strong>🎵 Songs</strong><br>" +
                ("<br>".join(f"• {r['title']} ({r['year']})" for r in rows) if rows else "No matching songs in the current database.")}

    # Direct movie lookup last.
    m=movie_lookup(q,c)
    if m:
        row=c.execute("""SELECT m.title,m.year,m.director,m.rating,m.synopsis,
                         GROUP_CONCAT(g.name, ', ') genres
                         FROM movies m LEFT JOIN movie_genres mg ON mg.movie_id=m.id
                         LEFT JOIN genres g ON g.id=mg.genre_id WHERE m.id=? GROUP BY m.id""",(m["id"],)).fetchone()
        c.close()
        return {"intent":"movie_detail","text":f"<strong>🎬 {row['title']}</strong><br>{row['year']} · {row['genres'] or '—'}<br>★ {row['rating']}<br>Director: {row['director']}<br><small>{row['synopsis'] or 'No synopsis available.'}</small>"}

    c.close()
    return {"intent":"fallback","text":"Namaste! 🎬 Try a movie name, a person + movies, two people together, a genre, a year range, or songs."}
