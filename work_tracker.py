import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
import gspread
from google.oauth2.service_account import Credentials


# ----Google sheet set up----
SHEET_ID = "1uU1e7GNVH4ZYxTiNZ49jF9GIbdR9eyn44Lxg7cfdz9g"
SHEET_NAME = "Hours Logged"
HEADERS = ["Date", "Start Time", "End Time", "Break Start", "Break End", "Work Duration (hrs)"]

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(st.secrets["google"],scopes=SCOPES)
client = gspread.authorize(creds)
worksheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# ----Constants----
PAY_PERIOD_START = datetime(2025, 9, 8).date()
PAY_PERIOD_LENGTH = 14
TARGET_HOURS = 60

# ----Helper functions----
def format_hours_minutes(hours_float):
    sign = "-" if hours_float < 0 else ""
    total_minutes = int(round(abs(hours_float) * 60))
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{sign}{hours}h {minutes}m"

def make_serializable(val):
    if pd.isna(val):
        return ""
    if isinstance(val, (datetime, pd.Timestamp, pd.Timedelta)):
        return str(val)
    if isinstance(val, (time,)):
        return val.strftime("%H:%M")
    return val

def load_data():
    """Load the latest data from the Google Sheet into a DataFrame."""
    records = worksheet.get_all_records()
    df = pd.DataFrame(records)
    if not df.empty:
        df["Date"] = pd.to_datetime(df["Date"]).dt.date
    else:
        df = pd.DataFrame(columns=["Date", "Start Time", "End Time", "Break Start", "Break End", "Work Duration (hrs)"])
    return df

# ----Load data from Google sheets----
df = load_data()

# ----Streamlit app----
# title
st.title("Work Time Tracker")

# Input form
st.subheader("Log New Work Entry")
with st.form("log_form"):
    date = st.date_input("Date")
    start_time = st.time_input("Start Time", value=time(9, 0))
    end_time = st.time_input("End Time", value=time(16, 0))
    break_start = st.time_input("Break Start", value=time(0, 0))
    break_end = st.time_input("Break End", value=time(0, 0))
    submitted = st.form_submit_button("Log Work")

if submitted:
    start_dt = datetime.combine(date, start_time)
    end_dt = datetime.combine(date, end_time)
    break_start_dt = datetime.combine(date, break_start)
    break_end_dt = datetime.combine(date, break_end)
    work_duration = (end_dt - start_dt - (break_end_dt - break_start_dt)).total_seconds() / 3600

    new_entry = {
        "Date": date.strftime("%Y-%m-%d"),
        "Start Time": start_time.strftime("%H:%M"),
        "End Time": end_time.strftime("%H:%M"),
        "Break Start": break_start.strftime("%H:%M"),
        "Break End": break_end.strftime("%H:%M"),
        "Work Duration (hrs)": round(work_duration, 2)
    }

    # ---- Append new row only----
    worksheet.append_rows([make_serializable(v) for v in new_entry.values()])

    # ---- Reload the full sheet----
    df = load_data()

    st.success(f"Logged {round(work_duration, 2)} hours for {date.strftime('%Y-%m-%d')}")


# Optional: show total and remaining hours in current pay period
st.write(f"Total logged: {df['Work Duration (hrs)'].astype(float).sum():.2f} hrs")
remaining = TARGET_HOURS - df['Work Duration (hrs)'].astype(float).sum()
st.write(f"Remaining to reach {TARGET_HOURS} hrs target: {format_hours_minutes(remaining)}")

# --- Summary statistics ---
# if not df.empty:
#     total_hours = df["Work Duration (hrs)"].astype(float).sum()
#     st.write(f"**Total logged:** {total_hours:.2f} hrs")
#
#     remaining = TARGET_HOURS - total_hours
#     st.write(f"**Remaining to reach {TARGET_HOURS} hrs target:** {format_hours_minutes(remaining)}")


# --- Display current data ---
# st.subheader("Logged Hours")
# st.dataframe(df.sort_values(df.columns[0], ascending=False))
# # Reverse logs
# df = df.sort_values(by="Date", ascending=False)
#
# # Pay period summary
# today = datetime.now().date()
# days_since_start = (today - PAY_PERIOD_START).days
# current_period_index = days_since_start // PAY_PERIOD_LENGTH
# current_period_start = PAY_PERIOD_START + timedelta(days=current_period_index * PAY_PERIOD_LENGTH)
# current_period_end = current_period_start + timedelta(days=PAY_PERIOD_LENGTH - 1)
#
# current_period_df = df[(df["Date"] >= current_period_start) & (df["Date"] <= current_period_end)]
# current_total_hours = current_period_df["Work Duration (hrs)"].sum()
# current_overtime = current_total_hours - TARGET_HOURS

# st.subheader("Current Pay Period Summary")
# st.write(f"**Period:** {current_period_start} to {current_period_end}")
# st.write(f"**Total Hours:** {format_hours_minutes(current_total_hours)}")
# st.write(f"**Overtime:** {format_hours_minutes(current_overtime)}")
#
# # Completed pay periods
# completed_periods = []
# for i in range(current_period_index):
#     period_start = PAY_PERIOD_START + timedelta(days=i * PAY_PERIOD_LENGTH)
#     period_end = period_start + timedelta(days=PAY_PERIOD_LENGTH - 1)
#     period_df = df[(df["Date"] >= period_start) & (df["Date"] <= period_end)]
#     total_hours = period_df["Work Duration (hrs)"].sum()
#     overtime = total_hours - TARGET_HOURS
#     completed_periods.append({
#         "Period Start": period_start,
#         "Period End": period_end,
#         "Total Hours": format_hours_minutes(total_hours),
#         "Overtime": format_hours_minutes(overtime)
#     })
#
# if completed_periods:
#     st.subheader("Summary of Completed Pay Periods")
#     summary_df = pd.DataFrame(completed_periods)
#     st.dataframe(summary_df)
#
# # Export
# st.subheader("Export Work Log")
# csv_data = df.to_csv(index=False).encode("utf-8")
# st.download_button("Download work_log.csv", data=csv_data, file_name="work_log.csv", mime="text/csv")
#
# # Display logs
# st.subheader("Logged Work Entries (Newest First)")
# st.dataframe(df)
#
# # Edit/Delete
# st.subheader("Edit or Delete Existing Entry")
# if not df.empty:
#     selected_date = st.selectbox("Select a date to edit/delete", sorted(df["Date"].unique(), reverse=True))
#     entry = df[df["Date"] == selected_date].iloc[0]
#
#     with st.form("edit_form"):
#         new_start = st.time_input("Start Time", value=datetime.strptime(entry["Start Time"], "%H:%M").time())
#         new_end = st.time_input("End Time", value=datetime.strptime(entry["End Time"], "%H:%M").time())
#         new_break_start = st.time_input("Break Start", value=datetime.strptime(entry["Break Start"], "%H:%M").time())
#         new_break_end = st.time_input("Break End", value=datetime.strptime(entry["Break End"], "%H:%M").time())
#         update = st.form_submit_button("Update Entry")
#         delete = st.form_submit_button("Delete Entry")
#
#     if update:
#         start_dt = datetime.combine(selected_date, new_start)
#         end_dt = datetime.combine(selected_date, new_end)
#         break_start_dt = datetime.combine(selected_date, new_break_start)
#         break_end_dt = datetime.combine(selected_date, new_break_end)
#         work_duration = (end_dt - start_dt - (break_end_dt - break_start_dt)).total_seconds() / 3600
#
#         df.loc[df["Date"] == selected_date, ["Start Time", "End Time", "Break Start", "Break End", "Work Duration (hrs)"]] = [
#             new_start.strftime("%H:%M"),
#             new_end.strftime("%H:%M"),
#             new_break_start.strftime("%H:%M"),
#             new_break_end.strftime("%H:%M"),
#             round(work_duration, 2)
#         ]
#         worksheet.clear()
#         worksheet.update([df.columns.values.tolist()] + df.values.tolist())
#         st.success(f"Updated entry for {selected_date}")
#
#     if delete:
#         df = df[df["Date"] != selected_date]
#         worksheet.clear()
#         worksheet.update([df.columns.values.tolist()] + df.values.tolist())
#         st.success(f"Deleted entry for {selected_date}")