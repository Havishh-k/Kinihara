import streamlit as st
import pandas as pd
import sqlite3
import io
import pytz
import calendar
from datetime import datetime

# ==========================================
# 1. Database Initialization (SQLite)
# ==========================================
DB_NAME = 'master_timesheet.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            date_val TEXT,
            month_val TEXT,
            year_val TEXT,
            day_val TEXT,
            check_in TEXT,
            check_out TEXT,
            work_hours REAL,
            ot_hours REAL,
            remark TEXT,
            absent TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            pin TEXT,
            role TEXT,
            monthly_salary REAL DEFAULT 18000.0,
            working_days INTEGER DEFAULT 26,
            standard_hours REAL DEFAULT 8.0,
            security_deposit REAL DEFAULT 0.0
        )
    ''')
    
    try:
        c.execute("ALTER TABLE users ADD COLUMN monthly_salary REAL DEFAULT 18000.0")
        c.execute("ALTER TABLE users ADD COLUMN working_days INTEGER DEFAULT 26")
        c.execute("ALTER TABLE users ADD COLUMN standard_hours REAL DEFAULT 8.0")
    except sqlite3.OperationalError:
        pass
        
    try:
        c.execute("ALTER TABLE users ADD COLUMN security_deposit REAL DEFAULT 0.0")
    except sqlite3.OperationalError:
        pass
        
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        initial_users = [
            ("Sangeeta", "0000", "hr"),
            ("Om", "1111", "staff"),
            ("Umesh", "2222", "staff"),
            ("Nilesh", "3333", "staff"),
            ("Abhishek", "4444", "staff")
        ]
        c.executemany("INSERT INTO users (name, pin, role) VALUES (?, ?, ?)", initial_users)
        
    conn.commit()
    conn.close()

init_db()

def get_users():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT name, pin, role, monthly_salary, working_days, standard_hours, security_deposit FROM users", conn)
    conn.close()
    return df

def get_staff_names():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT name FROM users")
    names = [row[0] for row in c.fetchall()]
    conn.close()
    return names

def check_pin(name, pin):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT pin, role FROM users WHERE name=?", (name,))
    res = c.fetchone()
    conn.close()
    if res and res[0] == pin:
        return True, res[1]
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
                    
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    
                    c.execute("SELECT id, date_val FROM attendance WHERE name=? AND check_out IS NULL AND date_val != ?", (employee_name, date_val))
                    open_shifts = c.fetchall()
                    for shift in open_shifts:
                        c.execute("UPDATE attendance SET check_out = '18:30:00', remark = 'Auto-checkout (Forgot)' WHERE id=?", (shift[0],))
                    
                    c.execute("SELECT id, check_in FROM attendance WHERE name=? AND date_val=?", (employee_name, date_val))
                    today_shift = c.fetchone()
                    
                    if today_shift and today_shift[1]:
                        st.warning(f"You checked in today at {today_shift[1]}.")
                    else:
                        c.execute('''
                            INSERT INTO attendance (name, date_val, month_val, year_val, day_val, check_in)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (employee_name, date_val, month_val, year_val, day_val, current_time))
                        st.success(f"{employee_name} checked in successfully at {current_time}! Please remember to check out.")
                    
                    conn.commit()
                    conn.close()

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
                    
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    
                    c.execute("SELECT id, check_in, check_out FROM attendance WHERE name=? AND date_val=?", (employee_name, date_val))
                    today_shift = c.fetchone()
                    
                    if not today_shift:
                        st.error("No Check-In record found for today. Please Check In first.")
                    elif today_shift[2]: 
                        st.warning(f"You already checked out today at {today_shift[2]}.")
                    else:
                        shift_id = today_shift[0]
                        check_in_time_str = today_shift[1]
                        
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
                            
                        c.execute("UPDATE attendance SET check_out=?, work_hours=? WHERE id=?", (current_time, work_hours, shift_id))
                        st.success(f"{employee_name} checked out successfully at {current_time}! Work Hours Logged: {work_hours:.2f} hrs.")
                    
                    conn.commit()
                    conn.close()

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
        
    total_working_hours = standard_hours_per_day * working_days
    per_hour_salary = monthly_salary / total_working_hours
    
    if actual_worked_hours < total_working_hours:
        missing_hours = total_working_hours - actual_worked_hours
        leave_deduction = missing_hours * per_hour_salary
    else:
        leave_deduction = 0.0
        
    # Professional Tax (PT) Calculation
    # PT is 200 every month, except February where it is 300
    pt_deduction = 0.0
    if not df.empty:
        first_month_recorded = df['month_val'].iloc[0].strip().lower()
        if first_month_recorded == "february":
            pt_deduction = 300.0
        else:
            pt_deduction = 200.0

    # Security Deposit Calculation
    # (Base Security Deposit / Standard Working Days) * Days Present
    days_present = df['date_val'].nunique()
    sd_deduction = 0.0
    if working_days > 0:
        sd_deduction = (security_deposit / working_days) * days_present
        
    total_deductions = leave_deduction + pt_deduction + sd_deduction
        
    ot_pay = total_ot_hours * 50.0
    final_salary = (monthly_salary - total_deductions) + ot_pay
    
    # UI Card Wrapper for Metrics
    with st.container(border=True):
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("Leave Deduct.", f"₹ {leave_deduction:,.2f}")
        with col_m2:
            st.metric("PT + SD Deduct.", f"₹ {(pt_deduction + sd_deduction):,.2f}")
        with col_m3:
            st.metric("Total OT Pay", f"₹ {ot_pay:,.2f}")
        with col_m4:
            st.metric("Final Payable Salary", f"₹ {final_salary:,.2f}")
        
    export_mapping = {
        'name': 'Name',
        'date_val': 'Date',
        'month_val': 'Month ',
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
        summary_df = pd.DataFrame([{
            "Employee": target_employee,
            "Base Monthly Salary": monthly_salary,
            "Actual Worked Hours": actual_worked_hours,
            "Total OT Hours": total_ot_hours,
            "Total OT Pay": ot_pay,
            "Leave Deductions": leave_deduction,
            "Professional Tax (PT)": pt_deduction,
            "Security Deposit (SD)": sd_deduction,
            "Total Deductions": total_deductions,
            "Final Payable Salary": final_salary
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
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT name FROM users WHERE role='hr'")
            hr_names = [row[0] for row in c.fetchall()]
            conn.close()
            
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
            
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT monthly_salary, working_days, standard_hours, security_deposit FROM users WHERE name=?", (target_employee,))
            user_vars = c.fetchone()
            if not user_vars: user_vars = (18000.0, 26, 8.0, 0.0)
            monthly_salary, working_days, standard_hours_per_day, security_deposit = user_vars
            
            query = "SELECT id, date_val, check_in, check_out, remark FROM attendance WHERE name=? AND month_val=? AND year_val=?"
            df = pd.read_sql_query(query, conn, params=(target_employee, target_month, target_year))
            conn.close()
            
            if df.empty:
                 st.info(f"No attendance records found to process.")
            else:
                edited_df = st.data_editor(
                    df,
                    column_config={
                        "id": None,
                        "date_val": st.column_config.TextColumn("Date", disabled=True),
                        "check_in": st.column_config.TextColumn("Check In (HH:MM:SS)"),
                        "check_out": st.column_config.TextColumn("Check Out (HH:MM:SS)"),
                        "remark": st.column_config.TextColumn("Remark")
                    },
                    hide_index=True,
                    num_rows="dynamic",
                    use_container_width=True
                )
                
                if st.button(":material/save: Save Edits & Compute Salary", type="primary"):
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    
                    for index, row in edited_df.iterrows():
                        db_id = row['id']
                        new_ci = row['check_in']
                        new_co = row['check_out']
                        new_remark = row['remark']
                        
                        work_hours = 0.0
                        if pd.notna(new_ci) and pd.notna(new_co) and new_ci != "" and new_co != "":
                            fmt = "%H:%M:%S"
                            try:
                                t1 = datetime.strptime(str(new_ci), fmt)
                                t2 = datetime.strptime(str(new_co), fmt)
                                tdelta = t2 - t1
                                work_hours = tdelta.total_seconds() / 3600.0
                                if work_hours < 0:
                                    work_hours += 24.0
                            except:
                                work_hours = 0.0
                                
                        c.execute('''
                            UPDATE attendance 
                            SET check_in=?, check_out=?, work_hours=?, remark=?
                            WHERE id=?
                        ''', (new_ci, new_co, work_hours, new_remark, db_id))
                    
                    conn.commit()
                    
                    query_full = "SELECT * FROM attendance WHERE name=? AND month_val=? AND year_val=?"
                    full_df = pd.read_sql_query(query_full, conn, params=(target_employee, target_month, target_year))
                    conn.close()
                    
                    st.success("Changes saved! Below are the recalculated salary metrics:")
                    render_salary_dashboard(full_df, target_employee, monthly_salary, working_days, standard_hours_per_day, security_deposit)
                else:
                    st.info("Click 'Save Edits & Compute Salary' to view the final payload slip and numbers.")

        with hr_sub_tabs[1]:
            st.subheader("Manage Staff & PINs")
            users_df = get_users()
            st.dataframe(users_df, use_container_width=True, hide_index=True)
            
            with st.container(border=True):
                st.markdown("#### Add or Update User")
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
                    
                    submit_user = st.form_submit_button("Save User")
                    
                    if submit_user:
                        if len(new_pin) != 4:
                            st.error("PIN must be exactly 4 digits.")
                        elif not new_name:
                            st.error("Name cannot be empty.")
                        else:
                            conn = sqlite3.connect(DB_NAME)
                            c = conn.cursor()
                            c.execute("SELECT id FROM users WHERE name=?", (new_name,))
                            ext = c.fetchone()
                            if ext:
                                c.execute("UPDATE users SET pin=?, role=?, monthly_salary=?, working_days=?, standard_hours=?, security_deposit=? WHERE name=?", (new_pin, new_role, new_salary, new_days, new_hrs, new_sd, new_name))
                                st.success(f"Updated {new_name}'s Profile Settings.")
                            else:
                                c.execute("INSERT INTO users (name, pin, role, monthly_salary, working_days, standard_hours, security_deposit) VALUES (?, ?, ?, ?, ?, ?, ?)", (new_name, new_pin, new_role, new_salary, new_days, new_hrs, new_sd))
                                st.success(f"Added {new_name} as {new_role}.")
                            conn.commit()
                            conn.close()
                            st.rerun()
                            
            with st.container(border=True):
                st.markdown("#### Remove Staff")
                with st.form("delete_user_form"):
                    del_name = st.selectbox("Select User to remove", staff_names)
                    del_submit = st.form_submit_button("Remove User")
                    if del_submit:
                        if del_name == st.session_state.hr_name:
                            st.error("You cannot delete your own account while logged in!")
                        else:
                            conn = sqlite3.connect(DB_NAME)
                            c = conn.cursor()
                            c.execute("DELETE FROM users WHERE name=?", (del_name,))
                            conn.commit()
                            conn.close()
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
