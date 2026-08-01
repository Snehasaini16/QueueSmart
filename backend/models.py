from datetime import datetime
from extensions import db


class Service(db.Model):
    """A service counter, e.g. 'OPD', 'Billing', 'Registration'."""
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    # Rolling average time (in seconds) it takes to serve one person.
    # Updated with an exponential moving average every time someone is served.
    avg_service_time = db.Column(db.Float, nullable=False, default=180.0)  # default: 3 min

    entries = db.relationship("QueueEntry", backref="service", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "avg_service_time": round(self.avg_service_time, 1),
        }


class QueueEntry(db.Model):
    """A single person's ticket in a service's queue."""
    __tablename__ = "queue_entries"

    STATUS_WAITING = "waiting"
    STATUS_SERVING = "serving"
    STATUS_DONE = "done"
    STATUS_NO_SHOW = "no_show"

    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    token_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=STATUS_WAITING)

    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    serving_started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "service_id": self.service_id,
            "name": self.name,
            "token_number": self.token_number,
            "status": self.status,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
        }
