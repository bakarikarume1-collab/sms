import hmac
import os
from flask import Blueprint, jsonify, request
from models import db, IntegrationEvent

integration = Blueprint('integration', __name__)

@integration.get('/api/integration/events')
def get_events():
    token = os.environ.get('INTEGRATION_TOKEN', '')
    provided = request.headers.get('X-Integration-Token', '')
    if not token or not hmac.compare_digest(provided, token):
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 401

    try:
        after_id = int(request.args.get('after_id', 0))
        limit = min(max(int(request.args.get('limit', 20)), 1), 50)
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid parameters.'}), 400

    events = (IntegrationEvent.query
              .filter(IntegrationEvent.id > after_id)
              .order_by(IntegrationEvent.id.asc())
              .limit(limit).all())
    return jsonify({
        'success': True,
        'events': [
            {
                'id': e.id,
                'event_type': e.event_type,
                'order_id': e.order_id,
                'payload': e.payload,
                'created_at': e.created_at.isoformat() if e.created_at else None,
            } for e in events
        ]
    })
