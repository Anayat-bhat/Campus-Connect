# CampusConnect: Smart Campus Lost & Found Management System

A centralized, reliable desktop application tailored for college campuses to report, track, match, and return lost personal belongings.

---

## 📌 Problem Statement
Students frequently lose personal belongings on campus (college ID cards, notebooks, calculators, earphones, keys, etc.). Most campuses rely on scattered WhatsApp messages or informal notices, leading to lost records, duplicate reports, and delayed returns. **CampusConnect** provides a structured, automated, and auditable system with intelligent text-matching algorithms to connect owners with found items.

---

## 🚀 Key Features Roadmap
- [x] **Phase 1: Project Setup & System Foundation**
- [ ] **Phase 2: SQLite Database Design & Schemas**
- [ ] **Phase 3: Data Models & CRUD Operations**
- [ ] **Phase 4: Authentication & Role-Based Access Control (Student vs Admin)**
- [ ] **Phase 5: Lost & Found Item Reporting Interfaces**
- [ ] **Phase 6: Multi-Factor Weighted Matching Algorithm**
- [ ] **Phase 7: Claim Verification & Return Tracking with DB Transactions**
- [ ] **Phase 8: Analytics Dashboard & Matplotlib Visualizations**
- [ ] **Phase 9: Comprehensive Unit Testing & Input Hardening**
- [ ] **Phase 10: Final Documentation, Presentation & Viva Preparation**

---

## 🛠️ Technology Stack
- **Language**: Python 3.10+
- **GUI Toolkit**: Tkinter & ttk (Python standard library)
- **Database**: SQLite 3 (ACID-compliant relational database)
- **Data Analytics & Charts**: Matplotlib, Pandas
- **Version Control**: Git & GitHub

---

## 📂 Architecture Overview
```text
CampusConnect/
├── main.py                  # Application entry point
├── database/                # SQLite connection, schema, and repository queries
├── models/                  # Domain entity dataclasses (User, Item, Claim)
├── services/                # Business logic (Auth, Matching, Claims, Returns)
├── gui/                     # Modular Tkinter view windows & components
├── analytics/               # Matplotlib statistics & Pandas aggregation
├── tests/                   # Automated unittest suite
├── data/                    # Local storage (gitignored database & uploads)
├── assets/                  # Icons and images
├── requirements.txt         # Project dependencies
└── .gitignore               # Ignored cache, databases, and venv
```

---

## 💻 Getting Started (Phase 1)

### 1. Clone the repository
```powershell
git clone https://github.com/Anayat-bhat/Campus-Connect.git
cd Campus-Connect
```

### 2. Create and activate a Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Run the Phase 1 Diagnostic
```powershell
python main.py
```
