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


# Create tables when the app starts. A database connection problem is visible in deploy logs.
with app.app_context():
    db.create_all()


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


ALLOWED_DATA_KEYS = {
    "product_list",
    "supply_register",
    "quotation_data",
    "settings",
    "others_register",
}


@app.route("/api/data/<key>", methods=["GET", "PUT", "DELETE"])
def app_data(key):
    if key not in ALLOWED_DATA_KEYS:
        return jsonify(error="Unknown data section"), 404

    row = AppData.query.filter_by(data_key=key).first()

    if request.method == "GET":
        if row:
            return jsonify(row.payload)
        return jsonify({} if key == "product_list" else [])

    if request.method == "DELETE":
        if row:
            db.session.delete(row)
            db.session.commit()
        return jsonify(ok=True)

    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify(error="A valid JSON request body is required"), 400

    if row is None:
        row = AppData(data_key=key, payload=payload)
    else:
        row.payload = payload

    db.session.add(row)
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
    payload = {row.data_key: row.payload for row in AppData.query.all()}
    return jsonify({"created_at": __import__("datetime").datetime.utcnow().isoformat() + "Z", "app_data": payload, "customers": [customer_json(c) for c in Customer.query.order_by(Customer.name).all()]})

@app.get("/health")
def health():
    # This checks the actual database connection, not only whether Flask is running.
    db.session.execute(text("SELECT 1"))
    return jsonify(status="ok", database="connected")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
