import streamlit as st
import requests

# Set up the look and feel of the webpage
st.set_page_config(page_title="PiggyBank | Budget Tracker", page_icon="💰", layout="centered")

# Fixed: Removed the trailing forward slash at the end
BACKEND_URL = "https://personal-finance-tracker-jdj7.onrender.com"

# --- Title and App Styling ---
st.title("💰 PiggyBank")
st.subheader("Your Personal Finance & Budget Companion")
st.markdown("---")

# --- SIMULATED USER LOGIN ---
if "token" not in st.session_state:
    # Auto-register default user on backend
    requests.post(f"{BACKEND_URL}/register", json={"username": "keith", "password": "password123"})
    # Auto-login to get the token
    login_response = requests.post(f"{BACKEND_URL}/token", data={"username": "keith", "password": "password123"})
    try:
        st.session_state.token = login_response.json().get("access_token")
    except Exception:
        st.session_state.token = None

headers = {"Authorization": f"Bearer {st.session_state.token}"} if st.session_state.get("token") else {}

# --- SIDEBAR: SET MONTHLY BUDGET ---
st.sidebar.header("🎯 Set Your Budget")
budget_category = st.sidebar.selectbox("Category Budget", ["Dining Out", "Groceries", "Entertainment", "Transport", "Bills"])
# Changed label to Peso sign (₱)
budget_limit = st.sidebar.number_input("Monthly Limit (₱)", min_value=1.0, value=200.0, step=10.0)

if st.sidebar.button("Save Budget", use_container_width=True):
    payload = {"category": budget_category, "monthly_limit": budget_limit}
    res = requests.post(f"{BACKEND_URL}/budgets", json=payload, headers=headers)
    if res.status_code == 200:
        # Changed display text to Peso sign (₱)
        st.sidebar.success(f"Saved! ₱{budget_limit} for {budget_category}")
        st.rerun()
    else:
        st.sidebar.error("Failed to save budget. Check backend connection.")

# --- MAIN FORM: ADD NEW EXPENSE ---
st.header("📝 Log an Expense")
with st.form("expense_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        category = st.selectbox("What category?", ["Dining Out", "Groceries", "Entertainment", "Transport", "Bills"])
    with col2:
        # Changed label to Peso sign (₱)
        amount = st.number_input("How much did you spend? (₱)", min_value=0.01, step=1.0)
        
    description = st.text_input("Description (e.g., Coffee on Tuesday, Movie Night)")
    
    # Fixed: Cleaned up the variable syntax mismatch from the original code here
    submit_button = st.form_submit_button("Add Expense to Tracker", use_container_width=True)

if submit_button:
    expense_payload = {"amount": amount, "category": category, "description": description}
    res = requests.post(f"{BACKEND_URL}/expenses", json=expense_payload, headers=headers)
    if res.status_code == 200:
        st.toast("Expense added successfully! 🎉")
        st.rerun()

# --- VISUAL ANALYTICS & WARNINGS SECTION ---
st.markdown("---")
st.header("📊 Your Financial Insights")

if headers:
    analytics_res = requests.get(f"{BACKEND_URL}/analytics", headers=headers)

    if analytics_res.status_code == 200:
        data = analytics_res.json()
        reports = data.get("category_reports", {})
        warnings = data.get("warnings", [])
        
        for warning in warnings:
            if "⚠️" in warning:
                st.error(warning)
            else:
                st.info(warning)
                
        if reports:
            cols = st.columns(len(reports))
            for idx, (cat_name, cat_data) in enumerate(reports.items()):
                with cols[idx]:
                    remaining = cat_data['remaining_balance']
                    delta_color = "normal" if remaining >= 0 else "inverse"
                    # Changed metric cards to show Peso sign (₱)
                    st.metric(
                        label=f"{cat_name} Balance", 
                        value=f"₱{remaining:.2f}", 
                        delta=f"Spent: ₱{cat_data['total_spent']:.2f}",
                        delta_color=delta_color
                    )
        else:
            st.write("No active budgets found. Setup a monthly budget in the sidebar to view insights!")
else:
    st.warning("Connecting to server... Make sure your Render backend is completely loaded.")