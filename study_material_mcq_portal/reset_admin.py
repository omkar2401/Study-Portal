
from pathlib import Path
import sqlite3
from werkzeug.security import generate_password_hash

# Use the same folder as app.py
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "portal.db"

print("Database path:", DB_PATH)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Check whether the users table exists
table = conn.execute("""
    SELECT name FROM sqlite_master
    WHERE type = 'table' AND name = 'users'
""").fetchone()

if not table:
    conn.close()
    print("ERROR: The users table does not exist in this database.")
    print("Please run: python app.py")
    print("Then stop Flask with Ctrl+C and run this script again.")
    raise SystemExit(1)

admin = conn.execute(
    "SELECT id FROM users WHERE role = 'admin' LIMIT 1"
).fetchone()

new_password = generate_password_hash("Admin123!")

if admin:
    conn.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (new_password, admin["id"])
    )
    print("Admin password reset successfully.")
else:
    conn.execute(
        """INSERT INTO users
        (username, email, password_hash, role, created_at)
        VALUES (?, ?, ?, 'admin', datetime('now'))""",
        ("admin", "admin@example.com", new_password)
    )
    print("Admin account created successfully.")

conn.commit()
conn.close()

print("Username: admin")
print("Password: Admin123!")
