import streamlit as st
import pandas as pd
import sqlite3
import io
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
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 2. Page Configuration & Setup
# ==========================================
st.set_page_config(page_title="Salary Calculator Portal", page_icon="💸", layout="wide")
st.title("💸 Dual-Interface Salary Portal")

tab_staff, tab_hr = st.tabs(["🧑‍💼 Staff Portal", "🏢 HR Portal"])

# ==========================================
# 3. Staff Portal (Attendance)
# ==========================================
with tab_staff:
    st.header("Staff Attendance")
    st.markdown("Please log your daily check-in and check-out times.")
    
    col_staff1, col_staff2 = st.columns([2, 1])
    with col_staff1:
        employee_name = st.selectbox("Select Your Name", ["Sangeeta", "Om", "Umesh", "Nilesh", "Abhishek"])
    with col_staff2:
        pin = st.text_input("Enter 4-digit PIN", type="password", max_chars=4, help="A basic 4-digit pin for validation.")
    
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("Check In", type="primary", use_container_width=True):
            if len(pin) != 4:
                st.error("Please enter a valid 4-digit PIN to Check In.")
            else:
                now = datetime.now()
                # KINIHARA Data Formatting Quirks
                current_time = now.strftime("%H:%M:%S")
                date_val = now.strftime("%Y-%m-%d")    # YYYY-MM-DD
                month_val = now.strftime("%B")         # Full month name e.g., April
                year_val = now.strftime("%Y")          # Full year e.g., 2026
                day_val = now.strftime("%A")           # Full day e.g., Tuesday
                
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                
                # "Forgot to Check Out" Edge Case
                # Find open shifts from previous days for this employee
                c.execute("SELECT id, date_val FROM attendance WHERE name=? AND check_out IS NULL AND date_val != ?", (employee_name, date_val))
                open_shifts = c.fetchall()
                for shift in open_shifts:
                    # Auto-fill 18:30:00 and flag for review
                    c.execute("UPDATE attendance SET check_out = '18:30:00', remark = 'Auto-checkout (Forgot)' WHERE id=?", (shift[0],))
                
                # Verify if already checked in today
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
        if st.button("Check Out", type="secondary", use_container_width=True):
            if len(pin) != 4:
                st.error("Please enter a valid 4-digit PIN to Check Out.")
            else:
                now = datetime.now()
                current_time = now.strftime("%H:%M:%S")
                date_val = now.strftime("%Y-%m-%d")
                
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                
                c.execute("SELECT id, check_in, check_out FROM attendance WHERE name=? AND date_val=?", (employee_name, date_val))
                today_shift = c.fetchone()
                
                if not today_shift:
                    st.error("No Check-In record found for today. Please Check In first.")
                elif today_shift[2]: # If check_out is not empty/null
                    st.warning(f"You already checked out today at {today_shift[2]}.")
                else:
                    shift_id = today_shift[0]
                    check_in_time_str = today_shift[1]
                    
                    # Auto-calculate Work Hours
                    fmt = "%H:%M:%S"
                    try:
                        t1 = datetime.strptime(check_in_time_str, fmt)
                        t2 = datetime.strptime(current_time, fmt)
                        tdelta = t2 - t1
                        work_hours = tdelta.total_seconds() / 3600.0
                        if work_hours < 0:
                            work_hours += 24.0 # Cross day boundary fix
                    except:
                        work_hours = 0.0
                        
                    c.execute("UPDATE attendance SET check_out=?, work_hours=? WHERE id=?", (current_time, work_hours, shift_id))
                    st.success(f"{employee_name} checked out successfully at {current_time}! Work Hours Logged: {work_hours:.2f} hrs.")
                
                conn.commit()
                conn.close()

# ==========================================
# 4. HR Portal (Configuration & Calculation)
# ==========================================
with tab_hr:
    st.header("Configuration Panel")
    col1, col2 = st.columns(2)

    with col1:
        monthly_salary = st.number_input("Monthly Salary", min_value=0.0, step=1000.0, value=18000.0)
        working_days = st.number_input("Total Working Days in Month", min_value=1, max_value=31, value=26)

    with col2:
        standard_hours_per_day = st.number_input("Standard Hours per Day", min_value=1.0, step=0.5, value=8.0)
        ot_rate_multiplier = st.selectbox("OT Rate Multiplier", options=[1.5, 2.0], help="1.5x for standard OT, 2.0x for Sundays/Holidays")
        # Ensure we ask HR exactly which employee's salary to calculate
        target_employee = st.selectbox("Select Employee to Calculate for", ["Sangeeta", "Om", "Umesh", "Nilesh", "Abhishek"])

    st.divider()
    st.header("Manual Timesheet Override (Optional)")
    st.markdown("By default, the engine loads data from the live Master Database. Upload a `.csv` only if you need to calculate an offline legacy file.")
    uploaded_file = st.file_uploader("Upload legacy timesheet (.csv) (Overrides Live Database)", type=["csv"])

    st.divider()
    calculate_btn = st.button("Calculate Salary & Prepare Export", type="primary", use_container_width=True)

    if calculate_btn:
        try:
            # --- Data Ingestion ---
            df = None
            if uploaded_file is not None:
                # Fallback to manual file
                df = pd.read_csv(uploaded_file)
                st.info("Using manually uploaded legacy CSV file for calculations.")
            else:
                # Primary Source: SQLite Master Database
                conn = sqlite3.connect(DB_NAME)
                query = "SELECT * FROM attendance WHERE name=?"
                df = pd.read_sql_query(query, conn, params=(target_employee,))
                conn.close()
                st.info(f"Loaded {len(df)} live records for {target_employee} from the Master Database.")
            
            if df.empty:
                st.error("No data found to process.")
            else:
                # Pre-processing to normalize Work Hours / OT Hours columns
                # Legacy CSV vs SQLite might have slight column name variations, map them generally
                working_col = 'work_hours' if 'work_hours' in df.columns else 'Worked_Hours'
                ot_col = 'ot_hours' if 'ot_hours' in df.columns else 'OT_Hours'
                
                # Ensure they exist in dataframe, fill with 0
                if working_col not in df.columns: df[working_col] = 0.0
                if ot_col not in df.columns: df[ot_col] = 0.0

                df.fillna(0, inplace=True)
                
                def parse_hours(val):
                    if pd.isna(val) or val == 0:
                        return 0.0
                    if isinstance(val, str):
                        try:
                            td = pd.to_timedelta(val)
                            return td.total_seconds() / 3600.0
                        except:
                            return 0.0
                    return float(val)

                df['Parsed_Work_Hrs'] = df[working_col].apply(parse_hours).abs()
                df['Parsed_OT_Hrs'] = df[ot_col].apply(parse_hours).abs()
                
                # Update our DF directly for export purposes if we are calculating missing OT
                # Assuming simple standard hours OT calculation if OT wasn't explicitly logged by Staff CheckOut
                def compute_ot(row):
                    if row['Parsed_Work_Hrs'] > standard_hours_per_day:
                        return row['Parsed_Work_Hrs'] - standard_hours_per_day
                    return row['Parsed_OT_Hrs'] # Fallback
                
                df['Parsed_OT_Hrs'] = df.apply(compute_ot, axis=1)

                actual_worked_hours = df['Parsed_Work_Hrs'].sum()
                total_ot_hours = df['Parsed_OT_Hrs'].sum()
                
                # --- Core Calculation Engine ---
                if working_days <= 0 or standard_hours_per_day <= 0:
                    st.error("Working Days and Standard Hours must be greater than 0.")
                else:
                    total_working_hours = standard_hours_per_day * working_days
                    per_hour_salary = monthly_salary / total_working_hours
                    
                    # Deductions
                    if actual_worked_hours < total_working_hours:
                        missing_hours = total_working_hours - actual_worked_hours
                        deduction = missing_hours * per_hour_salary
                    else:
                        deduction = 0.0
                        
                    # Overtime
                    ot_pay = total_ot_hours * (per_hour_salary * ot_rate_multiplier)
                    
                    # Final Salary
                    final_salary = (monthly_salary - deduction) + ot_pay
                    
                    # --- Output Visualization ---
                    st.subheader("Calculation Results")
                    col_m1, col_m2, col_m3 = st.columns(3)
                    with col_m1:
                        st.metric("Total Deductions", f"₹ {deduction:,.2f}")
                    with col_m2:
                        st.metric("Total OT Pay", f"₹ {ot_pay:,.2f}")
                    with col_m3:
                        st.metric("Final Payable Salary", f"₹ {final_salary:,.2f}")

                    # --- Strict KINIHARA Formatting & Export ---
                    # We must populate KINIHARA exact columns before exporting.
                    # 'Name', 'Date', 'Month ', 'Year ', 'Day ', 'Check In', 'Check Out', 'Working Hrs.', 'Work Hours', 'OT', 'Remark ', 'Absent '
                    # Map our internal columns to these names carefully.
                    export_mapping = {
                        'name': 'Name',
                        'date_val': 'Date',
                        'month_val': 'Month ',
                        'year_val': 'Year ',
                        'day_val': 'Day ',
                        'check_in': 'Check In',
                        'check_out': 'Check Out',
                        'Parsed_Work_Hrs': 'Working Hrs.', # Keep as representation of Float Work
                        'work_hours': 'Work Hours', # Can be duplicate or raw time string depending on system requirements
                        'Parsed_OT_Hrs': 'OT',
                        'remark': 'Remark ',
                        'absent': 'Absent '
                    }
                    
                    df_mapped = df.rename(columns=export_mapping)
                    
                    exact_columns = [
                        'Name', 'Date', 'Month ', 'Year ', 'Day ', 'Check In', 
                        'Check Out', 'Working Hrs.', 'Work Hours', 'OT', 'Remark ', 'Absent '
                    ]
                    
                    # Ensure all legacy columns exist, fill with blank if missing
                    for col in exact_columns:
                        if col not in df_mapped.columns:
                            df_mapped[col] = ""
                            
                    df_export = df_mapped[exact_columns]
                    
                    st.markdown("### Export Preview (KINIHARA Structure)")
                    st.dataframe(df_export)

                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_export.to_excel(writer, index=False, sheet_name='Timesheet')
                        
                        summary_df = pd.DataFrame([{
                            "Employee": target_employee,
                            "Base Monthly Salary": monthly_salary,
                            "Actual Worked Hours": actual_worked_hours,
                            "Total OT Hours": total_ot_hours,
                            "Total OT Pay": ot_pay,
                            "Total Deductions": deduction,
                            "Final Payable Salary": final_salary
                        }])
                        summary_df.to_excel(writer, index=False, sheet_name='Summary')
                    
                    processed_data = output.getvalue()
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
                    export_filename = f"KINIHARA_Timesheet_{target_employee}_{timestamp}.xlsx"
                    
                    st.download_button(
                        label="Download Original Timesheet Format (Excel)",
                        data=processed_data,
                        file_name=export_filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

        except Exception as e:
            st.error(f"An error occurred during calculation: {str(e)}")
