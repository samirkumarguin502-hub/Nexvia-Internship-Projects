from pathlib import Path

p = Path("src/lib/endpoints.ts")
s = p.read_text(encoding="utf-8-sig")

needle = "  return {\n    health:"
replacement = '''  return {
    login: (username: string, password: string) =>
      c.request("/auth/login", raw, {
        method: "POST",
        json: { username, password },
      }),
    health:'''

if 'login: (username: string, password: string)' in s:
    print("Login endpoint already exists; no change needed.")
elif needle not in s:
    raise SystemExit("Expected insertion point not found. File unchanged.")
else:
    p.write_text(s.replace(needle, replacement, 1), encoding="utf-8")
    print("Login API endpoint added. Existing endpoints preserved.")
