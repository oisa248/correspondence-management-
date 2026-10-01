"""Creates tables and demo users. Usage: DATABASE_URL=... python scripts/seed.py"""
import os, sys
import psycopg
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.security import hash_pw

USERS = [("Record Officer", "record@demo.local", "record_officer"), ("Chief Executive", "ceo@demo.local", "ceo"),
         ("Chief Technology Officer", "cto@demo.local", "cto"), ("Chief Operating Officer", "coo@demo.local", "coo"),
         ("Chief Commercial Officer", "cco@demo.local", "cco"), ("Director", "director@demo.local", "director"),
         ("Finance Department", "finance@demo.local", "department"), ("HR Department", "hr@demo.local", "department")]
PASSWORD = "Passw0rd!"

with psycopg.connect(os.environ["DATABASE_URL"]) as c:
    c.execute(open(os.path.join(os.path.dirname(__file__), "..", "db", "schema.sql")).read())
    for name, email, role in USERS:
        c.execute("insert into users(name,email,role,password_hash) values(%s,%s,%s,%s) on conflict (email) do nothing",
                  (name, email, role, hash_pw(PASSWORD)))
print("Done. Demo password for all users:", PASSWORD)
