from pathlib import Path

p = Path("backend/app/db.py")
s = p.read_text(encoding="utf-8")

if "CREATE TABLE IF NOT EXISTS users" in s:
    print("RBAC database tables already present.")
    raise SystemExit(0)

sql = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin','analyst')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
    created_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT NOT NULL,
    role TEXT NOT NULL,
    action TEXT NOT NULL,
    endpoint TEXT,
    request_id TEXT,
    created_utc TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_audit_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS ix_audit_created ON audit_logs(created_utc);
"""

marker = '\n"""\n\n\ndef _now()'
if marker not in s:
    raise SystemExit("ERROR: SCHEMA insertion point not found. No changes made.")

s = s.replace(marker, "\n" + sql + marker, 1)

methods = '''
    # ------------------------------------------------------------------
    # Authentication and audit
    # ------------------------------------------------------------------

    def create_user(self, username: str, password_hash: str, role: str) -> dict:
        if role not in ("admin", "analyst"):
            raise ValueError("Invalid role")
        username = username.strip()
        if not username or len(username) > 80:
            raise ValueError("Invalid username")

        now = _now()
        with self._conn(write=True) as conn:
            cursor = conn.execute(
                """INSERT INTO users
                   (username, password_hash, role, is_active, created_utc)
                   VALUES (?, ?, ?, 1, ?)""",
                (username, password_hash, role, now),
            )
            user_id = int(cursor.lastrowid)

        return self.get_user(user_id)

    def get_user(self, user_id: int) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                """SELECT id, username, password_hash, role,
                          is_active, created_utc
                   FROM users WHERE id=?""",
                (user_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_user_by_username(self, username: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                """SELECT id, username, password_hash, role,
                          is_active, created_utc
                   FROM users WHERE username=? COLLATE NOCASE""",
                (username.strip(),),
            ).fetchone()
        return dict(row) if row else None

    def list_users(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT id, username, role, is_active, created_utc
                   FROM users ORDER BY id"""
            ).fetchall()
        return [dict(row) for row in rows]

    def record_audit(
        self, user_id: int | None, username: str, role: str,
        action: str, endpoint: str | None = None,
        request_id: str | None = None,
    ) -> None:
        with self._conn(write=True) as conn:
            conn.execute(
                """INSERT INTO audit_logs
                   (user_id, username, role, action, endpoint,
                    request_id, created_utc)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    user_id, username[:80], role[:20], action[:80],
                    endpoint[:200] if endpoint else None,
                    request_id[:100] if request_id else None,
                    _now(),
                ),
            )

'''

marker2 = "    # ------------------------------------------------------------------\n    # Writes\n"
if marker2 not in s:
    raise SystemExit("ERROR: Method insertion point not found. No changes made.")

s = s.replace(marker2, methods + marker2, 1)
p.write_text(s, encoding="utf-8")
print("DB RBAC methods and migration added.")
