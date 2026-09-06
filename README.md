# 💧 HydroVision

**Crowdsourced Water Quality & Contamination Index Portal**
SDG 6: Clean Water & Sanitation

**🌐 Live/hosted link:** https://kothmajayasooriya.pythonanywhere.com

HydroVision lets citizens and lab technicians log real water quality readings pH, turbidity, total dissolved solids (TDS), and nitrates for wells, taps, rivers, lakes, and rainwater tanks in their community. Every submission is automatically scored server-side into a **Water Quality Index (WQI)** using the Weighted Arithmetic Method, turning raw numbers into a transparent, shared safety record instead of a self-reported opinion.

---

## ✨ Features

- **Server-side WQI calculation** — every reading is scored against WHO-based permissible limits and classified as Excellent, Good, Poor, Very Poor, or Unsuitable. The score is always recomputed on the server, never trusted from the client, on both submission and edit.
- **Contamination alerts feed** (`/alerts`) — automatically surfaces tests classified Poor or worse from the last 14 days.
- **Searchable, filterable dashboard** — live search by location, filter by safety status, sorted by most recent.
- **JSON search/filter API** (`GET /api/tests`) — a second, real API endpoint (beyond the core submit feature) that queries the live database with optional `search`, `status`, and `source_type` params. Returns `400` with a clear message for an invalid filter value, and `200` with an empty result list (not an error) when nothing matches.
- **Full submission workflow** — location, source type, four raw readings, optional GPS coordinates, and an optional evidence photo (camera-ready via `capture="environment"`).
- **Owner-only edit & delete** — only the original submitter can edit or delete a test; deletion is a confirmed, POST-only action that also removes the stored photo.
- **Secure authentication** — Flask-Login sessions with salted Werkzeug password hashing; separate citizen and lab-technician roles.
- **Live location autocomplete** — debounced type-ahead search powered by the free OpenStreetMap Nominatim API, auto-filling latitude/longitude.
- **Educational Learn hub** (`/learn`) — anchor-linked sections explaining pH, turbidity, TDS, and nitrates, and exactly how the WQI formula works.
- **Custom-styled UI** — a custom colour palette drawn from the project logo, card layouts, status badges, sticky header, and flash-message feedback - built entirely with custom CSS without relying on pre-made design frameworks.

---

## 🧮 How the WQI Score Works

HydroVision uses the **Weighted Arithmetic Water Quality Index** method.

| Parameter | Ideal value (Vio) | Standard limit (Sn) |
|---|---|---|
| pH | 7 | 8.5 |
| Turbidity (NTU) | 0 | 5 |
| TDS (mg/L) | 0 | 500 |
| Nitrates (mg/L) | 0 | 45 |

1. **Unit weight:** `wi = k / Sn`, where `k = 1 / Σ(1/Sn)`
2. **Quality rating:**
   - pH: `qi = |Vi - 7| / (8.5 - 7) × 100`
   - Others: `qi = (Vi / Sn) × 100`
3. **Final index:** `WQI = Σ(wi × qi) / Σ(wi)`

**Classification:**
| WQI Range | Status |
|---|---|
| 0 – 25 | Excellent (Safe) |
| 26 – 50 | Good (Safe) |
| 51 – 75 | Poor (Moderate/Warning) |
| 76 – 100 | Very Poor (Contaminated) |
| 100+ | Unsuitable (Hazardous) |

See `wqi_calculator.py` for the implementation, and `/learn#wqi` in the app for the plain-language explanation.

---

## 🛠️ Technology Stack

- **Backend:** Python 3, Flask 3.0.3
- **Database & ORM:** SQLite, Flask-SQLAlchemy 3.1.1
- **Authentication:** Flask-Login 0.6.3, Werkzeug 3.0.3
- **Frontend:** Jinja2, HTML5, custom CSS3, vanilla JavaScript
- **External API:** OpenStreetMap Nominatim (free, no API key) for location autocomplete
- **Hosting:** Live on PythonAnywhere — https://kothmajayasooriya.pythonanywhere.com

---

## 📁 Project Structure

```
hydrovision/
├── app.py                  # Flask app factory & all routes
├── models.py                # SQLAlchemy models: User, WaterTest
├── wqi_calculator.py        # WQI formula (standalone, testable)
├── requirements.txt
├── .gitignore
├── static/
│   ├── style.css
│   ├── img/
│   │   ├── favicon.png
│   │   ├── logo.png
│   │   └── logo.svg
│   └── uploads/              # evidence photos (created at runtime)
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── learn.html
│   ├── login.html
│   ├── register.html
│   ├── submit.html
│   ├── edit_test.html
│   ├── dashboard.html
│   └── alerts.html
└── instance/
    └── hydrovision.db        # SQLite database (created at runtime)
```

---

## 🚀 Setup & Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd hydrovision
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Add the static assets**
   Place `logo.png`, `logo.svg`, and `favicon.png` inside `static/img/` (referenced by every page's header and favicon).

5. **Run the application**
   ```bash
   python app.py
   ```
   This auto-creates the `instance/` folder, the SQLite database, and the `static/uploads/` folder on first run.

6. **Open the app**
   Visit **http://localhost:5001**, register an account, and start logging water tests.

---

## 🔒 Security Notes

- Passwords are salted and hashed with Werkzeug - never stored in plain text.
- WQI scores and safety statuses are **always** calculated server-side; client-submitted values for these fields are ignored.
- Edit and delete are restricted to the original submitter, enforced on the server regardless of how the URL is reached.
- Uploaded photos are restricted to `png`/`jpg`/`jpeg` and saved under sanitised, collision-proof filenames.
- ⚠️ Before deploying, change `SECRET_KEY` in `app.py` from the development placeholder.

---

## 👤 Author

**Kothma Jayasooriya**
Informatics Institute of Technology (IIT)
