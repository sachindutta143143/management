import os, json
from uuid import uuid4
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Text

app = Flask(__name__)
database_url = os.getenv("DATABASE_URL", "")
# Railway may provide postgres:// or postgresql://. This project installs psycopg v3,
# so explicitly select its SQLAlchemy dialect.
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///local_dev.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
db = SQLAlchemy(app)

class AppData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data_key = db.Column(db.String(100), unique=True, nullable=False)
    payload = db.Column(db.JSON, nullable=False, default=dict)

class Customer(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    name = db.Column(db.String(250), nullable=False)
    mobile = db.Column(db.String(40))
    email = db.Column(db.String(250))
    gstin = db.Column(db.String(30))
    state = db.Column(db.String(100))
    city = db.Column(db.String(100))
    pincode = db.Column(db.String(15))
    address = db.Column(db.Text)

with app.app_context():
    db.create_all()

# These pages are standalone HTML files with their own JavaScript/CSS.
# Serve them as files instead of running them through Jinja templating.
@app.get("/")
def home(): return send_from_directory("templates", "index.html")
@app.get("/product")
def product(): return send_from_directory("templates", "product.html")
@app.get("/credit")
def credit(): return send_from_directory("templates", "credit_register.html")
@app.get("/quotation")
def quotation(): return send_from_directory("templates", "quotation.html")
@app.get("/customers")
def customers_page(): return send_from_directory("templates", "customers.html")
@app.get("/others")
def others_page(): return send_from_directory("templates", "others.html")

@app.route("/api/data/<key>", methods=["GET","PUT","DELETE"])
def app_data(key):
    if key not in {"product_list","supply_register","quotation_data","settings","others_register"}:
        return jsonify(error="Unknown data section"), 404
    row = AppData.query.filter_by(data_key=key).first()
    if request.method == "GET":
        return jsonify(row.payload if row else ({} if key=="product_list" else []))
    if request.method == "DELETE":
        if row: db.session.delete(row); db.session.commit()
        return jsonify(ok=True)
    payload = request.get_json(silent=True)
    if payload is None: return jsonify(error="JSON body required"), 400
    if row is None: row=AppData(data_key=key,payload=payload)
    else: row.payload=payload
    db.session.add(row); db.session.commit()
    return jsonify(ok=True)

def customer_json(c):
    return {k:getattr(c,k) for k in ["id","name","mobile","email","gstin","state","city","pincode","address"]}
@app.get("/api/customers")
def customer_list():
    return jsonify([customer_json(c) for c in Customer.query.order_by(Customer.name).all()])
@app.post("/api/customers")
def customer_create():
    data=request.get_json(silent=True) or {}
    if not str(data.get("name","")).strip(): return jsonify(error="Customer name required"),400
    c=Customer(**{k:data.get(k) for k in ["name","mobile","email","gstin","state","city","pincode","address"]})
    db.session.add(c); db.session.commit()
    return jsonify(customer_json(c)),201
@app.put("/api/customers/<cid>")
def customer_update(cid):
    c=db.session.get(Customer,cid)
    if not c:return jsonify(error="Not found"),404
    data=request.get_json(silent=True) or {}
    for k in ["name","mobile","email","gstin","state","city","pincode","address"]:
        if k in data:setattr(c,k,data[k])
    db.session.commit();return jsonify(customer_json(c))
@app.delete("/api/customers/<cid>")
def customer_delete(cid):
    c=db.session.get(Customer,cid)
    if not c:return jsonify(error="Not found"),404
    db.session.delete(c);db.session.commit();return jsonify(ok=True)

@app.get("/health")
def health(): return jsonify(status="ok")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",5000)))
