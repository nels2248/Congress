import sqlite3

path = r".\MapData\Extracted\tlgpkg_2026_us_legislative.gpkg"

db = sqlite3.connect(path)

rows = db.execute("""
    PRAGMA table_info("Congressional Districts")
""").fetchall()

for row in rows:
    print(row)

db.close()
