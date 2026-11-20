from pathlib import Path
import re

ROOT = Path(".")
SKIP = {".venv", ".venv-test", "node_modules", ".git", "__pycache__", "dist", ".pytest_cache"}

GROUPS = {
    "KAFKA / STREAMING": [
        "kafka", "producer", "consumer", "transaction replay",
        "bootstrap_servers", "KafkaConsumer", "KafkaProducer"
    ],
    "GRAPH ML / FRAUD RING": [
        "torch_geometric", "GNN", "GraphSAGE", "GCN",
        "fraud ring", "fraud_ring", "graph score", "edge_index"
    ],
    "EVIDENTLY / DRIFT": [
        "evidently", "DataDrift", "drift", "PSI",
        "retraining", "reference_data"
    ],
    "FEAST / FEATURE STORE": [
        "feast", "FeatureStore", "feature_store", "feature_repo"
    ],
    "DOCKER / KUBERNETES": [
        "docker-compose", "Dockerfile", "kubernetes",
        "apiVersion:", "kind: Deployment", "readinessProbe"
    ],
    "AUDIT / AUTH / SECURITY": [
        "record_audit", "audit_logs", "JWT", "require_role",
        "password_hash", "rate_limit", "authorization"
    ],
    "DOCUMENTATION / DEMO": [
        "architecture", "installation", "quickstart",
        "demo", "limitations", "API documentation"
    ],
}

files = []
for p in ROOT.rglob("*"):
    if not p.is_file() or any(x in SKIP for x in p.parts):
        continue
    if p.suffix.lower() in {
        ".py", ".tsx", ".ts", ".js", ".json", ".yml",
        ".yaml", ".toml", ".md", ".txt", ".ini", ".sh"
    } or p.name.lower() in {"dockerfile", "makefile"}:
        files.append(p)

print("\n========== PROJECT FEATURE AUDIT ==========")
print("Scanned files:", len(files))

for group, keywords in GROUPS.items():
    print(f"\n{'='*16} {group} {'='*16}")
    matches = []
    for p in files:
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        found = [k for k in keywords if k.lower() in content.lower()]
        if found:
            matches.append((p, found))
    if not matches:
        print("No matching implementation references found.")
    else:
        for p, found in matches[:35]:
            print(f"{p}  ->  {', '.join(found[:6])}")
        if len(matches) > 35:
            print(f"... and {len(matches)-35} more files")

print("\n========== IMPORTANT FILE INVENTORY ==========")
for folder in [
    "streaming", "ml", "monitoring", "feature_repo",
    "backend", "frontend", "deploy", "docs", "k8s", "tests"
]:
    p = ROOT / folder
    if p.exists():
        print(f"\n[{folder}]")
        for f in sorted(p.rglob("*")):
            if f.is_file() and not any(x in SKIP for x in f.parts):
                print(" ", f)

print("\n========== GIT STATUS ==========")
