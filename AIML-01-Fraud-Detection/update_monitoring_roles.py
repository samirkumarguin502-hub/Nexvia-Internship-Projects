from pathlib import Path

monitoring = Path("frontend/src/pages/Monitoring.tsx")
s = monitoring.read_text(encoding="utf-8-sig")

if 'import { useAuth } from "../api-context.tsx";' not in s:
    s = s.replace(
        'import { useApi } from "../api-context.tsx";',
        'import { useApi, useAuth } from "../api-context.tsx";'
    )

if "const { user } = useAuth();" not in s:
    s = s.replace(
        'export function Monitoring() {\n  const api = useApi();',
        'export function Monitoring() {\n  const api = useApi();\n  const { user } = useAuth();'
    )

s = s.replace(
    '          <RetrainPanel />',
    '''          {user?.role === "admin" ? (
            <RetrainPanel />
          ) : (
            <Banner tone="info" title="Admin access required">
              Retraining workflow is restricted to administrators. Drift monitoring and performance metrics remain available to analysts.
            </Banner>
          )}'''
)

monitoring.write_text(s, encoding="utf-8")

panel = Path("frontend/src/components/RetrainPanel.tsx")
p = panel.read_text(encoding="utf-8-sig")
p = p.replace(
    "There is no authentication yet, sotreat this panel as a local-demo control.",
    "Access is restricted to authenticated administrators. All retraining transitions are validated by the API."
)
panel.write_text(p, encoding="utf-8")

print("Monitoring role-based UI updated.")
print("Admin: retraining workflow visible.")
print("Analyst: monitoring visible; retraining workflow restricted.")
