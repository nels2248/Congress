import sqlite3

path = r".\MapData\Extracted\tlgpkg_2026_us_legislative.gpkg"

db = sqlite3.connect(path)

rows = db.execute("""
    SELECT table_name, data_type, identifier, description
    FROM gpkg_contents
    WHERE lower(table_name) LIKE '%congress%'
       OR lower(identifier) LIKE '%congress%'
       OR lower(description) LIKE '%congress%'
""").fetchall()

for row in rows:
    print(row)

db.close()
