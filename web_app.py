"""
CampusConnect: Modern Web & Mobile Application Backend (Flask REST API)
Exposes complete lost & found management, smart algorithmic matching,
claims verification, notifications, and analytics to the responsive PWA frontend.
"""

import os
import sys
import json
import base64
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from flask import (
    Flask, request, jsonify, render_template, send_from_directory,
    session, redirect, url_for, make_response
)

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.connection import DEFAULT_DB_PATH, init_database, seed_default_admin
from database.repository import (
    UserRepository, ItemRepository, ClaimRepository, NotificationRepository
)
from models.user import User
from models.item import Item
from models.claim import Claim
from services.auth_service import AuthService, AuthenticationError, RegistrationError
from services.claim_service import ClaimService, ClaimWorkflowError
from services.matching_service import MatchingService
from services.notification_service import NotificationService
from services.image_service import ImageService
from analytics.metrics import AnalyticsMetrics

# Flask App Configuration
app = Flask(
    __name__,
    template_folder=os.path.join(PROJECT_ROOT, "web", "templates"),
    static_folder=os.path.join(PROJECT_ROOT, "web", "static")
)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "campusconnect_ultra_secure_dev_key_2026")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB

# Initialize Core Services
db_path = DEFAULT_DB_PATH
init_database(db_path)
seed_default_admin(db_path)

user_repo = UserRepository(db_path)
item_repo = ItemRepository(db_path)
claim_repo = ClaimRepository(db_path)
notif_repo = NotificationRepository(db_path)

auth_service = AuthService(user_repo=user_repo)
matching_service = MatchingService(db_path=db_path)
claim_service = ClaimService(item_repo=item_repo, claim_repo=claim_repo, user_repo=user_repo, db_path=db_path)
notif_service = NotificationService(db_path=db_path)
image_service = ImageService()
analytics_metrics = AnalyticsMetrics(db_path=db_path)


# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------

def get_current_user() -> Optional[User]:
    """Retrieve logged in user from session."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    return user_repo.get_by_id(user_id)


def require_auth(func):
    """Decorator to require login."""
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"success": False, "error": "Authentication required"}), 401
        return func(user, *args, **kwargs)
    return wrapper


def require_admin(func):
    """Decorator to require administrator privileges."""
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user or user.role != "admin":
            return jsonify({"success": False, "error": "Administrator privileges required"}), 403
        return func(user, *args, **kwargs)
    return wrapper


def serialize_item(item: Item, viewer_id: Optional[int] = None) -> Dict[str, Any]:
    """Serialize Item model to dictionary with match summary."""
    owner = user_repo.get_by_id(item.user_id) if item.user_id else None
    
    # Calculate smart matches count for open items
    match_count = 0
    if item.status == "OPEN":
        matches = matching_service.find_matches_for_item(item, min_threshold=50.0, limit=5)
        match_count = len(matches)

    return {
        "id": item.id,
        "type": item.type,
        "user_id": item.user_id,
        "owner_name": owner.full_name if owner else "Unknown",
        "owner_role": owner.role if owner else "student",
        "title": item.title,
        "category": item.category,
        "description": item.description,
        "event_date": item.event_date,
        "location": item.location,
        "image_path": item.image_path,
        "status": item.status,
        "created_at": item.created_at,
        "match_count": match_count,
        "is_owner": viewer_id == item.user_id if viewer_id else False
    }


# ---------------------------------------------------------
# Frontend & Static PWA Routes
# ---------------------------------------------------------

@app.route("/")
def index():
    """Serve main Single Page Application."""
    return render_template("index.html")


@app.route("/manifest.json")
def manifest():
    """Serve PWA manifest."""
    return send_from_directory(os.path.join(PROJECT_ROOT, "web", "static"), "manifest.json", mimetype="application/manifest+json")


@app.route("/sw.js")
def service_worker():
    """Serve Service Worker."""
    response = make_response(send_from_directory(os.path.join(PROJECT_ROOT, "web", "static"), "sw.js"))
    response.headers["Content-Type"] = "application/javascript"
    response.headers["Service-Worker-Allowed"] = "/"
    return response


@app.route("/assets/uploads/<path:filename>")
def uploaded_file(filename):
    """Serve uploaded item images."""
    upload_dir = os.path.join(PROJECT_ROOT, "assets", "uploads")
    return send_from_directory(upload_dir, filename)


# ---------------------------------------------------------
# Authentication API
# ---------------------------------------------------------

@app.route("/api/auth/me", methods=["GET"])
def api_auth_me():
    """Get current active session user."""
    user = get_current_user()
    if not user:
        return jsonify({"authenticated": False, "user": None})

    unread_notifs = notif_service.list_user_notifications(user.id, unread_only=True)
    return jsonify({
        "authenticated": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "unread_count": len(unread_notifs)
        }
    })


@app.route("/api/auth/demo-users", methods=["GET"])
def api_auth_demo_users():
    """Return all available demo users for 1-click viva/demo switching."""
    users = user_repo.list_all()
    demo_list = []
    for u in users:
        demo_list.append({
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name,
            "role": u.role,
            "email": u.email
        })
    return jsonify({"success": True, "users": demo_list})


@app.route("/api/auth/switch", methods=["POST"])
def api_auth_switch():
    """Instant switch to another demo user without credential re-entry."""
    data = request.get_json() or {}
    user_id = data.get("user_id")
    target_user = user_repo.get_by_id(user_id) if user_id else None

    if not target_user:
        return jsonify({"success": False, "error": "Target user not found"}), 404

    session["user_id"] = target_user.id
    session["username"] = target_user.username
    session["role"] = target_user.role

    unread = notif_service.list_user_notifications(target_user.id, unread_only=True)
    return jsonify({
        "success": True,
        "user": {
            "id": target_user.id,
            "username": target_user.username,
            "full_name": target_user.full_name,
            "email": target_user.email,
            "role": target_user.role,
            "unread_count": len(unread)
        }
    })


@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    """Authenticate with username or email and password."""
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username:
        return jsonify({"success": False, "error": "Username or campus email is required."}), 400
    if not password:
        return jsonify({"success": False, "error": "Password is required."}), 400

    try:
        user = auth_service.authenticate(username, password)
        session["user_id"] = user.id
        session["username"] = user.username
        session["role"] = user.role

        unread = notif_service.list_user_notifications(user.id, unread_only=True)
        return jsonify({
            "success": True,
            "message": f"Welcome back, {user.full_name}!",
            "user": {
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role,
                "unread_count": len(unread)
            }
        })
    except AuthenticationError as e:
        return jsonify({"success": False, "error": str(e)}), 401


@app.route("/api/auth/register", methods=["POST"])
def api_auth_register():
    """Register a new student or admin account and authenticate them."""
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip()
    role = data.get("role", "student").strip().lower()
    if role not in ("student", "admin"):
        role = "student"

    if not full_name:
        return jsonify({"success": False, "error": "Full name is required."}), 400
    if not username:
        return jsonify({"success": False, "error": "Username is required (min 3 alphanumeric characters)."}), 400
    if not email:
        return jsonify({"success": False, "error": "Valid campus email is required."}), 400
    if not password:
        return jsonify({"success": False, "error": "Password is required (min 6 characters)."}), 400

    try:
        new_user = auth_service.register_user(
            username=username,
            password=password,
            full_name=full_name,
            email=email,
            role=role
        )
        session["user_id"] = new_user.id
        session["username"] = new_user.username
        session["role"] = new_user.role

        return jsonify({
            "success": True,
            "message": f"Account created! Welcome to CampusConnect, {new_user.full_name}.",
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "full_name": new_user.full_name,
                "email": new_user.email,
                "role": new_user.role,
                "unread_count": 0
            }
        }), 201
    except (RegistrationError, ValueError) as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Registration failed: {str(e)}"}), 500


@app.route("/api/auth/logout", methods=["POST"])
def api_auth_logout():
    """Clear session."""
    session.clear()
    return jsonify({"success": True, "message": "Successfully logged out."})


# ---------------------------------------------------------
# Items Management & Search API
# ---------------------------------------------------------

@app.route("/api/items", methods=["GET"])
def api_list_items():
    """Filter and list items with comprehensive search."""
    user = get_current_user()
    viewer_id = user.id if user else None

    item_type = request.args.get("type")
    if item_type in ("ALL", "", None):
        item_type = None

    category = request.args.get("category")
    if category in ("ALL", "", None):
        category = None

    status = request.args.get("status")
    if status in ("ALL", "", None):
        status = None

    keyword = request.args.get("search") or request.args.get("keyword")
    location = request.args.get("location")
    only_mine = request.args.get("mine") == "true"

    user_id_filter = viewer_id if only_mine else None
    limit = int(request.args.get("limit", 100))
    offset = int(request.args.get("offset", 0))

    items = item_repo.list_items(
        item_type=item_type,
        category=category,
        status=status,
        location=location,
        keyword=keyword,
        user_id=user_id_filter,
        limit=limit,
        offset=offset
    )

    serialized = [serialize_item(it, viewer_id=viewer_id) for it in items]
    return jsonify({
        "success": True,
        "count": len(serialized),
        "items": serialized
    })


@app.route("/api/items/<int:item_id>", methods=["GET"])
def api_get_item(item_id: int):
    """Retrieve detailed information for a single item."""
    user = get_current_user()
    viewer_id = user.id if user else None

    item = item_repo.get_by_id(item_id)
    if not item:
        return jsonify({"success": False, "error": "Item not found"}), 404

    data = serialize_item(item, viewer_id=viewer_id)
    return jsonify({"success": True, "item": data})


@app.route("/api/items", methods=["POST"])
@require_auth
def api_create_item(user: User):
    """Create a new Lost or Found item report."""
    # Check if multipart or JSON
    if request.is_json:
        payload = request.get_json() or {}
        image_data = payload.get("image_base64")
        saved_image_path = None

        if image_data:
            try:
                # Format: data:image/jpeg;base64,...
                if "," in image_data:
                    header, encoded = image_data.split(",", 1)
                else:
                    encoded = image_data

                raw_bytes = base64.b64decode(encoded)
                unique_name = f"item_{uuid.uuid4().hex[:12]}.jpg"
                upload_dir = os.path.join(PROJECT_ROOT, "assets", "uploads")
                os.makedirs(upload_dir, exist_ok=True)
                dest = os.path.join(upload_dir, unique_name)

                with open(dest, "wb") as f:
                    f.write(raw_bytes)

                saved_image_path = f"assets/uploads/{unique_name}"
            except Exception as e:
                print(f"[WARN] Failed to save base64 image: {e}")

        item_type = payload.get("type", "LOST").upper()
        title = payload.get("title", "").strip()
        category = payload.get("category", "Electronics")
        description = payload.get("description", "").strip()
        event_date = payload.get("event_date") or datetime.now().strftime("%Y-%m-%d")
        location = payload.get("location", "").strip()
    else:
        # Form data + optional file upload
        item_type = request.form.get("type", "LOST").upper()
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "Electronics")
        description = request.form.get("description", "").strip()
        event_date = request.form.get("event_date") or datetime.now().strftime("%Y-%m-%d")
        location = request.form.get("location", "").strip()
        saved_image_path = None

        if "photo" in request.files:
            file = request.files["photo"]
            if file and file.filename:
                ext = Path(file.filename).suffix.lower()
                unique_name = f"item_{uuid.uuid4().hex[:12]}{ext}"
                upload_dir = os.path.join(PROJECT_ROOT, "assets", "uploads")
                os.makedirs(upload_dir, exist_ok=True)
                dest = os.path.join(upload_dir, unique_name)
                file.save(dest)
                saved_image_path = f"assets/uploads/{unique_name}"

    try:
        new_item = Item(
            id=None,
            type=item_type,
            user_id=user.id,
            title=title,
            category=category,
            description=description,
            event_date=event_date,
            location=location,
            image_path=saved_image_path,
            status="OPEN"
        )
        new_id = item_repo.create(new_item)
        new_item.id = new_id

        # Trigger automatic smart matching alerts!
        created_alerts = []
        try:
            alerts = notif_service.scan_and_alert_matches(new_item, min_threshold=55.0)
            created_alerts = [a.id for a in alerts]
        except Exception as e:
            print(f"[WARN] Error running auto-match scan: {e}")

        return jsonify({
            "success": True,
            "message": f"Successfully reported {item_type} item!",
            "item_id": new_id,
            "matches_triggered": len(created_alerts)
        }), 201

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/items/<int:item_id>", methods=["DELETE"])
@require_auth
def api_delete_item(user: User, item_id: int):
    """Delete an item report (only owner or admin)."""
    item = item_repo.get_by_id(item_id)
    if not item:
        return jsonify({"success": False, "error": "Item not found"}), 404

    if item.user_id != user.id and user.role != "admin":
        return jsonify({"success": False, "error": "You do not have permission to delete this report."}), 403

    try:
        item_repo.delete(item_id)
        return jsonify({"success": True, "message": f"Item #{item_id} deleted successfully."})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ---------------------------------------------------------
# Smart Algorithmic Matching API
# ---------------------------------------------------------

@app.route("/api/items/<int:item_id>/matches", methods=["GET"])
def api_item_matches(item_id: int):
    """Calculate and return ranked algorithmic matches for this item with breakdown."""
    user = get_current_user()
    viewer_id = user.id if user else None

    item = item_repo.get_by_id(item_id)
    if not item:
        return jsonify({"success": False, "error": "Item not found"}), 404

    min_threshold = float(request.args.get("threshold", 30.0))
    limit = int(request.args.get("limit", 10))

    matches = matching_service.find_matches_for_item(item, min_threshold=min_threshold, limit=limit)
    
    match_list = []
    for m in matches:
        target = m.target_item
        owner = user_repo.get_by_id(target.user_id) if target.user_id else None
        
        match_list.append({
            "target_item": {
                "id": target.id,
                "type": target.type,
                "title": target.title,
                "category": target.category,
                "description": target.description,
                "location": target.location,
                "event_date": target.event_date,
                "image_path": target.image_path,
                "status": target.status,
                "owner_name": owner.full_name if owner else "Anonymous"
            },
            "overall_score": round(m.overall_score, 1),
            "category_score": round(m.category_score * 100, 1),
            "keyword_score": round(m.text_score * 100, 1),
            "text_score": round(m.text_score * 100, 1),
            "location_score": round(m.location_score * 100, 1),
            "date_score": round(m.date_score * 100, 1),
            "explanation": m.explanation,
            "reasons": m.reasons if hasattr(m, "reasons") else []
        })

    return jsonify({
        "success": True,
        "source_item": serialize_item(item, viewer_id=viewer_id),
        "count": len(match_list),
        "matches": match_list
    })


# ---------------------------------------------------------
# Claims Management API
# ---------------------------------------------------------

@app.route("/api/claims", methods=["GET"])
@require_auth
def api_list_claims(user: User):
    """List claims. If admin: lists all/pending. If student: lists student's submitted claims."""
    status_filter = request.args.get("status")
    
    if user.role == "admin":
        claims = claim_repo.list_all(status=status_filter)
    else:
        claims = claim_repo.list_by_claimant(user.id)
        if status_filter:
            claims = [c for c in claims if c.status == status_filter]

    serialized = []
    for c in claims:
        item = item_repo.get_by_id(c.item_id)
        claimant = user_repo.get_by_id(c.claimant_id)
        reviewer = user_repo.get_by_id(c.reviewed_by) if c.reviewed_by else None

        serialized.append({
            "id": c.id,
            "item_id": c.item_id,
            "item_title": item.title if item else "Unknown Item",
            "item_category": item.category if item else "Unknown",
            "item_location": item.location if item else "",
            "item_image_path": item.image_path if item else None,
            "claimant_id": c.claimant_id,
            "claimant_name": claimant.full_name if claimant else "Unknown",
            "claimant_email": claimant.email if claimant else "",
            "proof_description": c.proof_description,
            "status": c.status,
            "verification_notes": getattr(c, "review_notes", "") or getattr(c, "verification_notes", "") or "",
            "reviewed_by_name": reviewer.full_name if reviewer else None,
            "created_at": getattr(c, "submitted_at", "") or getattr(c, "created_at", "") or "",
            "reviewed_at": c.reviewed_at
        })

    return jsonify({
        "success": True,
        "count": len(serialized),
        "claims": serialized
    })


@app.route("/api/claims", methods=["POST"])
@require_auth
def api_submit_claim(user: User):
    """Submit an ownership claim on a found item with distinguishing proof."""
    data = request.get_json() or {}
    item_id = data.get("item_id")
    proof_description = data.get("proof_description", "").strip()

    if not item_id:
        return jsonify({"success": False, "error": "Item ID is required"}), 400

    try:
        claim = claim_service.submit_claim(
            item_id=int(item_id),
            claimant_id=user.id,
            proof_description=proof_description
        )
        return jsonify({
            "success": True,
            "message": "Ownership claim submitted successfully. Campus administrators have been alerted.",
            "claim_id": claim.id
        }), 201
    except (ValueError, ClaimWorkflowError) as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/claims/<int:claim_id>/review", methods=["POST"])
@require_admin
def api_review_claim(admin_user: User, claim_id: int):
    """Approve or reject a claim with verification notes (admin only)."""
    data = request.get_json() or {}
    action = data.get("action", "").lower()
    notes = data.get("notes", "").strip()

    try:
        if action == "approve":
            claim_service.approve_claim(
                claim_id=claim_id,
                reviewer_id=admin_user.id,
                verification_notes=notes or "Identity and distinguishing proof confirmed."
            )
            return jsonify({"success": True, "message": "Claim approved! Item status set to RETURNED and claimant notified."})
        elif action == "reject":
            claim_service.reject_claim(
                claim_id=claim_id,
                reviewer_id=admin_user.id,
                reason=notes or "Proof description did not sufficiently match item distinguishing features.",
                verification_notes=notes or "Proof description did not sufficiently match item distinguishing features."
            )
            return jsonify({"success": True, "message": "Claim rejected. Item restored to OPEN status and claimant notified."})
        else:
            return jsonify({"success": False, "error": "Action must be 'approve' or 'reject'"}), 400
    except (ValueError, ClaimWorkflowError) as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to process claim review: {str(e)}"}), 500


# ---------------------------------------------------------
# Notifications & Smart Alerts API
# ---------------------------------------------------------

@app.route("/api/notifications", methods=["GET"])
@require_auth
def api_list_notifications(user: User):
    """Fetch notifications for logged in user."""
    unread_only = request.args.get("unread") == "true"
    limit = int(request.args.get("limit", 50))

    notifs = notif_service.list_user_notifications(user.id, unread_only=unread_only, limit=limit)
    unread_count = len([n for n in notifs if not n.is_read]) if not unread_only else len(notifs)

    serialized = []
    for n in notifs:
        serialized.append({
            "id": n.id,
            "user_id": n.user_id,
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "related_item_id": n.related_item_id,
            "is_read": bool(n.is_read),
            "created_at": n.created_at
        })

    return jsonify({
        "success": True,
        "unread_count": unread_count,
        "notifications": serialized
    })


@app.route("/api/notifications/<int:notif_id>/read", methods=["POST"])
@require_auth
def api_mark_notification_read(user: User, notif_id: int):
    """Mark single notification as read."""
    notif_service.mark_read(notif_id)
    return jsonify({"success": True})


@app.route("/api/notifications/read-all", methods=["POST"])
@require_auth
def api_mark_all_notifications_read(user: User):
    """Mark all notifications as read for current user."""
    count = notif_service.mark_all_read(user.id)
    return jsonify({"success": True, "updated_count": count})


# ---------------------------------------------------------
# Analytics & Export API
# ---------------------------------------------------------

@app.route("/api/analytics", methods=["GET"])
def api_get_analytics():
    """Retrieve operational metrics, recovery rate, category breakdowns, and hotspots."""
    kpis = analytics_metrics.get_summary_kpis()
    cat_dist = analytics_metrics.get_category_distribution()
    loc_hotspots = analytics_metrics.get_location_hotspots(top_n=6)
    status_dist = analytics_metrics.get_status_distribution()

    return jsonify({
        "success": True,
        "kpis": kpis,
        "categories": cat_dist.to_dict() if hasattr(cat_dist, "to_dict") else {},
        "locations": loc_hotspots.to_dict() if hasattr(loc_hotspots, "to_dict") else {},
        "statuses": status_dist.to_dict() if hasattr(status_dist, "to_dict") else {}
    })


@app.route("/api/export/csv", methods=["GET"])
def api_export_csv():
    """Export current items catalog as CSV file."""
    import io
    import csv

    items = item_repo.list_items(limit=1000)
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(["ID", "Type", "Title", "Category", "Description", "Location", "Event Date", "Status", "Reported At"])
    for it in items:
        writer.writerow([
            it.id, it.type, it.title, it.category, it.description,
            it.location, it.event_date, it.status, it.created_at
        ])

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=campus_connect_items.csv"
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    return response


# ---------------------------------------------------------
# Main Launcher
# ---------------------------------------------------------

def run_server(port: int = 5000, host: str = "0.0.0.0", debug: bool = False):
    """Launch Flask web server."""
    print("\n========================================================")
    print("   CampusConnect Modern Web & Mobile App Server")
    print("========================================================")
    print(f" [URL] Local Website & Mobile PWA: http://localhost:{port}")
    print(f" [NET] Access from Phone on Wi-Fi: http://<Your-IP>:{port}")
    print(" [OK]  Features: PWA Installable, Real-Time AI Matches, Demo Switcher")
    print("========================================================\n")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CampusConnect Modern Web App")
    parser.add_argument("--port", type=int, default=5000, help="Port to run server on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    run_server(port=args.port, host=args.host, debug=args.debug)
