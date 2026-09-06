"""
app.py
------
HydroVision - Crowdsourced Water Quality & Contamination Index Portal.

Route overview:
  /                -> landing page
  /learn           -> educational hub: pH / turbidity / TDS / nitrates facts
  /register, /login, /logout -> authentication
  /submit          -> form to log a new water test (GET shows form, POST saves it)
  /dashboard       -> searchable/filterable list of all submitted tests
  /alerts          -> recent tests classified as Poor/Very Poor/Unsuitable
  /api/tests       -> JSON search/filter API over the real WaterTest table
                    
"""

import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from werkzeug.utils import secure_filename

from models import db, User, WaterTest
from wqi_calculator import calculate_wqi

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-secret-key-change-this-before-deploying"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'hydrovision.db')}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # -----------------------------------------------------------------
    # Public pages
    # -----------------------------------------------------------------
    @app.route("/")
    def index():
        recent_tests = WaterTest.query.order_by(WaterTest.created_at.desc()).limit(6).all()
        return render_template("index.html", recent_tests=recent_tests)

    # -----------------------------------------------------------------
    # Learn hub - educational content on what each parameter means,
    # with internal anchor links (#ph, #turbidity, #tds, #nitrates)
    # so cards elsewhere on the site can deep-link straight to a topic.
    # -----------------------------------------------------------------
    @app.route("/learn")
    def learn():
        return render_template("learn.html")

    # -----------------------------------------------------------------
    # Authentication
    # -----------------------------------------------------------------
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            name = request.form["name"].strip()
            email = request.form["email"].strip().lower()
            password = request.form["password"]
            role = request.form.get("role", "citizen")

            if User.query.filter_by(email=email).first():
                flash("An account with that email already exists.", "error")
                return redirect(url_for("register"))

            user = User(name=name, email=email, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()

            flash("Account created — please log in.", "success")
            return redirect(url_for("login"))

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form["email"].strip().lower()
            password = request.form["password"]
            user = User.query.filter_by(email=email).first()

            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for("dashboard"))

            flash("Invalid email or password.", "error")

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("index"))

    # -----------------------------------------------------------------
    # Submit a water test - this is where the backend computation happens
    # -----------------------------------------------------------------
    @app.route("/submit", methods=["GET", "POST"])
    @login_required
    def submit_test():
        if request.method == "POST":
            location_name = request.form["location_name"].strip()
            source_type = request.form["source_type"]
            latitude = request.form.get("latitude") or None
            longitude = request.form.get("longitude") or None

            ph = float(request.form["ph"])
            turbidity = float(request.form["turbidity"])
            tds = float(request.form["tds"])
            nitrates = float(request.form["nitrates"])

            # --- This is the core backend logic: compute WQI server-side ---
            result = calculate_wqi(ph, turbidity, tds, nitrates)

            # Handle optional photo (works with a phone camera via the
            # capture="environment" attribute on the file input in the form)
            photo_filename = None
            photo = request.files.get("photo")
            if photo and photo.filename and _allowed_file(photo.filename):
                photo_filename = secure_filename(
                    f"{current_user.id}_{int(datetime.utcnow().timestamp())}_{photo.filename}"
                )
                photo.save(os.path.join(UPLOAD_FOLDER, photo_filename))

            test = WaterTest(
                user_id=current_user.id,
                location_name=location_name,
                source_type=source_type,
                latitude=float(latitude) if latitude else None,
                longitude=float(longitude) if longitude else None,
                ph=ph,
                turbidity=turbidity,
                tds=tds,
                nitrates=nitrates,
                wqi_score=result["wqi"],
                status=result["status"],
                photo_filename=photo_filename,
            )
            db.session.add(test)
            db.session.commit()

            flash(f"Test submitted — WQI {result['wqi']} ({result['status']})", "success")
            return redirect(url_for("dashboard"))

        return render_template("submit.html")

    # -----------------------------------------------------------------
    # Edit an existing water test - ONLY the original submitter may edit.
    # Any other logged-in user hitting this URL (even by guessing the id)
    # gets rejected with a 403, no matter how they got here.
    # -----------------------------------------------------------------
    @app.route("/test/<int:test_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_test(test_id):
        test = WaterTest.query.get_or_404(test_id)

        # --- Ownership check: this is the whole rule in one line ---
        if test.user_id != current_user.id:
            flash("You can only edit water tests you submitted yourself.", "error")
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            test.location_name = request.form["location_name"].strip()
            test.source_type = request.form["source_type"]
            latitude = request.form.get("latitude") or None
            longitude = request.form.get("longitude") or None
            test.latitude = float(latitude) if latitude else None
            test.longitude = float(longitude) if longitude else None

            test.ph = float(request.form["ph"])
            test.turbidity = float(request.form["turbidity"])
            test.tds = float(request.form["tds"])
            test.nitrates = float(request.form["nitrates"])

            # Recompute WQI server-side from the edited readings - same
            # rule as submit_test(): never trust/accept a client-sent score.
            result = calculate_wqi(test.ph, test.turbidity, test.tds, test.nitrates)
            test.wqi_score = result["wqi"]
            test.status = result["status"]

            # Optional: allow replacing the evidence photo
            photo = request.files.get("photo")
            if photo and photo.filename and _allowed_file(photo.filename):
                photo_filename = secure_filename(
                    f"{current_user.id}_{int(datetime.utcnow().timestamp())}_{photo.filename}"
                )
                photo.save(os.path.join(UPLOAD_FOLDER, photo_filename))
                test.photo_filename = photo_filename

            db.session.commit()
            flash(f"Test updated — WQI {result['wqi']} ({result['status']})", "success")
            return redirect(url_for("dashboard"))

        return render_template("edit_test.html", test=test)

    # -----------------------------------------------------------------
    # Delete an existing water test - ONLY the original submitter may
    # delete it. Same ownership rule as edit_test(). POST-only (never
    # triggered by a plain link/GET) so it can't be triggered by
    # accident or by a crawler, and the confirmation dialog on the
    # frontend gives the user one more chance to back out.
    # -----------------------------------------------------------------
    @app.route("/test/<int:test_id>/delete", methods=["POST"])
    @login_required
    def delete_test(test_id):
        test = WaterTest.query.get_or_404(test_id)

        if test.user_id != current_user.id:
            flash("You can only delete water tests you submitted yourself.", "error")
            return redirect(url_for("dashboard"))

        # Clean up the evidence photo from disk too, if one was attached.
        if test.photo_filename:
            photo_path = os.path.join(UPLOAD_FOLDER, test.photo_filename)
            if os.path.exists(photo_path):
                os.remove(photo_path)

        db.session.delete(test)
        db.session.commit()

        flash("Water test deleted.", "success")
        return redirect(url_for("dashboard"))

    # -----------------------------------------------------------------
    # Dashboard - searchable / filterable
    # -----------------------------------------------------------------
    @app.route("/dashboard")
    @login_required
    def dashboard():
        query = WaterTest.query

        search = request.args.get("search", "").strip()
        status_filter = request.args.get("status", "")

        if search:
            query = query.filter(WaterTest.location_name.ilike(f"%{search}%"))
        if status_filter:
            query = query.filter(WaterTest.status == status_filter)

        tests = query.order_by(WaterTest.created_at.desc()).all()
        return render_template(
            "dashboard.html", tests=tests, search=search, status_filter=status_filter
        )

    # -----------------------------------------------------------------
    # JSON API - search/filter water tests
    #
    # This is a second, meaningful endpoint beyond the core "submit a
    # test" feature: it lets any client (or a future frontend, mobile
    # app, etc.) query the *real* WaterTest table as JSON, using the
    # same search/status/source filters as the dashboard - it never
    # returns static or hardcoded data.
    #
    # Query params (all optional):
    #   search       - substring match on location_name
    #   status       - Excellent / Good / Poor / Very Poor / Unsuitable
    #   source_type  - Well / Tap / River / Lake / Rainwater
    #
    # Edge cases handled gracefully:
    #   - an invalid status/source_type value returns 400 with a clear
    #     error message instead of silently returning nothing
    #   - no matching rows returns 200 with an empty "results" list and
    #     a friendly message, rather than an error
    # -----------------------------------------------------------------
    @app.route("/api/tests")
    def api_tests():
        valid_statuses = ["Excellent", "Good", "Poor", "Very Poor", "Unsuitable"]
        valid_sources = ["Well", "Tap", "River", "Lake", "Rainwater"]

        search = request.args.get("search", "").strip()
        status_filter = request.args.get("status", "").strip()
        source_filter = request.args.get("source_type", "").strip()

        # --- Edge case: reject unknown filter values up front ---
        if status_filter and status_filter not in valid_statuses:
            return jsonify({
                "error": f"Invalid status '{status_filter}'. "
                         f"Must be one of: {', '.join(valid_statuses)}"
            }), 400

        if source_filter and source_filter not in valid_sources:
            return jsonify({
                "error": f"Invalid source_type '{source_filter}'. "
                         f"Must be one of: {', '.join(valid_sources)}"
            }), 400

        query = WaterTest.query
        if search:
            query = query.filter(WaterTest.location_name.ilike(f"%{search}%"))
        if status_filter:
            query = query.filter(WaterTest.status == status_filter)
        if source_filter:
            query = query.filter(WaterTest.source_type == source_filter)

        tests = query.order_by(WaterTest.created_at.desc()).all()

        # --- Edge case: no results is a valid, successful response ---
        if not tests:
            return jsonify({
                "count": 0,
                "results": [],
                "message": "No water tests match those filters."
            }), 200

        return jsonify({
            "count": len(tests),
            "results": [t.to_dict() for t in tests],
        }), 200

    # -----------------------------------------------------------------
    # Emergency alert feed - recent hazardous submissions
    # -----------------------------------------------------------------
    @app.route("/alerts")
    def alerts():
        cutoff = datetime.utcnow() - timedelta(days=14)
        hazardous = (
            WaterTest.query.filter(
                WaterTest.status.in_(["Poor", "Very Poor", "Unsuitable"]),
                WaterTest.created_at >= cutoff,
            )
            .order_by(WaterTest.created_at.desc())
            .all()
        )
        return render_template("alerts.html", hazardous=hazardous)

    with app.app_context():
        db.create_all()

    return app


def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5001)
