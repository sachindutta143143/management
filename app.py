import os
from uuid import uuid4
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"

app = Flask(__name__)

# Railway provides DATABASE_URL. Convert it to the Psycopg 3 SQLAlchemy URL.
database_url = os.environ.get("DATABASE_URL", "").strip()
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

# Local SQLite is only a development fallback. Railway should use PostgreSQL.
app.config["SQLALCHEMY_DATABASE_URI"] = database_url or f"sqlite:///{BASE_DIR / 'local_dev.db'}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True, "pool_recycle": 300}

db = SQLAlchemy(app)


class AppData(db.Model):
    __tablename__ = "app_data"
    id = db.Column(db.Integer, primary_key=True)
    data_key = db.Column(db.String(100), unique=True, nullable=False)
    payload = db.Column(db.JSON, nullable=False, default=dict)


# Dedicated PostgreSQL tables. Credit and Supply intentionally share ONE table.
class ProductListData(db.Model):
    __tablename__ = "product_list"
    id = db.Column(db.Integer, primary_key=True)
    payload = db.Column(db.JSON, nullable=False, default=dict)

class CreditSupplyRegisterData(db.Model):
    __tablename__ = "credit_supply_register"
    id = db.Column(db.Integer, primary_key=True)
    # One row stores both lists: {"credit": [...], "supply": [...]}
    payload = db.Column(db.JSON, nullable=False, default=lambda: {"credit": [], "supply": []})

class OthersRegisterData(db.Model):
    __tablename__ = "others_register"
    id = db.Column(db.Integer, primary_key=True)
    payload = db.Column(db.JSON, nullable=False, default=list)

class QuotationData(db.Model):
    __tablename__ = "quotation_data"
    id = db.Column(db.Integer, primary_key=True)
    payload = db.Column(db.JSON, nullable=False, default=dict)

class InstallmentRegisterData(db.Model):
    __tablename__ = "installment_register"
    id = db.Column(db.Integer, primary_key=True)
    payload = db.Column(db.JSON, nullable=False, default=list)

SECTION_MODELS = {
    "product_list": ProductListData,
    "others_register": OthersRegisterData,
    "quotation_data": QuotationData,
    "installment_register": InstallmentRegisterData,
}

class Customer(db.Model):
    __tablename__ = "customers"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    name = db.Column(db.String(250), nullable=False)
    mobile = db.Column(db.String(40))
    email = db.Column(db.String(250))
    gstin = db.Column(db.String(30))
    state = db.Column(db.String(100))
    city = db.Column(db.String(100))
    pincode = db.Column(db.String(15))
    address = db.Column(db.Text)


# Create tables and safely migrate old Credit/Supply data into one combined row.
with app.app_context():
    db.create_all()

    # Migrate the other modules from the legacy key/value table when needed.
    for section_key, model in SECTION_MODELS.items():
        legacy = AppData.query.filter_by(data_key=section_key).first()
        if legacy is not None and db.session.get(model, 1) is None:
            db.session.add(model(id=1, payload=legacy.payload))

    combined = db.session.get(CreditSupplyRegisterData, 1)
    if combined is None:
        # Prefer app_data as the authoritative legacy source. The earlier
        # dedicated tables may be copies of these same values, so do not add
        # both sources and accidentally duplicate records.
        old_credit = AppData.query.filter_by(data_key="credit_register").first()
        old_supply = AppData.query.filter_by(data_key="supply_register").first()

        # If a legacy app_data key is absent, fall back to the previous
        # dedicated table using SQL, without mapping it as an active model.
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        table_names = set(inspector.get_table_names())
        def legacy_table_payload(table_name):
            if table_name not in table_names:
                return []
            result = db.session.execute(text(f'SELECT payload FROM "{table_name}" WHERE id = 1')).first()
            return (result[0] if result else []) or []

        credit_payload = old_credit.payload if old_credit is not None else legacy_table_payload("credit_register")
        supply_payload = old_supply.payload if old_supply is not None else legacy_table_payload("supply_register")
        combined = CreditSupplyRegisterData(
            id=1,
            payload={
                "credit": credit_payload if isinstance(credit_payload, list) else [],
                "supply": supply_payload if isinstance(supply_payload, list) else [],
            },
        )
        db.session.add(combined)
    db.session.commit()


# IMPORTANT: Serve these standalone HTML pages as static files.
# Do NOT use render_template() here; Jinja interprets HTML/JS sequences such as {{ ... }}.
def serve_page(filename):
    return send_from_directory(str(TEMPLATE_DIR), filename)


@app.get("/")
def home():
    return serve_page("index.html")


@app.get("/product")
def product():
    return serve_page("product.html")


@app.get("/credit")
def credit():
    return serve_page("credit_register.html")


@app.get("/quotation")
def quotation():
    return serve_page("quotation.html")


@app.get("/customers")
def customers_page():
    return serve_page("customers.html")


@app.get("/installments")
def installments_page():
    return serve_page("installments.html")


@app.get("/backup")
def backup_page():
    return serve_page("backup.html")


@app.get("/others")
def others_page():
    return serve_page("others.html")


@app.get("/manifest.webmanifest")
def pwa_manifest():
    return send_from_directory(str(BASE_DIR / "static"), "manifest.webmanifest", mimetype="application/manifest+json")


@app.get("/sw.js")
def service_worker():
    response = send_from_directory(str(BASE_DIR / "static"), "sw.js", mimetype="application/javascript")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response


ALLOWED_DATA_KEYS = set(SECTION_MODELS.keys()) | {"credit_register", "supply_register", "credit_supply_register"}

@app.route("/api/data/<key>", methods=["GET", "PUT", "DELETE"])
def app_data(key):
    if key not in ALLOWED_DATA_KEYS:
        return jsonify(error="Unknown data section"), 404

    # Backward-compatible API aliases: both old URLs read/write the same row.
    if key in {"credit_register", "supply_register", "credit_supply_register"}:
        row = db.session.get(CreditSupplyRegisterData, 1)
        if row is None:
            row = CreditSupplyRegisterData(id=1, payload={"credit": [], "supply": []})
            db.session.add(row)
            db.session.commit()

        if request.method == "GET":
            if key == "credit_supply_register":
                return jsonify(row.payload or {"credit": [], "supply": []})
            part = "credit" if key == "credit_register" else "supply"
            return jsonify((row.payload or {}).get(part, []))

        if request.method == "DELETE":
            if key == "credit_supply_register":
                row.payload = {"credit": [], "supply": []}
            else:
                part = "credit" if key == "credit_register" else "supply"
                data = dict(row.payload or {})
                data[part] = []
                row.payload = data
            db.session.commit()
            return jsonify(ok=True)

        payload = request.get_json(silent=True)
        if payload is None:
            return jsonify(error="A valid JSON request body is required"), 400
        if key == "credit_supply_register":
            if not isinstance(payload, dict):
                return jsonify(error="Combined payload must be an object with credit and supply arrays"), 400
            row.payload = {"credit": payload.get("credit", []), "supply": payload.get("supply", [])}
        else:
            if not isinstance(payload, list):
                return jsonify(error="Register data must be a JSON array"), 400
            part = "credit" if key == "credit_register" else "supply"
            data = dict(row.payload or {"credit": [], "supply": []})
            data[part] = payload
            row.payload = data
        db.session.commit()
        return jsonify(ok=True)

    model = SECTION_MODELS[key]
    row = db.session.get(model, 1)
    if request.method == "GET":
        if row is not None:
            return jsonify(row.payload)
        return jsonify({} if key in {"product_list", "quotation_data"} else [])
    if request.method == "DELETE":
        if row is not None:
            db.session.delete(row)
            db.session.commit()
        return jsonify(ok=True)
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify(error="A valid JSON request body is required"), 400
    if row is None:
        row = model(id=1, payload=payload)
        db.session.add(row)
    else:
        row.payload = payload
    db.session.commit()
    return jsonify(ok=True)


def customer_json(customer):
    fields = ["id", "name", "mobile", "email", "gstin", "state", "city", "pincode", "address"]
    return {field: getattr(customer, field) for field in fields}


@app.get("/api/customers")
def customer_list():
    customers = Customer.query.order_by(Customer.name).all()
    return jsonify([customer_json(customer) for customer in customers])


@app.post("/api/customers")
def customer_create():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    if not name:
        return jsonify(error="Customer name is required"), 400

    allowed_fields = ["mobile", "email", "gstin", "state", "city", "pincode", "address"]
    customer_id = str(data.get("id") or uuid4())
    existing = db.session.get(Customer, customer_id)
    if existing is not None:
        return jsonify(customer_json(existing)), 200
    customer = Customer(id=customer_id, name=name, **{field: data.get(field) for field in allowed_fields})
    db.session.add(customer)
    db.session.commit()
    return jsonify(customer_json(customer)), 201


@app.put("/api/customers/<customer_id>")
def customer_update(customer_id):
    customer = db.session.get(Customer, customer_id)
    if customer is None:
        return jsonify(error="Customer not found"), 404

    data = request.get_json(silent=True) or {}
    for field in ["name", "mobile", "email", "gstin", "state", "city", "pincode", "address"]:
        if field in data:
            setattr(customer, field, data[field])

    if not str(customer.name or "").strip():
        return jsonify(error="Customer name is required"), 400

    db.session.commit()
    return jsonify(customer_json(customer))


@app.delete("/api/customers/<customer_id>")
def customer_delete(customer_id):
    customer = db.session.get(Customer, customer_id)
    if customer is None:
        return jsonify(error="Customer not found"), 404
    db.session.delete(customer)
    db.session.commit()
    return jsonify(ok=True)



@app.get("/api/backup/export")
def backup_export():
    """Export all server-side app data and customers as a JSON backup."""
    payload = {}
    for section_key, model in SECTION_MODELS.items():
        row = db.session.get(model, 1)
        if row is not None:
            payload[section_key] = row.payload
    combined = db.session.get(CreditSupplyRegisterData, 1)
    if combined is not None:
        payload["credit_supply_register"] = combined.payload
    legacy_rows = [
        {"id": row.id, "data_key": row.data_key, "payload": row.payload}
        for row in AppData.query.order_by(AppData.id).all()
    ]
    return jsonify({
        "created_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "app_data": payload,
        "customers": [customer_json(c) for c in Customer.query.order_by(Customer.name).all()],
        "legacy_app_data_backup": legacy_rows
    })

@app.get("/api/database/status")
def database_status():
    """Report database connectivity and the expected module tables."""
    from sqlalchemy import inspect
    db.session.execute(text("SELECT 1"))
    inspector = inspect(db.engine)
    existing = set(inspector.get_table_names())
    expected = [
        "product_list",
        "credit_supply_register",
        "installment_register",
        "others_register",
        "quotation_data",
        "customers",
        "app_data",
    ]
    return jsonify({
        "status": "ok",
        "database": "connected",
        "tables": {name: name in existing for name in expected},
    })


@app.get("/health")
def health():
    # This checks the actual database connection, not only whether Flask is running.
    db.session.execute(text("SELECT 1"))
    return jsonify(status="ok", database="connected")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
