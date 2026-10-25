"""
CampusConnect: Realistic Demo Data Seeder
Populates local SQLite database with realistic university lost & found reports,
ownership claims, and handover returns for demonstrations and viva presentations.
"""

import os
from database.connection import DEFAULT_DB_PATH, init_database, seed_default_admin
from database.repository import UserRepository, ItemRepository, ClaimRepository
from services.auth_service import AuthService
from services.claim_service import ClaimService
from models.item import Item


def seed_demo_data(db_path: str = DEFAULT_DB_PATH) -> None:
    """Seed sample campus users, lost/found items, claims, and returns."""
    print("[INFO] Initializing database schema...")
    init_database(db_path)
    seed_default_admin(db_path)

    user_repo = UserRepository(db_path)
    item_repo = ItemRepository(db_path)
    claim_repo = ClaimRepository(db_path)
    auth_service = AuthService(user_repo=user_repo)
    claim_service = ClaimService(item_repo=item_repo, claim_repo=claim_repo, user_repo=user_repo, db_path=db_path)

    admin = user_repo.get_by_username("admin")

    print("[INFO] Seeding student user accounts...")
    students = [
        ("aarav_sharma", "Aarav Sharma", "aarav@campus.edu", "Student@2026"),
        ("priya_verma", "Priya Verma", "priya@campus.edu", "Student@2026"),
        ("rohit_kumar", "Rohit Kumar", "rohit@campus.edu", "Student@2026"),
        ("ananya_sen", "Ananya Sen", "ananya@campus.edu", "Student@2026"),
        ("vikram_singh", "Vikram Singh", "vikram@campus.edu", "Student@2026"),
    ]

    student_objs = []
    for uname, fname, email, pwd in students:
        existing = user_repo.get_by_username(uname)
        if not existing:
            u = auth_service.register_user(uname, pwd, fname, email, role="student")
            student_objs.append(u)
        else:
            student_objs.append(existing)

    s1, s2, s3, s4, s5 = student_objs

    print("[INFO] Seeding diverse campus lost and found items...")
    demo_items = [
        # Electronics
        ("LOST", s1.id, "Apple AirPods Pro (2nd Gen)", "Electronics",
         "White wireless charging case with black silicone cover. Left on table near 2nd-floor window.", "2026-10-22", "Central Library 2nd Floor", "OPEN"),
        ("FOUND", s2.id, "AirPods Pro Wireless Case", "Electronics",
         "Found white Apple AirPods case in a black silicone sleeve on reading table.", "2026-10-22", "Central Library", "OPEN"),
        ("LOST", s3.id, "Dell 65W Type-C Laptop Charger", "Electronics",
         "Black Dell barrel-tip/Type-C charger with velcro wire tie. Left plugged into power strip.", "2026-10-23", "Computer Lab 3, Block B", "OPEN"),
        ("FOUND", s4.id, "Black Laptop Charging Adapter", "Electronics",
         "Found black Dell 65W charger in computer lab row 4.", "2026-10-23", "Block B Lab 3", "OPEN"),
        ("FOUND", s5.id, "Casio fx-991EX Scientific Calculator", "Electronics",
         "Scientific calculator with solar panel and engraved initials on protective cover.", "2026-10-24", "Engineering Block Room 204", "OPEN"),

        # Identity Cards
        ("LOST", s2.id, "Student ID Card — Priya Verma", "Identity cards",
         "B.Tech CSE student identity card with blue campus lanyard and RFID chip.", "2026-10-24", "Cafeteria Ground Floor", "OPEN"),
        ("FOUND", s1.id, "Campus ID Card Priya Verma", "Identity cards",
         "Found plastic college identity card near billing counter in cafeteria.", "2026-10-24", "Cafeteria", "OPEN"),

        # Personal belongings & Accessories
        ("LOST", s4.id, "Brown Leather Titan Watch", "Accessories",
         "Silver dial wrist watch with brown genuine leather strap. Buckle has minor scuff.", "2026-10-21", "Sports Complex Badminton Court", "OPEN"),
        ("FOUND", s3.id, "Titan Wrist Watch", "Accessories",
         "Found a gents wrist watch on spectator bench near court 2.", "2026-10-21", "Sports Complex", "OPEN"),
        ("LOST", s5.id, "Blue Milton Thermosteel Water Bottle", "Personal belongings",
         "1000ml stainless steel vacuum insulated bottle with mountain sticker.", "2026-10-25", "Block A Lecture Hall 101", "OPEN"),

        # Books and Stationery
        ("FOUND", s2.id, "Data Structures & Algorithms in Python Textbook", "Books and stationery",
         "Goodrich & Tamassia hardcover textbook with yellow highlighters on Chapter 4.", "2026-10-23", "Central Library Ground Floor", "OPEN"),
        ("FOUND", s1.id, "Black Leather Bound Planner Diary", "Books and stationery",
         "A5 diary notebook with elastic closure band and ribbon bookmark.", "2026-10-24", "Student Center", "OPEN"),
    ]

    created_items = []
    for itype, uid, title, cat, desc, dt, loc, status in demo_items:
        it = Item(None, itype, uid, title, cat, desc, dt, loc, None, status)
        it_id = item_repo.create(it)
        it.id = it_id
        created_items.append(it)

    print("[INFO] Seeding claims and return handovers...")
    calc_item = created_items[4]  # Casio calculator
    diary_item = created_items[11]  # Diary notebook

    # Record return for Casio calculator to student 3
    calc_claim = claim_service.submit_claim(
        item_id=calc_item.id,
        claimant_id=s3.id,
        proof_description="Back cover has an engraved initial 'RK' inside battery compartment."
    )
    claim_service.approve_claim(
        claim_id=calc_claim.id,
        reviewer_id=admin.id,
        verification_notes="Verified student identity and engraved initials 'RK' matched enrollment record."
    )

    # Record return for Diary to student 4
    diary_claim = claim_service.submit_claim(
        item_id=diary_item.id,
        claimant_id=s4.id,
        proof_description="First page has my email ananya@campus.edu written in blue ink."
    )
    claim_service.approve_claim(
        claim_id=diary_claim.id,
        reviewer_id=admin.id,
        verification_notes="Handed over after verifying matching contact info on title leaf."
    )

    # Active pending claim for AirPods
    airpods_found = created_items[1]
    claim_service.submit_claim(
        item_id=airpods_found.id,
        claimant_id=s1.id,
        proof_description="Engraved with initials 'A.S.' and right ear tip is size Small."
    )

    print("[INFO] Triggering smart match alert scans...")
    from services.notification_service import NotificationService
    notif_service = NotificationService(db_path=db_path)
    
    # Run scan for found items to notify lost item owners
    for item in created_items:
        if item.type == "FOUND" and item.status == "OPEN":
            notif_service.scan_and_alert_matches(item, min_threshold=55.0)

    # Seed a campus welcome notification for each student
    for st in student_objs:
        notif_service.notify(
            user_id=st.id,
            title="👋 Welcome to CampusConnect",
            message=f"Welcome {st.full_name}! Check here for real-time algorithmic match alerts and claim updates.",
            notif_type="SYSTEM"
        )

    print("[SUCCESS] Demo dataset successfully populated!")
    print(f"[SUMMARY] {len(created_items)} items, 5 student accounts, 1 pending claim queue, 2 verified returns, and active match alerts.")


if __name__ == "__main__":
    seed_demo_data()
