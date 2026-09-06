"""
models.py
---------
SQLAlchemy models for HydroVision.

Two tables:
  - User: people who submit water test readings (citizens or technicians)
  - WaterTest: an individual water quality submission, including the
    computed WQI score and status (these are NEVER set by the user directly -
    they're calculated server-side in app.py using wqi_calculator.py)
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="citizen")  # "citizen" or "technician"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # One user can submit many water tests
    tests = db.relationship("WaterTest", backref="submitted_by", lazy=True)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)


class WaterTest(db.Model):
    __tablename__ = "water_tests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    location_name = db.Column(db.String(150), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    source_type = db.Column(db.String(50), nullable=False)  # well, tap, river, etc.

    # Raw measurements entered by the user
    ph = db.Column(db.Float, nullable=False)
    turbidity = db.Column(db.Float, nullable=False)
    tds = db.Column(db.Float, nullable=False)
    nitrates = db.Column(db.Float, nullable=False)

    # Computed server-side - never trust client-submitted values for these
    wqi_score = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # Excellent/Good/Poor/Very Poor/Unsuitable

    photo_filename = db.Column(db.String(255), nullable=True)  # optional evidence photo
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convenience method for rendering in templates / future API use."""
        return {
            "id": self.id,
            "location_name": self.location_name,
            "source_type": self.source_type,
            "ph": self.ph,
            "turbidity": self.turbidity,
            "tds": self.tds,
            "nitrates": self.nitrates,
            "wqi_score": self.wqi_score,
            "status": self.status,
            "photo_filename": self.photo_filename,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M"),
            "submitted_by": self.submitted_by.name,
        }
