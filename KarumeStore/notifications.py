from flask import Blueprint, jsonify
from auth import login_required, get_current_user
from models import db, Notification

notifications = Blueprint("notifications", __name__)

@notifications.get("/api/notifications")
@login_required
def get_notifications():
    user = get_current_user()
    items = Notification.query.filter_by(user_id=user.id).order_by(Notification.id.desc()).all()
    return jsonify({
        "success": True,
        "notifications": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None
            } for n in items
        ]
    })

@notifications.post("/api/notifications/<int:notification_id>/read")
@login_required
def mark_read(notification_id):
    user = get_current_user()
    item = db.session.get(Notification, notification_id)
    if not item or item.user_id != user.id:
        return jsonify({"success": False, "message": "Notification not found."}), 404
    item.is_read = True
    db.session.commit()
    return jsonify({"success": True})
