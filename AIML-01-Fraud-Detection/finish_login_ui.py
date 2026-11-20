from pathlib import Path

css = Path("frontend/src/styles.css")
s = css.read_text(encoding="utf-8-sig")

# Correct an existing CSS typo without replacing the stylesheet.
s = s.replace("border-bottom: 1px solidvar(--line);",
              "border-bottom: 1px solid var(--line);")

login_css = r"""

/* Authentication screen */
.login-shell {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background:
    radial-gradient(ellipse at 15% 10%, rgba(59, 130, 246, .12), transparent 42%),
    var(--bg);
}

.login-card {
  width: min(100%, 430px);
  padding: clamp(24px, 5vw, 40px);
  border: 1px solid var(--line);
  border-radius: 18px;
  background: var(--panel);
  box-shadow: 0 24px 70px rgba(0, 0, 0, .28);
}

.login-card h1 {
  margin: 28px 0 8px;
  font-size: clamp(28px, 5vw, 36px);
  letter-spacing: -1px;
}

.login-card .brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  font-size: 17px;
}

.login-form {
  display: grid;
  gap: 18px;
  margin-top: 26px;
}

.login-form label {
  display: block;
  margin-bottom: 7px;
  font-size: 13px;
  font-weight: 600;
}

.login-form input {
  width: 100%;
  min-height: 44px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--panel-2);
  color: var(--text);
  font: inherit;
}

.login-form input:focus {
  outline: 2px solid var(--accent, #6598ff);
  outline-offset: 2px;
}

.login-form button {
  width: 100%;
  min-height: 46px;
}

.login-card .hint {
  margin: 22px 0 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 480px) {
  .login-shell { padding: 14px; }
  .login-card { padding: 24px 20px; }
}
"""

if "/* Authentication screen */" not in s:
    s += "\n" + login_css

css.write_text(s, encoding="utf-8")

login = Path("frontend/src/pages/Login.tsx")
l = login.read_text(encoding="utf-8-sig")
l = l.replace("AIML-01 Â· Financial", "AIML-01 · Financial")
l = l.replace("Signing inâ€¦", "Signing in…")
login.write_text(l, encoding="utf-8")

panel = Path("frontend/src/components/RetrainPanel.tsx")
p = panel.read_text(encoding="utf-8-sig")
p = p.replace("requested â†’ candidate trained â†’ evaluated by the server â†’ promotion decision recorded.",
              "requested → candidate trained → evaluated by the server → promotion decision recorded.")
panel.write_text(p, encoding="utf-8")

print("Login styling appended; existing dashboard CSS preserved.")
print("Login and retraining text encoding corrected.")
