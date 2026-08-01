"""
QueueSmart Lite - backend
A minimal real-time queue management system.

Run with:
    python app.py
Defaults to SQLite (queuesmart.db) so it runs with zero external setup.
To use MySQL instead, just change SQLALCHEMY_DATABASE_URI below to e.g.
    "mysql+pymysql://user:password@localhost/queuesmart"
and `pip install pymysql`.
"""

from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS

from extensions import db, socketio
from models import Service, QueueEntry

# ---- EMA smoothing factor for updating avg service time ----
# Higher = more weight to the most recent serve time.
ALPHA = 0.3


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///queuesmart.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    CORS(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)
    socketio.init_app(app)

    with app.app_context():
        db.create_all()
        _seed_default_services()

    register_routes(app)
    return app


def _seed_default_services():
    """Create a few default services on first run so the app is usable immediately."""
    if Service.query.count() == 0:
        for name in ["OPD", "Billing", "Registration"]:
            db.session.add(Service(name=name))
        db.session.commit()


# ---------- helper functions ----------

def waiting_entries_for(service_id):
    return (
        QueueEntry.query.filter_by(service_id=service_id, status=QueueEntry.STATUS_WAITING)
        .order_by(QueueEntry.token_number.asc())
        .all()
    )


def position_of(entry, waiting_list=None):
    """1-indexed position of `entry` among waiting entries for its service."""
    waiting_list = waiting_list if waiting_list is not None else waiting_entries_for(entry.service_id)
    for idx, e in enumerate(waiting_list):
        if e.id == entry.id:
            return idx + 1
    return None


def broadcast_queue_state(service_id):
    """Emit the full current state for a service to everyone watching its room."""
    service = Service.query.get(service_id)
    if not service:
        return

    waiting = waiting_entries_for(service_id)
    serving = QueueEntry.query.filter_by(
        service_id=service_id, status=QueueEntry.STATUS_SERVING
    ).first()

    payload = {
        "service": service.to_dict(),
        "serving": serving.to_dict() if serving else None,
        "waiting": [
            {
                **e.to_dict(),
                "position": idx + 1,
                "estimated_wait_seconds": round(idx * service.avg_service_time, 1),
            }
            for idx, e in enumerate(waiting)
        ],
    }
    socketio.emit("queue_update", payload, room=f"service_{service_id}")
    return payload


# ---------- REST routes ----------

def register_routes(app):

    @app.get("/api/services")
    def list_services():
        services = Service.query.all()
        return jsonify([s.to_dict() for s in services])

    @app.get("/api/queue/<int:service_id>")
    def get_queue(service_id):
        service = Service.query.get_or_404(service_id)
        waiting = waiting_entries_for(service_id)
        serving = QueueEntry.query.filter_by(
            service_id=service_id, status=QueueEntry.STATUS_SERVING
        ).first()
        return jsonify(
            {
                "service": service.to_dict(),
                "serving": serving.to_dict() if serving else None,
                "waiting": [
                    {
                        **e.to_dict(),
                        "position": idx + 1,
                        "estimated_wait_seconds": round(idx * service.avg_service_time, 1),
                    }
                    for idx, e in enumerate(waiting)
                ],
            }
        )

    @app.post("/api/queue/join")
    def join_queue():
        data = request.get_json(force=True)
        service_id = data.get("service_id")
        name = (data.get("name") or "").strip()

        if not service_id or not name:
            return jsonify({"error": "service_id and name are required"}), 400

        service = Service.query.get(service_id)
        if not service:
            return jsonify({"error": "service not found"}), 404

        last = (
            QueueEntry.query.filter_by(service_id=service_id)
            .order_by(QueueEntry.token_number.desc())
            .first()
        )
        next_token = (last.token_number + 1) if last else 1

        entry = QueueEntry(
            service_id=service_id,
            name=name,
            token_number=next_token,
            status=QueueEntry.STATUS_WAITING,
        )
        db.session.add(entry)
        db.session.commit()

        broadcast_queue_state(service_id)

        waiting = waiting_entries_for(service_id)
        pos = position_of(entry, waiting)
        return jsonify(
            {
                "entry": entry.to_dict(),
                "position": pos,
                "estimated_wait_seconds": round((pos - 1) * service.avg_service_time, 1),
            }
        ), 201

    @app.post("/api/queue/call-next")
    def call_next():
        data = request.get_json(force=True)
        service_id = data.get("service_id")
        service = Service.query.get(service_id)
        if not service:
            return jsonify({"error": "service not found"}), 404

        # 1. Finish whoever is currently being served, update the rolling average.
        current = QueueEntry.query.filter_by(
            service_id=service_id, status=QueueEntry.STATUS_SERVING
        ).first()
        if current:
            current.status = QueueEntry.STATUS_DONE
            current.finished_at = datetime.utcnow()
            if current.serving_started_at:
                actual_seconds = (current.finished_at - current.serving_started_at).total_seconds()
                service.avg_service_time = (
                    ALPHA * actual_seconds + (1 - ALPHA) * service.avg_service_time
                )

        # 2. Pull the next waiting person in.
        next_entry = (
            QueueEntry.query.filter_by(service_id=service_id, status=QueueEntry.STATUS_WAITING)
            .order_by(QueueEntry.token_number.asc())
            .first()
        )
        if next_entry:
            next_entry.status = QueueEntry.STATUS_SERVING
            next_entry.serving_started_at = datetime.utcnow()

        db.session.commit()
        state = broadcast_queue_state(service_id)
        return jsonify(state)

    @app.post("/api/queue/no-show")
    def mark_no_show():
        data = request.get_json(force=True)
        entry_id = data.get("entry_id")
        entry = QueueEntry.query.get(entry_id)
        if not entry:
            return jsonify({"error": "entry not found"}), 404

        entry.status = QueueEntry.STATUS_NO_SHOW
        entry.finished_at = datetime.utcnow()
        db.session.commit()

        state = broadcast_queue_state(entry.service_id)
        return jsonify(state)


# ---------- Socket.IO events ----------

@socketio.on("join_room")
def handle_join_room(data):
    """Client tells us which service's room it wants live updates for."""
    from flask_socketio import join_room

    service_id = data.get("service_id")
    if service_id:
        join_room(f"service_{service_id}")


app = create_app()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
