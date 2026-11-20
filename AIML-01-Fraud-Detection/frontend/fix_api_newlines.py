from pathlib import Path

p = Path("src/lib/api.ts")
s = p.read_text(encoding="utf-8-sig")

bad = r'''    const headers: Record<string, string> = { Accept: "application/json" };\n    const token = getToken?.();\n    if (token) headers.Authorization = `Bearer ${token}`;'''

good = '''    const headers: Record<string, string> = { Accept: "application/json" };
    const token = getToken?.();
    if (token) headers.Authorization = `Bearer ${token}`;'''

if bad not in s:
    print("Exact injected text not found. No changes made.")
else:
    p.write_text(s.replace(bad, good, 1), encoding="utf-8")
    print("Fixed literal newline characters in api.ts.")
