# Multi Plaza Management — Railway Starter

## Included
- `templates/product.html` — original product & price list, split into its own file; saves to PostgreSQL API.
- `templates/credit_register.html` — original credit/supply register, split into its own file; saves to PostgreSQL API.
- `templates/quotation.html` — original quotation, separate file.
- `templates/others.html` — separate Others register with flexible multiline fields, PostgreSQL-backed.\n- `templates/customers.html` — new flexible customer manager (add/edit/delete/search).
- `templates/index.html` — dashboard navigation; add future modules here.
- `app.py` — Flask routes + PostgreSQL JSON data API + customer CRUD.

## Run locally
1. Install Python 3.11+.
2. In this folder run: `python -m venv .venv`
3. Activate: Windows PowerShell: `.venv\\Scripts\\Activate.ps1`
4. Install: `pip install -r requirements.txt`
5. Set `DATABASE_URL` to a PostgreSQL connection string (or omit for local SQLite test).
6. Run: `python app.py`
7. Open `http://127.0.0.1:5000`.

## Railway deployment
1. Push this folder to a new GitHub repository.
2. In Railway create a project and deploy the GitHub repository.
3. Add a PostgreSQL service to the same Railway project.
4. Open web service → Variables → add `DATABASE_URL` using the PostgreSQL service's `DATABASE_URL` reference.
5. Add `SECRET_KEY` with a long random value.
6. Deploy/redeploy. Open the generated public domain.
7. Test `/health`, then add one test customer and refresh the page.

## Important
- Product list and supply register have PostgreSQL API persistence with browser-local fallback if the server/database is unavailable.
- Customer CRUD is PostgreSQL-backed.\n- Customer field in Credit/Supply Register is multiline and vertically resizable, like Item.\n- Others section has its own database key (`others_register`).
- Quotation remains a separate original HTML page in this first migration; quotation-history saving and automatic customer autofill are the next integration step.
- Back up the database before production use. Add authentication/login and role permissions before exposing business records publicly.
- Do not commit `.env` or database credentials to GitHub.

## Auto-save
- Product & Price List: edits and row additions/deletions auto-save after a short pause.
- Credit / Supply Register: existing automatic database save remains enabled.
- Others: each typed change auto-saves to the shared database after a short pause.
- Quotation: form fields and editable text auto-save to the shared database; a local browser draft is also kept.
- Customers: once a customer name is entered, changes auto-save to the shared database; an incomplete draft is kept locally until a name is entered.

Auto-save to the shared database requires the Railway PostgreSQL service to be connected and the app deployed. Local drafts are browser/device-specific and are not a substitute for database backup.


## Payment remarks (new)
Credit / Supply Register now has a separate multiline remark field directly below each of Payment Received 1, 2, and 3. Use it to record when the payment was received, payment mode (cash/UPI/bank), transaction/reference details, or any note. These fields are saved with the corresponding row through the existing auto-save API and PostgreSQL record. Existing payment amounts remain unchanged.

## Desktop installation (PWA)
The dashboard includes a web app manifest and service worker. Open the HTTPS Railway site in Chrome and use the browser menu to install the page as an app / create shortcut.
