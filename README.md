# DentAI Dental

Academic demo of a clinic patient-management app with an ML treatment-urgency
predictor. **Not for real clinical decisions**: the ML model is trained on synthetic
data and sample patients are not real records.

## Quick start

Requires Python 3.10+ and Node.js 18+ (for the Tailwind build).

```bash
python -m venv venv
. venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
npm install
npm run build                  # compile static/src -> static/dist/tailwind.css
python app.py
```

Open http://127.0.0.1:5000 (Windows: double-click `run.bat`). First launch creates
and migrates `dental_ai.db`, seeds sample data, and trains ML models lazily on the
first prediction (cached in `models/`).

## Demo accounts

| Role          | Email                   | Password    |
|---------------|-------------------------|-------------|
| Administrator | admin@dentalai.local    | admin123    |
| Dentist       | dentist@dentalai.local  | dentist123  |
| Evaluator     | evaluator@dentalai.local| evaluator123|

Evaluator is read-only (no edits, no CSV import). Dentist and Administrator edit
patients, teeth, treatments, and appointments. `/users` is Administrator-only.

## Features

- Role-based login/logout (Dentist, Administrator, Evaluator), CSRF-protected
- Dashboard, patient management (add/edit/search/paginate/delete/CSV import)
- Interactive FDI dental chart (teeth 11-48) with clinical records and treatment history
- AI urgency prediction (5 sklearn models) with signals breakdown and risk assessment
- Appointments, Reports & Analytics, User management
- JSON API: `POST /api/predict`, `POST /api/import_csv`

## Config

- `DENTAI_DB`: database path (default `dental_ai.db`)
- `DENTAI_SECRET`: Flask secret; auto-generated to `.secret_key` (chmod 600) if unset.
  Set a strong value before any non-demo deployment.

## Project layout

```
app.py                Thin entrypoint (create_app + run)
dentai_app/           Flask package: config, db, migrations, ml, auth, routes/
templates/            Jinja2 templates
static/               Tailwind v4 source (static/src) + compiled dist, fonts, icons
tests/                pytest smoke suite
```

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests/
```

## API example

State-changing endpoints require a CSRF token: a session cookie plus an
`X-CSRF-Token` header from any logged-in page (form field `csrf_token`).

```bash
curl -c cookies.txt http://127.0.0.1:5000/login -o login.html   # get token + cookie

curl -X POST http://127.0.0.1:5000/api/predict \
  -b cookies.txt -H "Content-Type: application/json" -H "X-CSRF-Token: <token>" \
  -d '{"age":45,"sex":"Female","smoking":"Yes","dental_pain":"Yes","caries_count":6,"periodontal_status":"Severe"}'
```