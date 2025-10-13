from datetime import datetime
from flask import Blueprint, Response

from ..services.backup_service import generate_db_dump
from .auth import require_token

backup_bp = Blueprint("backup", __name__)


@backup_bp.get("/backup/dump")
@require_token
def download_dump():
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    headers = {
        "Content-Disposition": f"attachment; filename=backup_{ts}.sql"
    }
    return Response(generate_db_dump(), mimetype="application/sql", headers=headers)
