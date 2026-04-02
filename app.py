import streamlit as st
import pandas as pd
import pymongo
import io
import pytz
import calendar
from datetime import datetime

# ==========================================
# 1. Database Initialization (MongoDB)
# ==========================================
@st.cache_resource
def init_connection():
    return pymongo.MongoClient(st.secrets["MONGO_URI"])

client = init_connection()
db = client['kinihara_timesheet']
def init_db():
    users_coll = db['users']
    if users_coll.count_documents({}) == 0:
        initial_users = [
            {"name": "Sangeeta", "pin": "0000", "role": "hr", "monthly_salary": 18000.0, "working_days": 26, "standard_hours": 8.0, "security_deposit": 0.0},
            {"name": "Om", "pin": "1111", "role": "staff", "monthly_salary": 18000.0, "working_days": 26, "standard_hours": 8.0, "security_deposit": 0.0},
            {"name": "Umesh", "pin": "2222", "role": "staff", "monthly_salary": 18000.0, "working_days": 26, "standard_hours": 8.0, "security_deposit": 0.0},
            {"name": "Nilesh", "pin": "3333", "role": "staff", "monthly_salary": 18000.0, "working_days": 26, "standard_hours": 8.0, "security_deposit": 0.0},
            {"name": "Abhishek", "pin": "4444", "role": "staff", "monthly_salary": 18000.0, "working_days": 26, "standard_hours": 8.0, "security_deposit": 0.0}
        ]
        users_coll.insert_many(initial_users)

init_db()

def get_users():
    cursor = db.users.find({}, {"_id": 0, "name": 1, "pin": 1, "role": 1, "monthly_salary": 1, "working_days": 1, "standard_hours": 1, "security_deposit": 1})
    df = pd.DataFrame(list(cursor))
    return df

def get_staff_names():
    names = db.users.distinct("name")
    return names

def check_pin(name, pin):
    user = db.users.find_one({"name": name})
    if user and user.get("pin") == pin:
        return True, user.get("role")
    return False, None

# ==========================================
# 2. Page Configuration & Setup
# ==========================================
st.set_page_config(page_title="Salary Calculator Portal", page_icon=":material/account_balance_wallet:", layout="centered")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif !important;
    }
    
    /* Center aligning main block like a standard SaaS website */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 3rem !important;
        max-width: 800px;
    }
    
    /* Make Metric container stack nicely on very small screens */
    @media (max-width: 600px) {
        div[data-testid="stMetricValue"] {
            font-size: 1.8rem;
        }
    }
    
    /* Customizing Tabs for a pill-like structure */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        padding-bottom: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 500;
        background-color: transparent;
        border: 1px solid #e2e8f0;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #f1f5f9;
        border-bottom-color: transparent;
    }

    /* Beautifying Metric Cards */
    div[data-testid="stMetricValue"] {
        font-size: 2.2rem;
        font-weight: 600;
    }
    
    div[data-testid="stMetricLabel"] {
        font-size: 1.05rem;
        font-weight: 500;
        opacity: 0.85;
    }
    
    /* Rounded Inputs & Buttons */
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
        border-radius: 8px;
    }
    
    button {
        border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

if "hr_logged_in" not in st.session_state:
    st.session_state.hr_logged_in = False
if "hr_name" not in st.session_state:
    st.session_state.hr_name = ""

st.title(":material/account_balance_wallet: Dual-Interface Salary Portal")

tab_staff, tab_hr = st.tabs([":material/badge: Staff Portal", ":material/admin_panel_settings: HR Portal"])

# ==========================================
# 3. Staff Portal (Attendance)
# ==========================================
with tab_staff:
    st.header("Staff Attendance")
    st.markdown("Please log your daily check-in and check-out times.")
    
    staff_names = get_staff_names()
    
    with st.container(border=True):
        col_staff1, col_staff2 = st.columns([2, 1])
        with col_staff1:
            if staff_names:
                employee_name = st.selectbox("Select Your Name", staff_names, key="staff_name_select")
            else:
                st.error("No staff found. HR needs to add staff.")
                employee_name = None
                
        with col_staff2:
            pin = st.text_input("Enter your PIN", type="password", max_chars=4, help="Ask HR for your PIN if you don't know it.")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button(":material/login: Check In", type="primary", use_container_width=True) and employee_name:
                valid, role = check_pin(employee_name, pin)
                if not valid:
                    st.error("Invalid PIN. Please try again.")
                else:
                    ist = pytz.timezone('Asia/Kolkata')
                    now = datetime.now(ist)
                    current_time = now.strftime("%H:%M:%S")
                    date_val = now.strftime("%Y-%m-%d")    
                    month_val = now.strftime("%B")         
                    year_val = now.strftime("%Y")          
                    day_val = now.strftime("%A")           
                    
                    open_shifts = db.attendance.find({
                        "name": employee_name, 
                        "check_out": {"$in": [None, ""]}, 
                        "date_val": {"$ne": date_val}
                    })
                    for shift in open_shifts:
                        db.attendance.update_one(
                            {"_id": shift["_id"]}, 
                            {"$set": {"check_out": "18:30:00", "remark": "Auto-checkout (Forgot)"}}
                        )
                    
                    today_shift = db.attendance.find_one({"name": employee_name, "date_val": date_val})
                    
                    if today_shift and today_shift.get("check_in"):
                        st.warning(f"You checked in today at {today_shift['check_in']}.")
                    else:
                        doc = {
                            "name": employee_name,
                            "date_val": date_val,
                            "month_val": month_val,
                            "year_val": year_val,
                            "day_val": day_val,
                            "check_in": current_time,
                            "check_out": "",
                            "work_hours": 0.0,
                            "ot_hours": 0.0,
                            "remark": "",
                            "absent": "No"
                        }
                        db.attendance.insert_one(doc)
                        st.success(f"{employee_name} checked in successfully at {current_time}! Please remember to check out.")

        with col_btn2:
            if st.button(":material/logout: Check Out", type="secondary", use_container_width=True) and employee_name:
                valid, role = check_pin(employee_name, pin)
                if not valid:
                    st.error("Invalid PIN. Please try again.")
                else:
                    ist = pytz.timezone('Asia/Kolkata')
                    now = datetime.now(ist)
                    current_time = now.strftime("%H:%M:%S")
                    date_val = now.strftime("%Y-%m-%d")
                    
                    today_shift = db.attendance.find_one({"name": employee_name, "date_val": date_val})
                    
                    if not today_shift:
                        st.error("No Check-In record found for today. Please Check In first.")
                    elif today_shift.get("check_out"): 
                        st.warning(f"You already checked out today at {today_shift['check_out']}.")
                    else:
                        doc_id = today_shift["_id"]
                        check_in_time_str = today_shift.get("check_in", "")
                        
                        fmt = "%H:%M:%S"
                        try:
                            t1 = datetime.strptime(check_in_time_str, fmt)
                            t2 = datetime.strptime(current_time, fmt)
                            tdelta = t2 - t1
                            work_hours = tdelta.total_seconds() / 3600.0
                            if work_hours < 0:
                                work_hours += 24.0 
                        except:
                            work_hours = 0.0
                            
                        db.attendance.update_one(
                            {"_id": doc_id},
                            {"$set": {"check_out": current_time, "work_hours": work_hours}}
                        )
                        st.success(f"{employee_name} checked out successfully at {current_time}! Work Hours Logged: {work_hours:.2f} hrs.")

# ==========================================
# 4. Shared Salary Processing Function
# ==========================================
def render_salary_dashboard(df, target_employee, monthly_salary, working_days, standard_hours_per_day, security_deposit=0.0):
    if df.empty:
        st.info(f"No attendance records found to process.")
        return

    st.success(f"Processing {len(df)} records for {target_employee}.")
    
    working_col = 'work_hours' if 'work_hours' in df.columns else 'Worked_Hours'
    ot_col = 'ot_hours' if 'ot_hours' in df.columns else 'OT_Hours'
    
    if working_col not in df.columns: df[working_col] = 0.0
    if ot_col not in df.columns: df[ot_col] = 0.0
    
    df.fillna(0, inplace=True)
    
    def parse_hours(val):
        if pd.isna(val) or val == 0: return 0.0
        if isinstance(val, str):
            try:
                td = pd.to_timedelta(val)
                return td.total_seconds() / 3600.0
            except:
                return 0.0
        return float(val)

    df['Parsed_Work_Hrs'] = df[working_col].apply(parse_hours).abs()
    df['Parsed_OT_Hrs'] = df[ot_col].apply(parse_hours).abs()
    
    def compute_ot(row):
        if row['Parsed_Work_Hrs'] > standard_hours_per_day:
            return row['Parsed_Work_Hrs'] - standard_hours_per_day
        return row['Parsed_OT_Hrs'] 
    
    df['Parsed_OT_Hrs'] = df.apply(compute_ot, axis=1)

    actual_worked_hours = df['Parsed_Work_Hrs'].sum()
    total_ot_hours = df['Parsed_OT_Hrs'].sum()
    
    if working_days <= 0 or standard_hours_per_day <= 0:
        st.error("Working Days and Standard Hours must be greater than 0.")
        return
        
    # 30-Day Fixed Salary Math with 2-Decimal Precision
    per_day_salary = round(monthly_salary / 30.0, 2)
    per_day_sd = round(security_deposit / 30.0, 2)
    
    # Calculate days present (count based on check-in existence rather than parseable hours)
    if 'check_in' in df.columns:
        days_present = df[df['check_in'].notna() & (df['check_in'] != '')]['date_val'].nunique()
    else:
        days_present = df['date_val'].nunique()
    
    # Calculate Earned Proportions
    earned_salary = round(per_day_salary * days_present, 2)
    earned_sd = round(per_day_sd * days_present, 2)
    total_earned = round(earned_salary + earned_sd, 2)
        
    # Professional Tax (PT) Calculation
    # PT is 200 every month, except February where it is 300
    pt_deduction = 0.0
    if not df.empty:
        first_month_recorded = df['month_val'].iloc[0].strip().lower()
        if first_month_recorded == "february":
            pt_deduction = 300.0
        else:
            pt_deduction = 200.0
        
    ot_pay = round(total_ot_hours * 50.0, 2)
    final_salary = round(total_earned - pt_deduction + ot_pay, 2)
    
    # UI Card Wrapper for Metrics
    with st.container(border=True):
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("Earned Basic Pay", f"₹ {earned_salary:,.2f}")
        with col_m2:
            st.metric("Earned Sec. Deposit", f"₹ {earned_sd:,.2f}")
        with col_m3:
            st.metric("PT Deduction", f"₹ {-pt_deduction:,.2f}")
        with col_m4:
            st.metric("Final Payable", f"₹ {final_salary:,.2f}")
        
    df['record_date'] = pd.to_datetime(df['date_val'], errors='coerce')
    df['Month '] = df['record_date'].dt.strftime('%B')
        
    export_mapping = {
        'name': 'Name',
        'date_val': 'Date',
        'year_val': 'Year ',
        'day_val': 'Day ',
        'check_in': 'Check In',
        'check_out': 'Check Out',
        'Parsed_Work_Hrs': 'Working Hrs.', 
        'work_hours': 'Work Hours', 
        'Parsed_OT_Hrs': 'OT',
        'remark': 'Remark ',
        'absent': 'Absent '
    }
    
    safe_mapping = {k: v for k, v in export_mapping.items() if v not in df.columns}
    df_mapped = df.rename(columns=safe_mapping)
    
    exact_columns = [
        'Name', 'Date', 'Month ', 'Year ', 'Day ', 'Check In', 
        'Check Out', 'Working Hrs.', 'Work Hours', 'OT', 'Remark ', 'Absent '
    ]
    
    for col in exact_columns:
        if col not in df_mapped.columns:
            df_mapped[col] = ""
            
    df_export = df_mapped[exact_columns]
    
    st.markdown("### Export Preview")
    st.dataframe(df_export, use_container_width=True)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Timesheet')
        # Calculate absent days for the export
        absent_days = max(0, 30 - days_present)
        
        # Fine/Security with KINI = earned_sd (the SD component earned for present days)
        fine_security_kini = earned_sd
        
        # Earn Gross = Earned Salary + OT + Fine/Security
        earn_gross = round(earned_salary + ot_pay + fine_security_kini, 2)
        
        # Total Deduction = Absent penalty (absent_days * per_day_salary) + PT
        total_deduction = round(pt_deduction, 2)
        
        # Net Payable = Earn Gross - Total Deduction = final_salary we already computed
        net_payable = final_salary
        
        summary_df = pd.DataFrame([{
            "Sr No": 1,
            "Employee Name": target_employee,
            "Male/ Female": "",
            "Fixed days in Month": 30,
            "Paid Pay": days_present,
            "Fixed Salary": monthly_salary,
            "Basic": monthly_salary,
            "Fixed Gross": monthly_salary,
            "Security Deposit": security_deposit,
            "OT": ot_pay,
            "Incentive": 0,
            "Compensation": 0,
            "Diwali Bon": 0,
            "Fine/Security with KINI": fine_security_kini,
            "Earn Gross": earn_gross,
            "Absent": absent_days,
            "PT": pt_deduction,
            "TDS": 0,
            "Fine": 0,
            "Total Deduction": total_deduction,
            "Advance": 0,
            "Net Payable": net_payable
        }])
        summary_df.to_excel(writer, index=False, sheet_name='Summary')
    
    processed_data = output.getvalue()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    export_filename = f"KINIHARA_Timesheet_{target_employee}_{timestamp}.xlsx"
    
    st.download_button(
        label=f":material/download: Download {target_employee} Timesheet",
        data=processed_data,
        file_name=export_filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

# ==========================================
# 5. HR Portal (Gatekeeping & Management)
# ==========================================
with tab_hr:
    if not st.session_state.hr_logged_in:
        st.header(":material/lock: HR Security Portal")
        st.markdown("Only authorized HR personnel can access these tools.")
        
        with st.container(border=True):
            hr_users = db.users.find({"role": "hr"})
            hr_names = [user['name'] for user in hr_users]
            
            
            if not hr_names:
                st.error("No HR Admin found in database. Please initialize the DB properly.")
            else:
                hr_name = st.selectbox("Select HR Admin", hr_names, key="hr_name_select")
                hr_pin = st.text_input("Enter HR PIN", type="password", key="hr_pin_input")
                
                if st.button(":material/login: Login as HR", type="primary"):
                    valid, role = check_pin(hr_name, hr_pin)
                    if valid and role == "hr":
                        st.session_state.hr_logged_in = True
                        st.session_state.hr_name = hr_name
                        st.rerun()
                    else:
                        st.error("Access Denied. Invalid PIN.")
    
    if st.session_state.hr_logged_in:
        st.sidebar.header(f":material/manage_accounts: Welcome, {st.session_state.hr_name}")
        if st.sidebar.button(":material/logout: Logout", type="secondary"):
            st.session_state.hr_logged_in = False
            st.rerun()
            
        st.sidebar.divider()
        st.header(":material/dashboard: HR Management Dashboard")

        hr_sub_tabs = st.tabs([":material/analytics: Salary Calculations", ":material/groups: Staff Management", ":material/folder_open: Manual Overrides"])
        
        with hr_sub_tabs[0]:
            st.subheader("Live Employee Calculations")
            st.markdown("Edit Check In/Out fields below to correct mistakes. Click **Save Edits** to recalculate.")
            target_employee = st.selectbox("Select Employee to Calculate", staff_names)
            
            ist = pytz.timezone('Asia/Kolkata')
            curr_month = datetime.now(ist).strftime("%B")
            curr_year = datetime.now(ist).strftime("%Y")
            months = list(calendar.month_name)[1:]
            
            col_f1, col_f2 = st.columns(2)
            with col_f1: 
                target_month = st.selectbox("Select Month", months, index=months.index(curr_month) if curr_month in months else 0)
            with col_f2: 
                years = [str(y) for y in range(2024, 2030)]
                target_year = st.selectbox("Select Year", years, index=years.index(curr_year) if curr_year in years else 1)
            
            month_index = months.index(target_month) + 1
            num_days = calendar.monthrange(int(target_year), month_index)[1]
            all_dates = [f"{target_year}-{month_index:02d}-{day:02d}" for day in range(1, num_days + 1)]
            all_dates_df = pd.DataFrame({'date_val': all_dates})
            
            cursor = db.attendance.find({
                "name": target_employee, 
                "month_val": target_month, 
                "year_val": target_year
            }, {"_id": 1, "date_val": 1, "check_in": 1, "check_out": 1, "remark": 1})
            
            db_df = pd.DataFrame(list(cursor))
            if not db_df.empty:
                db_df['_id'] = db_df['_id'].astype(str)
                df = pd.merge(all_dates_df, db_df, on='date_val', how='left')
            else:
                df = all_dates_df.copy()
                df['_id'] = ""
                df['check_in'] = ""
                df['check_out'] = ""
                df['remark'] = ""
                
            df.fillna("", inplace=True)
            df.sort_values("date_val", inplace=True)
            
            edited_df = st.data_editor(
                df,
                column_config={
                    "_id": None,
                    "date_val": st.column_config.TextColumn("Date", disabled=True),
                    "check_in": st.column_config.TextColumn("Check In (HH:MM:SS)"),
                    "check_out": st.column_config.TextColumn("Check Out (HH:MM:SS)"),
                    "remark": st.column_config.TextColumn("Remark")
                },
                hide_index=True,
                num_rows="dynamic",
                use_container_width=True
            )
            
            check1 = df.fillna("").astype(str)
            check2 = edited_df.fillna("").astype(str)
            
            if not check1.equals(check2):
                from bson.objectid import ObjectId
                from datetime import datetime as dt
                
                for index, row in edited_df.iterrows():
                    db_id = str(row.get('_id', '')).strip() if pd.notna(row.get('_id')) else ""
                    new_ci = str(row.get('check_in', '')).strip() if pd.notna(row.get('check_in')) else ""
                    new_co = str(row.get('check_out', '')).strip() if pd.notna(row.get('check_out')) else ""
                    new_remark = str(row.get('remark', '')).strip() if pd.notna(row.get('remark')) else ""
                    date_val = str(row['date_val'])
                    
                    work_hours = 0.0
                    if new_ci != "" and new_co != "":
                        fmt = "%H:%M:%S"
                        try:
                            t1 = datetime.strptime(new_ci, fmt)
                            t2 = datetime.strptime(new_co, fmt)
                            tdelta = t2 - t1
                            work_hours = tdelta.total_seconds() / 3600.0
                            if work_hours < 0:
                                work_hours += 24.0
                        except:
                            work_hours = 0.0
                            
                    if db_id and db_id.lower() != 'nan':
                        db.attendance.update_one(
                            {"_id": ObjectId(db_id)},
                            {"$set": {
                                "check_in": new_ci, 
                                "check_out": new_co, 
                                "work_hours": work_hours, 
                                "remark": new_remark
                            }}
                        )
                    elif new_ci or new_co or new_remark:
                        try:
                            day_name = dt.strptime(date_val, "%Y-%m-%d").strftime("%A")
                        except:
                            day_name = ""
                            
                        db.attendance.insert_one({
                            "name": target_employee,
                            "date_val": date_val,
                            "day_val": day_name,
                            "month_val": target_month,
                            "year_val": target_year,
                            "check_in": new_ci,
                            "check_out": new_co,
                            "work_hours": work_hours,
                            "remark": new_remark
                        })
                
                st.toast("Timesheet Auto-Saved!")
                st.rerun()

            full_cursor = db.attendance.find({
                "name": target_employee, 
                "month_val": target_month, 
                "year_val": target_year
            })
            full_df = pd.DataFrame(list(full_cursor))
            if not full_df.empty:
                full_df['_id'] = full_df['_id'].astype(str)
            
            user_vars = db.users.find_one({"name": target_employee})
            if not user_vars: 
                user_vars = {"monthly_salary": 18000.0, "working_days": 26, "standard_hours": 8.0, "security_deposit": 0.0}
            monthly_salary = float(user_vars.get("monthly_salary", 18000.0))
            working_days = int(user_vars.get("working_days", 26))
            standard_hours_per_day = float(user_vars.get("standard_hours", 8.0))
            security_deposit = float(user_vars.get("security_deposit", 0.0))
            
            render_salary_dashboard(full_df, target_employee, monthly_salary, working_days, standard_hours_per_day, security_deposit)

        with hr_sub_tabs[1]:
            st.subheader("Manage Staff & PINs")
            
            st.markdown("#### Individual Staff Data")
            st.markdown("Edit fields directly in the table below. Changes auto-save instantly.")
            users_df = get_users()
            edited_users = st.data_editor(
                users_df, 
                use_container_width=True, 
                hide_index=True,
                disabled=["name"] # Prevent changing primary keys directly
            )
            
            check1 = users_df.fillna("").astype(str)
            check2 = edited_users.fillna("").astype(str)
            
            if not check1.equals(check2):
                for _, row in edited_users.iterrows():
                    db.users.update_one(
                        {"name": row['name']},
                        {"$set": {
                            "pin": row['pin'], 
                            "role": row['role'], 
                            "monthly_salary": float(row['monthly_salary']), 
                            "working_days": int(row['working_days']), 
                            "standard_hours": float(row['standard_hours']), 
                            "security_deposit": float(row['security_deposit'])
                        }}
                    )
                st.toast("Staff table auto-saved!")
                st.rerun()
            
            with st.expander("Add New User"):
                with st.form("add_user_form", clear_on_submit=True):
                    col_f1, col_f2, col_f3 = st.columns(3)
                    with col_f1: new_name = st.text_input("Exact Name")
                    with col_f2: new_pin = st.text_input("PIN (4 digits)", max_chars=4)
                    with col_f3: new_role = st.selectbox("Role", ["staff", "hr"])
                    
                    col_v1, col_v2 = st.columns(2)
                    with col_v1: new_salary = st.number_input("Monthly Salary", value=18000.0, step=1000.0)
                    with col_v2: new_days = st.number_input("Working Days", value=26)
                    
                    col_v3, col_v4 = st.columns(2)
                    with col_v3: new_hrs = st.number_input("Standard Hrs/Day", value=8.0, step=0.5)
                    with col_v4: new_sd = st.number_input("Base Security Deposit", value=0.0, step=500.0)
                    
                    submit_user = st.form_submit_button("Save New User")
                    
                    if submit_user:
                        if len(new_pin) != 4:
                            st.error("PIN must be exactly 4 digits.")
                        elif not new_name:
                            st.error("Name cannot be empty.")
                        else:
                            ext = db.users.find_one({"name": new_name})
                            if ext:
                                db.users.update_one(
                                    {"name": new_name},
                                    {"$set": {
                                        "pin": new_pin, "role": new_role, 
                                        "monthly_salary": new_salary, "working_days": new_days, 
                                        "standard_hours": new_hrs, "security_deposit": new_sd
                                    }}
                                )
                                st.success(f"Updated {new_name}'s Profile Settings.")
                            else:
                                db.users.insert_one({
                                    "name": new_name, "pin": new_pin, "role": new_role, 
                                    "monthly_salary": new_salary, "working_days": new_days, 
                                    "standard_hours": new_hrs, "security_deposit": new_sd
                                })
                                st.success(f"Added {new_name} as {new_role}.")
                            st.rerun()
                            
            with st.expander("Remove User"):
                with st.form("delete_user_form"):
                    del_name = st.selectbox("Select User to remove", staff_names)
                    del_submit = st.form_submit_button("Remove User")
                    if del_submit:
                        if del_name == st.session_state.hr_name:
                            st.error("You cannot delete your own account while logged in!")
                        else:
                            db.users.delete_one({"name": del_name})
                            st.success(f"Removed user {del_name}")
                            st.rerun()

        with hr_sub_tabs[2]:
            st.subheader("Manual Timesheet Override")
            st.markdown("Run calculations securely on external files without updating the live database.")
            uploaded_file = st.file_uploader("Upload External Timesheet", type=["csv", "xlsx"])
            if uploaded_file is not None:
                try:
                    if uploaded_file.name.endswith('.csv'):
                        man_df = pd.read_csv(uploaded_file)
                    else:
                        man_df = pd.read_excel(uploaded_file)
                        
                    render_salary_dashboard(man_df, "External User", 18000.0, 26, 8.0, 0.0)
                except Exception as e:
                    st.error(f"Error reading file format: {e}")
