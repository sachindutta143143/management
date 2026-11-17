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

## Offline-first backup and sync (added)
- `static/offline-sync.js` caches successful API GET responses in IndexedDB.
- Data API changes and customer create/update/delete operations are queued in the browser when the network/server is unavailable, then retried when the connection returns.
- Offline customer creation uses a client-generated ID so a retry does not create a duplicate.
- A daily local browser snapshot is retained in localStorage (subject to browser storage limits and the user not clearing site data).
- The dashboard has a **Backup** button. When online it downloads a JSON export from `/api/backup/export` (server-side app data + customers); when offline it downloads a local browser backup.
- A small status indicator shows online/synced or pending offline changes.

Important limitations:
- Offline changes are stored on that same device until they sync. They are not visible on another device until the server sync succeeds.
- Browser storage can be cleared or evicted. Export backups regularly and configure Railway PostgreSQL backups separately in Railway's database Backups tab. This application does not claim to create a separate daily cloud backup automatically.
- If the browser is closed while offline, queued changes remain on that device and sync on the next visit when online.


## Others Register

The Others page now uses the same full register interface and features as Credit / Supply Register (dashboard totals, editable grid, payment 1/2/3 with remarks, Excel/CSV import/export, row controls, and auto-save). It uses a separate PostgreSQL key `others_register` and separate browser storage key, so its records remain independent from Credit / Supply.


## Railway PostgreSQL data organization (current)

The app uses Railway `DATABASE_URL` when configured. Current application tables are:

- `product_list` — Product & Price List
- `credit_supply_register` — ONE combined table for Credit and Supply. Row `id=1` stores JSON arrays under `credit` and `supply`.
- `installment_register` — Installment Register
- `others_register` — Others Register
- `quotation_data` — Quotation data
- `customers` — Customer details
- `app_data` — legacy key/value storage retained for migration and rollback; it is not the current active storage for the modules above.

The old `credit_register` and `supply_register` tables/keys may remain in PostgreSQL from earlier versions. The application migrates their data into `credit_supply_register` when the combined row does not yet exist. Legacy tables and rows are intentionally retained; do not drop them until the new tables and all records have been verified and a Railway backup has been taken.

Installment Register is available at `/installments` and stores data through `/api/data/installment_register`.

Verify the database connection by opening `/health` on the deployed site. Configure Railway PostgreSQL backups separately.
