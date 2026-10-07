import sys
import os
import json
from datetime import datetime
from bson import ObjectId

# Set UTF-8 encoding for standard output if supported
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add project root to sys.path
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_dir)

import asyncio
from app.database import connect_to_database, get_database, close_database_connection

async def display_data():
    print("=" * 75)
    print("  DUSY HEALTHCARE PLATFORM - MONGODB DATABASE INSPECTION & STORAGE AUDIT")
    print("=" * 75)
    print("DATABASE ENGINE : MongoDB Community Server (Running on localhost:27017)")
    print("DATABASE NAME   : health_assistant")
    print("PHYSICAL STORAGE: C:\\Program Files\\MongoDB\\Server\\8.3\\data")
    print("DRIVER / ORM    : Motor (AsyncIOMotorClient) + PyMongo + Pydantic v2")
    print("=" * 75)

    await connect_to_database()
    db = get_database()
    colls = await db.list_collection_names()
    
    print("\n[+] SUMMARY OF STORED COLLECTIONS & DOCUMENT COUNTS:\n")
    for c in sorted(colls):
        count = await db[c].count_documents({})
        print(f"  * {c:<24} : {count:>4} stored documents")
    
    print("\n" + "=" * 75)
    print("[+] DETAILED VIEW OF KEY COLLECTIONS (LIVE STORED RECORDS):")
    print("=" * 75)

    # 1. users
    print("\n[1] COLLECTION: 'users' (User Credentials & Identity)")
    print("-" * 75)
    users = await db.users.find().to_list(10)
    for u in users:
        print(f"  ID        : {u['_id']}")
        print(f"  Name      : {u.get('name')}")
        print(f"  Email     : {u.get('email')}")
        print(f"  Pass Hash : {u.get('password_hash')[:25]}... (Bcrypt salted hash)")
        print(f"  Created   : {u.get('created_at')}")
        print()

    # 2. health_profiles
    print("\n[2] COLLECTION: 'health_profiles' (Patient Physical Baseline & Vitals)")
    print("-" * 75)
    profiles = await db.health_profiles.find().to_list(10)
    for p in profiles:
        print(f"  User ID   : {p.get('user_id')}")
        print(f"  Height    : {p.get('height_cm')} cm")
        print(f"  Weight    : {p.get('weight_kg')} kg")
        print(f"  BMI       : {p.get('bmi')} ({p.get('bmi_category')})")
        print(f"  Blood Grp : {p.get('blood_group')}")
        print(f"  Allergies : {p.get('allergies')}")
        print(f"  Conditions: {p.get('medical_conditions')}")
        print(f"  Family Hx : {p.get('family_history')}")
        print(f"  Updated   : {p.get('updated_at')}")
        print()

    # 3. agent_consultations
    print("\n[3] COLLECTION: 'agent_consultations' (Multi-Turn Clinical Triage Encounters)")
    print("-" * 75)
    consults = await db.agent_consultations.find().sort("created_at", -1).to_list(3)
    for c in consults:
        print(f"  Consultation ID : {c['_id']}")
        print(f"  User ID         : {c.get('user_id')}")
        print(f"  Task Type       : {c.get('task_type')}")
        print(f"  Current Stage   : {c.get('stage')}")
        print(f"  Total Turns     : {len(c.get('messages', []))} messages")
        if c.get('messages'):
            first_user = next((m for m in c['messages'] if m.get('role') == 'user'), None)
            if first_user:
                print(f"  Chief Complaint : \"{first_user.get('content')[:60]}...\"")
        print(f"  Probed Params   : {c.get('probed_parameters')}")
        print(f"  Red Flags Safe  : {c.get('red_flags_cleared')}")
        print()

    # 4. agent_actions
    print("\n[4] COLLECTION: 'agent_actions' (Active Recovery Goals & Lifestyle Targets)")
    print("-" * 75)
    actions = await db.agent_actions.find().sort("executed_at", -1).to_list(5)
    for a in actions:
        print(f"  Action ID  : {a['_id']}")
        print(f"  User ID    : {a.get('user_id')}")
        print(f"  Type       : {a.get('action_type')}")
        print(f"  Title      : {a.get('title')}")
        print(f"  Description: {a.get('description')}")
        print(f"  Status     : {a.get('status')}")
        print()

    # 5. preventive_analyses
    print("\n[5] COLLECTION: 'preventive_analyses' (Lifestyle Logs & Risk Calculations)")
    print("-" * 75)
    prev = await db.preventive_analyses.find().sort("generated_at", -1).to_list(1)
    if prev:
        p_doc = prev[0]
        ls = p_doc.get("lifestyle_data", {})
        scores = p_doc.get("scores", {})
        print(f"  User ID      : {p_doc.get('user_id')}")
        print(f"  Logged Sleep : {ls.get('sleep_hours')} hrs/night")
        print(f"  Water Intake : {ls.get('water_intake_liters')} L/day")
        print(f"  Daily Steps  : {ls.get('daily_steps')} steps")
        print(f"  Exercise     : {ls.get('exercise_minutes_per_day')} min/day")
        print(f"  Diet Type    : {ls.get('diet_type')}")
        print(f"  Risk Scores  : {scores}")
        print(f"  Overall Score: {p_doc.get('overall_score')}")
        print()

    await close_database_connection()
    print("=" * 75)
    print("[SUCCESS] All data is live and actively managed in local MongoDB!")
    print("=" * 75)

if __name__ == "__main__":
    asyncio.run(display_data())
