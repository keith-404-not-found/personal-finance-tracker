import streamlit as st
import requests

# Set up the look and feel of the webpage
st.set_page_config(page_title="PiggyBank | Budget Tracker", page_icon="💰", layout="centered")

BACKEND_URL = "http://127.0.0.1:8000"

# --- Title and App Styling ---
st.title("💰 PiggyBank")
st.subheader("Your Personal Finance & Budget Companion")
st.markdown("---")

# --- SIMULATED USER LOGIN ---
# To keep this UI clean, we auto-register/login a default user behind the scenes
if "token" not in st.session_state:
    # Auto-register default user on backend
    requests.post(f"{BACKEND_URL}/register", json={"username": "keith", "password": "password123"})
    # Auto-login to get the token
    login_response = requests.post(f"{BACKEND_URL}/token", data={"username": "keith", "password": "password123"})
    st.session_state.token = login_response.json().get("access_token")

headers = {"Authorization": f"Bearer {st.session_state.token}"}

# --- SIDEBAR: SET MONTHLY BUDGET ---
st.sidebar.header("🎯 Set Your Budget")
budget_category = st.sidebar.selectbox("Category Budget", ["Dining Out", "Groceries", "Entertainment", "Transport", "Bills"])
budget_limit = st.sidebar.number_input("Monthly Limit ($)", min_value=1.0, value=200.0, step=10.0)

if st.sidebar.button("Save Budget", use_container_width=True):
    payload = {"category": budget_category, "monthly_limit": budget_limit}
    res = requests.post(f"{BACKEND_URL}/budgets", json=payload, headers=headers)
    if res.status_code == 200:
        st.sidebar.success(f"Saved! ${budget_limit} for {budget_category}")

# --- MAIN FORM: ADD NEW EXPENSE ---
st.header("📝 Log an Expense")
with st.form("expense_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        amount = col2.number_input("How much did you spend? ($)", min_value=0.01, step=1.0)
        category = col1.selectbox("What category?", ["Dining Out", "Groceries", "Entertainment", "Transport", "Bills"])
    description = st.text_input("Description (e.g., Coffee on Tuesday, Movie Night)")
    
    submit_button = st.form_submit_with_rows = st.form_submit_button("Add Expense to Tracker", use_container_width=True)

if submit_button:
    expense_payload = {"amount": amount, "category": category, "description": description}
    res = requests.post(f"{BACKEND_URL}/expenses", json=expense_payload, headers=headers)
    if res.status_code == 200:
        st.toast("Expense added successfully! 🎉")

# --- VISUAL ANALYTICS & WARNINGS SECTION ---
st.markdown("---")
st.header("📊 Your Financial Insights")

# Fetch analytics from our FastAPI backend
analytics_res = requests.get(f"{BACKEND_URL}/analytics", headers=headers)

if analytics_res.status_code == 200:
    data = analytics_res.json()
    reports = data.get("category_reports", {})
    warnings = data.get("warnings", [])
    
    # Show Backend Warnings nicely as UI Alert Elements
    for warning in warnings:
        if "⚠️" in warning:
            st.error(warning) # Big Red Warning Alert box if over budget
        else:
            st.info(warning) # Clean Blue Informational box if safe
            
    # Display the remaining balances as clean visual cards
    if reports:
        cols = st.columns(len(reports))
        for idx, (cat_name, cat_data) in enumerate(reports.items()):
            with cols[idx]:
                remaining = cat_data['remaining_balance']
                # Green card if you have money left, red card if negative
                delta_color = "normal" if remaining >= 0 else "inverse"
                st.metric(
                    label=f"{cat_name} Balance", 
                    value=f"${remaining:.2f}", 
                    delta=f"Spent: ${cat_data['total_spent']:.2f}",
                    delta_color=delta_color
                )
    else:
        st.write("No active budgets found. Setup a monthly budget in the sidebar to view insights!")