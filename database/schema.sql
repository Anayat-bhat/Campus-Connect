-- CampusConnect: SQLite Relational Database Schema
-- Defines normalized tables, constraints, foreign keys, and indexes.

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- 1. USERS TABLE
-- Stores authenticated student and administrator accounts.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL CHECK(role IN ('student', 'admin')) DEFAULT 'student',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ----------------------------------------------------------------------------
-- 2. ITEMS TABLE
-- Stores both LOST and FOUND items reported on campus.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK(type IN ('LOST', 'FOUND')),
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN (
        'Electronics',
        'Books and stationery',
        'Identity cards',
        'Accessories',
        'Personal belongings',
        'Other'
    )),
    description TEXT NOT NULL,
    event_date TEXT NOT NULL,          -- Date item was lost or found (YYYY-MM-DD)
    location TEXT NOT NULL,
    image_path TEXT,                   -- Path to saved local image if uploaded
    status TEXT NOT NULL CHECK(status IN (
        'OPEN',                        -- Unresolved report
        'CLAIM_PENDING',               -- Claim currently submitted/under review
        'RETURNED',                    -- Claim approved and item returned to owner
        'CLOSED'                       -- Cancelled by reporter or expired
    )) DEFAULT 'OPEN',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- 3. CLAIMS TABLE
-- Allows a student to claim ownership of a reported found item.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    claimant_id INTEGER NOT NULL,
    proof_description TEXT NOT NULL,   -- Hidden distinguishing detail (e.g., sticker, scratch)
    status TEXT NOT NULL CHECK(status IN ('PENDING', 'APPROVED', 'REJECTED')) DEFAULT 'PENDING',
    submitted_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    reviewed_at TEXT,
    reviewed_by INTEGER,
    review_notes TEXT,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
    FOREIGN KEY (claimant_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL
);

-- ----------------------------------------------------------------------------
-- 4. ITEM_RETURNS TABLE
-- Auditable record of completed returns after a claim is approved.
-- Ensures an item cannot be returned more than once.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS item_returns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL UNIQUE,   -- UNIQUE prevents duplicate returns of the same item
    claim_id INTEGER NOT NULL UNIQUE,  -- UNIQUE binds return to the specific approved claim
    handed_over_by INTEGER NOT NULL,   -- Admin or student who handed the item over
    received_by INTEGER NOT NULL,      -- Verified claimant who received the item
    return_date TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    verification_notes TEXT,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
    FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE,
    FOREIGN KEY (handed_over_by) REFERENCES users(id) ON DELETE RESTRICT,
    FOREIGN KEY (received_by) REFERENCES users(id) ON DELETE RESTRICT
);

-- ----------------------------------------------------------------------------
-- 5. PERFORMANCE INDEXES
-- Optimize searching, filtering, and foreign key join lookups.
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_items_type_status ON items(type, status);
CREATE INDEX IF NOT EXISTS idx_items_category ON items(category);
CREATE INDEX IF NOT EXISTS idx_items_location ON items(location);
CREATE INDEX IF NOT EXISTS idx_items_date ON items(event_date);
CREATE INDEX IF NOT EXISTS idx_items_user_id ON items(user_id);
CREATE INDEX IF NOT EXISTS idx_claims_item_id ON claims(item_id);
CREATE INDEX IF NOT EXISTS idx_claims_claimant_id ON claims(claimant_id);
CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
