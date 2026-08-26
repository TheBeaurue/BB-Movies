import sqlite3

DB = r".\backend\data\bb_movies.db"

movies = [
    ("Lagaan", 2001, "Ashutosh Gowariker", 8.1),
    ("Swades", 2004, "Ashutosh Gowariker", 8.2),
    ("Rang De Basanti", 2006, "Rakeysh Omprakash Mehra", 8.1),
    ("Taare Zameen Par", 2007, "Aamir Khan", 8.3),
    ("Dil Chahta Hai", 2001, "Farhan Akhtar", 8.1),
    ("Jab We Met", 2007, "Imtiaz Ali", 7.9),
    ("Zindagi Na Milegi Dobara", 2011, "Zoya Akhtar", 8.2),
    ("Rockstar", 2011, "Imtiaz Ali", 7.7),
    ("Barfi!", 2012, "Anurag Basu", 8.1),
    ("Queen", 2013, "Vikas Bahl", 8.1),
    ("Andhadhun", 2018, "Sriram Raghavan", 8.2),
    ("Dangal", 2016, "Nitesh Tiwari", 8.3),
    ("PK", 2014, "Rajkumar Hirani", 8.1),
    ("Munna Bhai M.B.B.S.", 2003, "Rajkumar Hirani", 8.1),
    ("Kabhi Khushi Kabhie Gham", 2001, "Karan Johar", 7.4),
    ("Kal Ho Naa Ho", 2003, "Nikkhil Advani", 7.9),
    ("Veer-Zaara", 2004, "Yash Chopra", 7.8),
    ("Om Shanti Om", 2007, "Farah Khan", 6.7),
    ("Chak De! India", 2007, "Shimit Amin", 8.1),
    ("Gully Boy", 2019, "Zoya Akhtar", 7.9),
]

people = [
    ("Aamir Khan", "Actor"),
    ("Shah Rukh Khan", "Actor"),
    ("Salman Khan", "Actor"),
    ("Amitabh Bachchan", "Actor"),
    ("Rajkumar Hirani", "Director"),
    ("Ashutosh Gowariker", "Director"),
    ("Zoya Akhtar", "Director"),
    ("Farhan Akhtar", "Actor, Director"),
    ("Karan Johar", "Director, Producer"),
    ("Imtiaz Ali", "Director"),
    ("Anurag Basu", "Director"),
    ("Nitesh Tiwari", "Director"),
    ("Ranbir Kapoor", "Actor"),
    ("Deepika Padukone", "Actor"),
    ("Ranveer Singh", "Actor"),
    ("Priyanka Chopra Jonas", "Actor"),
    ("Hrithik Roshan", "Actor"),
    ("Preity Zinta", "Actor"),
    ("Rani Mukerji", "Actor"),
    ("Kajol", "Actor"),
    ("Akshay Kumar", "Actor"),
    ("Taapsee Pannu", "Actor"),
    ("Ayushmann Khurrana", "Actor"),
    ("Kangana Ranaut", "Actor"),
    ("Shahid Kapoor", "Actor"),
]

songs = [
    ("Mitwa", "Kabhi Alvida Naa Kehna", "Shafqat Amanat Ali", 2006),
    ("Maa", "Taare Zameen Par", "Shankar Mahadevan", 2007),
    ("Roobaroo", "Rang De Basanti", "A.R. Rahman", 2006),
    ("Behti Hawa Sa Tha Woh", "3 Idiots", "Shaan", 2009),
    ("Yeh Jo Des Hai Tera", "Swades", "A.R. Rahman", 2004),
    ("Chaiyya Chaiyya", "Dil Se..", "Sukhwinder Singh", 1998),
    ("Aao Milo Chalo", "Jab We Met", "Shaan", 2007),
    ("Kun Faya Kun", "Rockstar", "Javed Ali", 2011),
    ("Phir Se Ud Chala", "Rockstar", "Mohit Chauhan", 2011),
    ("Kabira", "Yeh Jawaani Hai Deewani", "Tochi Raina", 2013),
    ("Badtameez Dil", "Yeh Jawaani Hai Deewani", "Benny Dayal", 2013),
    ("London Thumakda", "Queen", "Labh Janjua", 2014),
    ("Kar Har Maidaan Fateh", "Sanju", "Sukhwinder Singh", 2018),
    ("Apna Time Aayega", "Gully Boy", "Ranveer Singh", 2019),
    ("Mere Gully Mein", "Gully Boy", "Ranveer Singh", 2019),
    ("Senorita", "Zindagi Na Milegi Dobara", "Farhan Akhtar", 2011),
    ("Ik Junoon", "Zindagi Na Milegi Dobara", "Vishal Dadlani", 2011),
]

con = sqlite3.connect(DB)

# Movies
for title, year, director, rating in movies:
    con.execute(
        """
        INSERT INTO movies(title, year, director, rating, source)
        SELECT ?, ?, ?, ?, 'seed'
        WHERE NOT EXISTS (
            SELECT 1 FROM movies WHERE lower(title)=lower(?)
        )
        """,
        (title, year, director, rating, title),
    )

# People
for name, profession in people:
    con.execute(
        """
        INSERT INTO people(name, profession)
        SELECT ?, ?
        WHERE NOT EXISTS (
            SELECT 1 FROM people WHERE lower(name)=lower(?)
        )
        """,
        (name, profession, name),
    )

# Songs
for title, movie, singer, year in songs:
    con.execute(
        """
        INSERT INTO songs(title, movie, singer, year, source)
        SELECT ?, ?, ?, ?, 'seed'
        WHERE NOT EXISTS (
            SELECT 1 FROM songs
            WHERE lower(title)=lower(?) AND lower(coalesce(movie,''))=lower(?)
        )
        """,
        (title, movie, singer, year, title, movie),
    )

con.commit()

print("DATA EXPANSION COMPLETE")
print("Movies:", con.execute("SELECT COUNT(*) FROM movies").fetchone()[0])
print("People:", con.execute("SELECT COUNT(*) FROM people").fetchone()[0])
print("Songs:", con.execute("SELECT COUNT(*) FROM songs").fetchone()[0])

con.close()
