"""
Safe local API test for Multi Plaza.
Uses a temporary SQLite database and never connects to Railway PostgreSQL.
Run from this folder with: python test_database.py
"""
import os
import sys
import tempfile
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent
tmp = tempfile.TemporaryDirectory(prefix="multi_plaza_test_")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(tmp.name) / "test.sqlite")

# Load the Flask app only after setting the temporary database URL.
spec = importlib.util.spec_from_file_location("multi_plaza_test_app", ROOT / "app.py")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

client = module.app.test_client()
results = []

def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append((name, condition, detail))
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))

# Register modules: PUT -> GET must return exactly the submitted data.
cases = [
    ("installment_register", [{"id": "test-i-1", "name": "Test Installment", "total": 12000}]),
    ("others_register", [{"date": "2026-11-17", "customer": "Test Other", "amount": "500"}]),
    ("quotation_data", {"controls": {"test": True}, "items": [{"description": "Test item"}]}),
    ("product_list", {"html": "<table><tr><td>Test Product</td></tr></table>"}),
]
for key, payload in cases:
    put = client.put(f"/api/data/{key}", json=payload)
    get = client.get(f"/api/data/{key}")
    check(key, put.status_code == 200 and get.status_code == 200 and get.get_json() == payload,
          f"PUT={put.status_code}, GET={get.status_code}")

# Customer create then read.
created = client.post("/api/customers", json={"name": "Test Customer", "mobile": "1234567890"})
customer_ok = created.status_code == 201 and bool(created.get_json().get("id"))
listed = client.get("/api/customers")
check("customers", customer_ok and listed.status_code == 200 and
      any(c.get("name") == "Test Customer" for c in listed.get_json()),
      f"POST={created.status_code}, GET={listed.status_code}")

# Backup and database diagnostics.
backup = client.get("/api/backup/export")
check("backup export", backup.status_code == 200 and "legacy_app_data_backup" in backup.get_json(),
      f"HTTP={backup.status_code}")
diag = client.get("/api/database/status")
diag_json = diag.get_json() or {}
check("database status", diag.status_code == 200 and diag_json.get("database") == "connected",
      f"HTTP={diag.status_code}")

failed = [name for name, ok, _ in results if not ok]
print("\\nSummary:", len(results) - len(failed), "passed,", len(failed), "failed")
# Close SQLAlchemy's SQLite connections before Windows removes the temp folder.
try:
    with module.app.app_context():
        module.db.session.remove()
        module.db.engine.dispose()
finally:
    tmp.cleanup()

sys.exit(1 if failed else 0)
