# HydroVision — Technical Documentation

*Kothma Jayasooriya | Informatics Institute of Technology (IIT)*

---

## 1. Introduction

HydroVision is a crowdsourced web application that lets citizens and lab technicians log water quality readings pH, turbidity, total dissolved solids (TDS), and nitrates for wells, taps, rivers, lakes, and rainwater tanks in their community. Each submission is automatically scored server-side into a Water Quality Index (WQI) using the Weighted Arithmetic Method, producing a transparent, objective safety classification instead of a self-reported opinion. The project addresses UN Sustainable Development Goal 6: Clean Water and Sanitation, turning scattered individual observations into a shared, searchable safety record for a community.

---

## 2. Problem Statement

- **No affordable, community-level testing** — lab-grade water analysis is expensive and slow, so most households, especially in low-resource areas, never get their well, tap, or river water professionally checked.
- **Contamination is invisible** — parameters such as nitrates and dissolved solids cannot be seen, smelled, or tasted, so a source can turn unsafe with no visible warning to the people relying on it.
- **Readings are fragmented or lost** — informal testing (strips, handheld meters) is usually recorded on paper or not at all, so a community has no shared, searchable history of its own water quality.
- **No early-warning mechanism** — even when a bad reading is taken, there is no shared channel for flagging it to neighbours who draw from the same source.
- **Low public understanding** — most residents do not know what pH, turbidity, TDS, or nitrates actually indicate, so a raw number on a test strip carries little meaning on its own.

HydroVision is built directly against these five gaps: it gives anyone a free way to log a real reading, computes an unbiased score for them automatically, stores every submission in a shared, searchable record, raises hazardous readings through a dedicated alerts feed, and pairs every reading with plain-language education on what it means.

---

## 3. Key Features

### 3.1 Core Data & Water Quality Engine

- **Server-side WQI calculation** — every submission is scored using the Weighted Arithmetic Water Quality Index method against WHO-based permissible limits for pH, turbidity, TDS, and nitrates, then classified into one of five statuses (Excellent, Good, Poor, Very Poor, Unsuitable). The score is always recomputed on the server and is never accepted from the client, on both submission and edit.
- **Contamination alerts feed** — a dedicated `/alerts` page automatically surfaces every test classified Poor, Very Poor, or Unsuitable within the last 14 days, so hazardous readings are never buried in the general dashboard.
- **Searchable, filterable dashboard** — the community dashboard supports live search by location name and filtering by safety status, with results always ordered by most recent submission.
- **JSON search/filter API (`GET /api/tests`)** — a second, standalone endpoint beyond the core submission flow, so any client (a future mobile app, another team's tool, etc.) can query real, live `WaterTest` rows as JSON. It accepts optional `search` (location substring), `status`, and `source_type` query parameters and combines them the same way the dashboard does. Invalid `status`/`source_type` values return `400` with a clear error message; a query with no matches returns `200` with an empty `results` array and a friendly `message`, rather than erroring out. Example: `GET /api/tests?search=river&status=Poor`. Full write-up in Section 5.1.

### 3.2 Data Capture & Ownership

- **Full test submission workflow** — users log a location, water source type (well, tap, river, lake, or rainwater), the four raw readings, optional GPS coordinates, and an optional evidence photo.
- **Camera-ready evidence photos** — the photo field uses `capture="environment"` so it opens a phone's rear camera directly, with uploads restricted to safe image types and stored under sanitised, collision-proof filenames.
- **Owner-only edit & delete** — every water test can only be edited or deleted by the user who originally submitted it; the WQI is transparently recalculated on every edit, and deletion is a confirmed, POST-only action that also cleans up the stored photo.
- **Secure authentication** — registration and login are backed by Flask-Login sessions and salted Werkzeug password hashing, with separate citizen and lab-technician roles.

### 3.3 Location & User Experience

- **Live location autocomplete** — a debounced, type-ahead search (built on the free OpenStreetMap Nominatim API) suggests real place names and auto-fills latitude/longitude, used on both the test form and the global header search.
- **Educational Learn hub** — anchor-linked sections explain what pH, turbidity, TDS, and nitrates mean, their safe limits, common causes, and exactly how the WQI formula turns them into a score, so every number on the dashboard has a plain-language explanation behind it.
- **Custom, considered UI** — a bespoke colour palette drawn from the project logo, card-based layouts, colour-coded status badges, a sticky header with global search, flash-message feedback, and a back-to-top control - built entirely in custom CSS rather than a default framework theme.
- **Real, live data throughout** — the home page statistics, recent-submissions grid, and dashboard all render genuine community-submitted rows from the database; nothing on the public pages is hard-coded or placeholder content.

---

## 4. Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3, Flask 3.0.3 |
| Database & ORM | SQLite, Flask-SQLAlchemy 3.1.1 |
| Authentication | Flask-Login 0.6.3, Werkzeug 3.0.3 (salted password hashing, `secure_filename` for uploads) |
| Frontend | Jinja2 templating, HTML5, hand-written CSS3, vanilla JavaScript |
| External API | OpenStreetMap Nominatim (free, no API key) for location autocomplete |
| Version control / hosting | Git & GitHub repository; live at https://kothmajayasooriya.pythonanywhere.com |

---

## 5. Bonus Features

### 5.1 Backend Bonus Brick — JSON Search/Filter API

- **What it does** — `GET /api/tests` is a second, standalone endpoint beyond the core "submit a test" feature. It queries the real `WaterTest` table (never static or hardcoded data) using the same search/status/source_type logic as the dashboard, and returns the results as JSON rather than a rendered page.
- **Why it was added** — to demonstrate that the underlying data is genuinely reusable beyond the website itself: any future client (a mobile app, another team's tool, an automated report) could query live water quality data without needing to parse HTML.
- **Edge cases handled** — an invalid `status` or `source_type` value returns a `400` response with a clear error message instead of failing silently; a query with no matching rows returns a successful `200` response with an empty `results` list and a friendly `message`, rather than an error.
- **Example** — `GET /api/tests?search=river&status=Poor` returns every Poor-rated test with "river" in its location name.

### 5.2 Python Bonus Brick — WQI Calculation Engine

- **What it does** — `wqi_calculator.py` implements the Weighted Arithmetic Water Quality Index formula as a standalone module, independent of Flask or the database, going well beyond basic CRUD operations.
- **Why it was added** — a genuine calculation was needed to turn four raw readings into one meaningful, trustworthy safety score, rather than asking users to interpret four separate numbers themselves.
- **Tested with real data** — the module's own `__main__` block runs three sample cases (clean tap water, slightly polluted, heavily contaminated) and prints the resulting WQI and status, verifying the formula before it was wired into the Flask app.

---

## 6. Data Model

**User**
| Field | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| name | String(100) | |
| email | String(150) | Unique |
| password_hash | String(255) | Salted hash, never plain text |
| role | String(20) | `citizen` or `technician` |
| created_at | DateTime | |

**WaterTest**
| Field | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| user_id | Integer | Foreign key → User |
| location_name | String(150) | |
| latitude / longitude | Float | Optional |
| source_type | String(50) | Well, Tap, River, Lake, Rainwater |
| ph / turbidity / tds / nitrates | Float | Raw user-entered readings |
| wqi_score | Float | **Computed server-side only** |
| status | String(20) | **Computed server-side only** |
| photo_filename | String(255) | Optional evidence photo |
| created_at | DateTime | |

---

## 7. Setup Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd hydrovision
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   source venv/bin/activate     # macOS/Linux
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   Installs Flask, Flask-SQLAlchemy, Flask-Login, Werkzeug, gunicorn.

4. **Add the static assets**
   Place `logo.png`, `logo.svg`, and `favicon.png` inside `static/img/` (referenced by every page's header and favicon).

5. **Run the application**
   ```bash
   python app.py
   ```
   This auto-creates the `instance/` folder, the SQLite database, and the `static/uploads/` folder on first run.

6. **Open the app**
   Visit `http://localhost:5001` in a browser, register an account, and start logging water tests.

---

## 8. Conclusion

HydroVision is a fully connected three-tier build - a Flask backend, an SQLAlchemy/SQLite database, and a hand-styled Jinja2 frontend - where every meaningful interaction (registering, logging in, submitting, searching, editing, deleting) triggers real backend logic and a genuine calculation engine, and where computed scores are never trusted from the client. It directly answers the problem it set out to solve: giving any community a free, understandable, and shared way to monitor its own water quality in support of SDG 6: Clean Water and Sanitation.
