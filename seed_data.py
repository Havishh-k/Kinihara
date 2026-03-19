import pymongo
import streamlit as st
import datetime
import calendar

try:
    # Try to load secrets locally if available
    secrets = st.secrets
    mongo_uri = secrets["MONGO_URI"]
except:
    import toml
    with open(".streamlit/secrets.toml", "r") as f:
        secrets = toml.load(f)
    mongo_uri = secrets["MONGO_URI"]

client = pymongo.MongoClient(mongo_uri)
db = client['kinihara_timesheet']
users_coll = db['users']
attendance_coll = db['attendance']

# Get all active user names
users = [user['name'] for user in users_coll.find({}, {"name": 1})]
print(f"Found users: {users}")

# Generate dates from March 1, 2026 to today (March 19, 2026)
start_date = datetime.date(2026, 3, 1)
end_date = datetime.date(2026, 3, 19)
delta = datetime.timedelta(days=1)

current_date = start_date
count = 0

while current_date <= end_date:
    date_val = current_date.strftime("%Y-%m-%d")
    month_val = calendar.month_name[current_date.month]
    year_val = current_date.strftime("%Y")
    day_val = current_date.strftime("%A")
    
    for name in users:
        # Check if a record already exists for this user on this exact date
        existing = attendance_coll.find_one({"name": name, "date_val": date_val})
        if not existing:
            # Insert blank record
            doc = {
                "name": name,
                "date_val": date_val,
                "month_val": month_val,
                "year_val": year_val,
                "day_val": day_val,
                "check_in": "",
                "check_out": "",
                "work_hours": 0.0,
                "ot_hours": 0.0,
                "remark": "",
                "absent": "No"
            }
            attendance_coll.insert_one(doc)
            count += 1
            print(f"Inserted record for {name} on {date_val}")
    
    current_date += delta

print(f"Seeding completed. Inserted {count} missing records.")
