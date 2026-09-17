# DentAI Dental

Academic demo/prototype — a Flask patient-management app for dental clinics with an
ML treatment-urgency predictor. **Do not use for real clinical decisions**: the ML
component uses synthetic training data, and sample patients are not real records.

## Features

- Login / logout (POST-only) with role-based access (Dentist, Administrator, Evaluator)
- Dashboard with live stats and recent patients
- Patient management (add / edit / search / paginated list / delete / CSV import)
- Interactive FDI dental chart (teeth 11–48) with 9 tooth statuses
- Treatment / clinical record history per patient
- AI treatment-urgency prediction (5 sklearn models) with signals breakdown and a linked risk-assessment page
- Appointments with inline status updates, Reports & Analytics, User management
- CSRF protection on all state-changing requests
- JSON API: `POST /api/predict`, `POST /api/import_csv`

## Demo accounts

| Role          | Email                   | Password    |
|---------------|-------------------------|-------------|
| Administrator | admin@dentalai.local    | admin123    |
| Dentist       | dentist@dentalai.local  | dentist123  |
| Evaluator     | evaluator@dentalai.local| evaluator123|

Evaluator is read-only; Patient/AI/reports areas. Dentist and Administrator can also
create and edit patients, teeth, treatments, and appointments. `/users` is
Administrator-only.

## Run

```bash
python -m venv venv
. venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
npm install                    # Tailwind v4 CLI + vendored fonts/icons
npm run build                  # compile static/dist/tailwind.css
python app.py
```

Then open http://127.0.0.1:5000. Windows users can also double-click `run.bat`.

On first launch the app creates and migrates `dental_ai.db` (SQLite) and seeds sample
patients and the demo users above. The ML models train lazily on first prediction and
are cached to `models/` (joblib), so startup stays fast.

Configuration via environment variables:

- `DENTAI_DB` — database path
- `DENTAI_SECRET` — Flask secret key; if unset, a key is auto-generated and persisted
  to `.secret_key` in the project root (chmod 600) on first start

Set a strong `DENTAI_SECRET` before any non-demo deployment.

## Project layout

```
app.py                Thin entrypoint (create_app + run)
dentai_app/           Application package
  __init__.py         create_app() factory, blueprint registration
  config.py           Paths, secrets, constants (features, FDI, statuses)
  db.py               Connections, repositories, seeding
  migrations.py       Versioned SQLite schema migrations (FK rebuild)
  ml.py               Synthetic data, model training/cache, risk payload
  auth.py             login_required / role_required decorators
  routes/             Blueprints: auth, patients, chart, ai, admin, api
templates/            Jinja2 templates
static/               Tailwind v4 source (static/src) + compiled CSS, fonts, icons
tests/                pytest smoke suite (35 tests, incl. CSRF, roles, FK checks)
```

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests/
```

## API examples

Every state-changing endpoint requires a valid CSRF token. For the JSON API that
means an `X-CSRF-Token` header plus a logged-in session cookie: first GET `/` (or any
page) to obtain a `csrf_token` value and a session cookie, then use both:

```bash
# 1. Obtain a token + session cookie (any logged-in page works)
curl -c cookies.txt http://127.0.0.1:5000/login -o login.html
#    extract value="<token>" from login.html (field name="csrf_token")

# 2. JSON API with the token header
curl -X POST http://127.0.0.1:5000/api/predict \
  -b cookies.txt \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <token>" \
  -d '{"age":45,"sex":"Female","smoking":"Yes","dental_pain":"Yes","caries_count":6,"periodontal_status":"Severe"}'

curl -X POST http://127.0.0.1:5000/api/import_csv \
  -b cookies.txt \
  -H "X-CSRF-Token: <token>" \
  -F "file=@patients.csv"
```