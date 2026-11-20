from pathlib import Path

# 1. API client: automatically attach JWT
p = Path("frontend/src/lib/api.ts")
s = p.read_text(encoding="utf-8")
s = s.replace(
    "export interface ClientOptions { baseUrl: string; fetchImpl?: typeof fetch; timeoutMs?: number }",
    "export interface ClientOptions { baseUrl: string; fetchImpl?: typeof fetch; timeoutMs?: number; getToken?: () => string | null }"
)
s = s.replace(
    "export function createClient({ baseUrl, fetchImpl, timeoutMs = 15000 }: ClientOptions)",
    "export function createClient({ baseUrl, fetchImpl, timeoutMs = 15000, getToken }: ClientOptions)"
)
s = s.replace(
    'const headers: Record<string, string> = { Accept: "application/json" };',
    'const headers: Record<string, string> = { Accept: "application/json" };\\n    const token = getToken?.();\\n    if (token) headers.Authorization = `Bearer ${token}`;'
)
p.write_text(s, encoding="utf-8")

# 2. API endpoint: login
p = Path("frontend/src/lib/endpoints.ts")
s = p.read_text(encoding="utf-8")
needle = '  return {\\n'
if 'login: (username:' not in s:
    s = s.replace(
        needle,
        needle + '    login: (username: string, password: string) => c.request("/auth/login", raw, { method: "POST", json: { username, password } }),\\n',
        1
    )
p.write_text(s, encoding="utf-8")

# 3. Authentication context
p = Path("frontend/src/api-context.tsx")
p.write_text('''import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { createClient } from "./lib/api.ts";
import { makeApi, type Api } from "./lib/endpoints.ts";

const baseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/api/v1";
const TOKEN_KEY = "aiml01_access_token";
const USER_KEY = "aiml01_user";

function readToken() {
  try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
}
function readUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) as AuthUser : null;
  } catch { return null; }
}

export interface AuthUser { id: number; username: string; role: "admin" | "analyst" }
interface AuthContextValue {
  token: string | null;
  user: AuthUser | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  authenticated: boolean;
}
const AuthCtx = createContext<AuthContextValue | null>(null);

const defaultApi: Api = makeApi(createClient({
  baseUrl,
  getToken: readToken,
}));
const Ctx = createContext<Api>(defaultApi);

export function ApiProvider({ api, children }: { api?: Api; children: ReactNode }) {
  const [token, setToken] = useState<string | null>(readToken);
  const [user, setUser] = useState<AuthUser | null>(readUser);

  const auth = useMemo<AuthContextValue>(() => ({
    token,
    user,
    authenticated: Boolean(token && user),
    async login(username, password) {
      const result = await defaultApi.login(username, password) as {
        access_token: string;
        user: AuthUser;
      };
      if (!result.access_token || !result.user || !["admin", "analyst"].includes(result.user.role)) {
        throw new Error("Invalid login response from server.");
      }
      localStorage.setItem(TOKEN_KEY, result.access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(result.user));
      setToken(result.access_token);
      setUser(result.user);
    },
    logout() {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      setToken(null);
      setUser(null);
      window.location.hash = "/";
    },
  }), [token, user]);

  return (
    <AuthCtx.Provider value={auth}>
      <Ctx.Provider value={api ?? defaultApi}>{children}</Ctx.Provider>
    </AuthCtx.Provider>
  );
}
export const useApi = () => useContext(Ctx);
export function useAuth() {
  const value = useContext(AuthCtx);
  if (!value) throw new Error("useAuth must be used inside ApiProvider");
  return value;
}
export const API_BASE_URL = baseUrl;
''', encoding="utf-8")

# 4. Login screen
Path("frontend/src/pages/Login.tsx").write_text('''import { useState, type FormEvent } from "react";
import { useAuth } from "../api-context.tsx";
import { ApiError, NetworkError } from "../lib/api.ts";

export function Login() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(username.trim(), password);
    } catch (e) {
      setError(e instanceof ApiError
        ? e.status === 401 ? "Incorrect username or password." : e.message
        : e instanceof NetworkError ? e.message : "Login failed. Please try again.");
    } finally { setBusy(false); }
  }

  return (
    <main className="login-shell">
      <section className="login-card">
        <div className="brand"><span className="logo" /> Fraud Operations</div>
        <p className="muted small">AIML-01 · Financial Fraud Detection Platform</p>
        <h1>Sign in</h1>
        <p className="muted">Access the fraud analyst workspace.</p>
        <form onSubmit={submit} className="login-form">
          <div>
            <label htmlFor="login-username">Username</label>
            <input id="login-username" autoComplete="username" value={username}
              onChange={e => setUsername(e.target.value)} required minLength={3} maxLength={80} />
          </div>
          <div>
            <label htmlFor="login-password">Password</label>
            <input id="login-password" type="password" autoComplete="current-password"
              value={password} onChange={e => setPassword(e.target.value)}
              required minLength={8} maxLength={128} />
          </div>
          {error && <div className="banner bad" role="alert">{error}</div>}
          <button className="btn primary" type="submit" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <p className="hint">Use the account provisioned by your platform administrator.</p>
      </section>
    </main>
  );
}
''', encoding="utf-8")

print("FRONTEND JWT CLIENT, AUTH CONTEXT AND LOGIN PAGE CREATED")
