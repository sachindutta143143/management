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


## Install Multi Plaza on Desktop (PWA)
After deploying the site over HTTPS, open the home page in Google Chrome or Microsoft Edge.
- Chrome: click the three-dot menu (top-right) → Cast, save and share (or Save and share) → Install page as app / Install Multi Plaza. In some versions this appears as an install icon at the right of the address bar.
- Edge: three-dot menu → Apps → Install this site as an app.
If Chrome only shows “Create shortcut”, select it and tick “Open as window”.

The app includes a web app manifest, 192px/512px icons, and a service worker for app-shell caching. Online connection is still required for PostgreSQL data saving; offline edits are not queued for database sync.

## Others Register
The Others section is now a separate full copy of the Credit / Supply Register layout and functions. It uses its own PostgreSQL key (`others_register`) and browser storage key, so its records remain separate from Credit / Supply records.
