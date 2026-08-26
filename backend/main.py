from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from .db import connect,init_db,seed
from .query_engine import query

app=FastAPI(title="BB Movies API",version="2.0")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
class ChatRequest(BaseModel): message:str

@app.on_event("startup")
def startup(): init_db(); seed()

def movie_rows():
    c=connect()
    rows=c.execute("""SELECT m.id,m.title,m.year,m.director,m.rating,m.synopsis,GROUP_CONCAT(g.name, ', ') genres
                      FROM movies m LEFT JOIN movie_genres mg ON mg.movie_id=m.id
                      LEFT JOIN genres g ON g.id=mg.genre_id GROUP BY m.id ORDER BY m.year DESC""").fetchall()
    c.close(); return rows

@app.get("/api/health")
def health():
    c=connect()
    x={"status":"ok","project":"BB Movies","version":"2.0","database":"SQLite",
       "movies":c.execute("SELECT COUNT(*) FROM movies").fetchone()[0],
       "songs":c.execute("SELECT COUNT(*) FROM songs").fetchone()[0],
       "people":c.execute("SELECT COUNT(*) FROM people").fetchone()[0]}
    c.close(); return x

@app.get("/api/movies")
def movies():
    r=movie_rows(); return {"count":len(r),"movies":[dict(x) for x in r]}

@app.get("/api/songs")
def songs():
    c=connect(); r=c.execute("SELECT id,title,movie,singer,year FROM songs ORDER BY year DESC").fetchall(); c.close()
    return {"count":len(r),"songs":[dict(x) for x in r]}

@app.get("/api/people")
def people():
    c=connect(); r=c.execute("SELECT id,name,profession,biography FROM people ORDER BY name").fetchall(); c.close()
    return {"count":len(r),"people":[dict(x) for x in r]}

@app.post("/api/chat")
def chat(req:ChatRequest):
    return query(req.message)

FRONT=Path(__file__).resolve().parent.parent/"frontend"
app.mount("/assets",StaticFiles(directory=FRONT),name="assets")
@app.get("/")
def home(): return FileResponse(FRONT/"index.html")
