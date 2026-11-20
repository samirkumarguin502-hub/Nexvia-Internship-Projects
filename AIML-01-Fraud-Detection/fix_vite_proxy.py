from pathlib import Path

p = Path("frontend/vite.config.ts")
s = p.read_text(encoding="utf-8-sig")

old = 'process.env.VITE_API_PROXY ?? "http://127.0.0.1:8000"'
new = 'process.env.VITE_API_PROXY ?? "http://127.0.0.1:8001"'

if new in s:
    print("Vite proxy already points to port 8001.")
elif old in s:
    p.write_text(s.replace(old, new, 1), encoding="utf-8")
    print("Vite proxy successfully changed: 8000 -> 8001")
else:
    raise SystemExit("Expected proxy configuration not found. No changes made.")
