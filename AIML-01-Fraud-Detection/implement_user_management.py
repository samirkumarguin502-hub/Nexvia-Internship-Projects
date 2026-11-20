from pathlib import Path

# 1. Add user-management API methods.
p = Path("frontend/src/lib/endpoints.ts")
s = p.read_text(encoding="utf-8-sig")

if "createUser:" not in s:
    needle = '    login: (username: string, password: string) =>'
    if needle not in s:
        raise SystemExit("Login API insertion point missing; endpoints.ts unchanged.")

    # Insert user methods immediately before health, keeping login intact.
    needle2 = '    health: (s?: Sig) =>'
    addition = '''    users: (s?: Sig) => c.request("/users", raw, sig(s)),
    createUser: (username: string, password: string, role: "admin" | "analyst") =>
      c.request("/users", raw, { method: "POST", json: { username, password, role } }),
'''
    if needle2 not in s:
        raise SystemExit("Health API insertion point missing; endpoints.ts unchanged.")
    s = s.replace(needle2, addition + needle2, 1)
    p.write_text(s, encoding="utf-8")
    print("Added users and createUser API methods.")
else:
    print("User API methods already exist.")

# 2. Create the Admin User Management page.
page = Path("frontend/src/pages/Users.tsx")
page.write_text(r'''import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useApi } from "../api-context.tsx";
import { PageHead } from "../components/PageHead.tsx";
import { Badge, Banner, Card, EmptyState } from "../components/ui.tsx";
import { describeError } from "../lib/errors.ts";

interface UserRecord {
  id: number;
  username: string;
  role: "admin" | "analyst";
  is_active: boolean;
  created_utc?: string;
}

export function Users() {
  const api = useApi();
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"admin" | "analyst">("analyst");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await api.users() as UserRecord[];
      setUsers(result);
    } catch (e) {
      setError(describeError(e).message);
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => { void loadUsers(); }, [loadUsers]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSuccess("");
    setBusy(true);
    try {
      await api.createUser(username.trim(), password, role);
      setSuccess(`Account "${username.trim()}" created successfully.`);
      setUsername("");
      setPassword("");
      setRole("analyst");
      await loadUsers();
    } catch (e) {
      setError(describeError(e).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHead
        title="User management"
        sub="Create and review platform accounts. Only administrators can access this page."
        actions={<button className="btn" onClick={() => void loadUsers()}>Refresh users</button>}
      />

      {error && <Banner tone="bad" title="Operation failed">{error}</Banner>}
      {success && <Banner tone="good" title="Account created">{success}</Banner>}

      <Card title="Create platform account">
        <form className="grid" onSubmit={submit}>
          <div>
            <label htmlFor="new-user-name">Username</label>
            <input
              id="new-user-name"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              minLength={3}
              maxLength={80}
              pattern="[A-Za-z0-9_.-]+"
              autoComplete="off"
              required
            />
            <p className="small muted">3–80 characters: letters, numbers, underscore, dot or hyphen.</p>
          </div>

          <div>
            <label htmlFor="new-user-password">Temporary password</label>
            <input
              id="new-user-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              maxLength={128}
              autoComplete="new-password"
              required
            />
            <p className="small muted">Minimum 8 characters. Share credentials securely with the account holder.</p>
          </div>

          <div>
            <label htmlFor="new-user-role">Account role</label>
            <select
              id="new-user-role"
              value={role}
              onChange={(e) => setRole(e.target.value as "admin" | "analyst")}
            >
              <option value="analyst">Analyst</option>
              <option value="admin">Administrator</option>
            </select>
          </div>

          <div>
            <button className="btn primary" type="submit" disabled={busy}>
              {busy ? "Creating account..." : "Create account"}
            </button>
          </div>
        </form>
      </Card>

      <Card title="Registered platform users">
        {loading ? <p className="muted">Loading users...</p> :
          users.length === 0 ? <EmptyState title="No users found">No accounts are registered.</EmptyState> :
          <div className="grid">
            {users.map((u) => (
              <div className="row" key={u.id} style={{ justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <strong>{u.username}</strong>
                  <div className="small muted">User ID: {u.id}</div>
                </div>
                <div className="row" style={{ alignItems: "center" }}>
                  <Badge tone={u.role === "admin" ? "good" : "neutral"}>{u.role.toUpperCase()}</Badge>
                  <Badge tone={u.is_active ? "good" : "bad"}>{u.is_active ? "Active" : "Inactive"}</Badge>
                </div>
              </div>
            ))}
          </div>
        }
      </Card>
    </>
  );
}
''', encoding="utf-8")
print("Created frontend/src/pages/Users.tsx.")

# 3. Add Users route and role-aware navigation.
p = Path("frontend/src/App.tsx")
s = p.read_text(encoding="utf-8-sig")

if 'import { Users } from "./pages/Users.tsx";' not in s:
    s = s.replace(
        'import { Transactions } from "./pages/Transactions.tsx";',
        'import { Transactions } from "./pages/Transactions.tsx";\nimport { Users } from "./pages/Users.tsx";'
    )

if 'path: "/users"' not in s:
    needle = '  { path: "/about", title: "About & limits", group: "Project", el: () => <About /> },'
    if needle not in s:
        raise SystemExit("About route insertion point missing; App.tsx not saved.")
    s = s.replace(
        needle,
        needle + '\n  { path: "/users", title: "User management", group: "Administration", el: () => <Users /> },'
    )

s = s.replace(
    '  const current = ROUTES.find((r) => r.path === route) ?? ROUTES[0]!;',
    '  const current = ROUTES.find((r) => r.path === route && (r.path !== "/users" || user?.role === "admin")) ?? ROUTES[0]!;'
)

if 'if (user?.role !== "admin" && route === "/users")' not in s:
    needle = '  useEffect(() => {\n    document.title = token && user'
    s = s.replace(
        needle,
        '''  useEffect(() => {
    if (user?.role !== "admin" && route === "/users") {
      window.location.hash = "/";
    }
  }, [route, user]);

  useEffect(() => {
    document.title = token && user'''
    )

s = s.replace(
    'ROUTES.filter((r) => r.group === g).map((r) => (',
    'ROUTES.filter((r) => r.group === g && (r.path !== "/users" || user.role === "admin")).map((r) => ('
)

p.write_text(s, encoding="utf-8")
print("Added Admin-only Users navigation and route guard.")
print("User Management implementation completed.")
