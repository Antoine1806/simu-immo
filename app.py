import streamlit as st
import pandas as pd
import numpy as np

# Set page configuration
st.set_page_config(page_title="Multi-Scenario Investment Simulator", layout="wide")

st.title("🏡 Multi-Scenario Real Estate & Wealth Simulator")
st.write("Combine loan, rent, and stock market modules to evaluate and compare financial strategies over time.")

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("⚙️ Global Parameters")
horizon_years = st.sidebar.slider("Simulation Horizon (Years)", min_value=5, max_value=35, value=20, step=1)
property_appreciation_rate = st.sidebar.slider("Annual Property Appreciation (%)", min_value=0.0, max_value=8.0, value=2.0, step=0.5) / 100

def render_scenario_builder(scenario_label: str, key_prefix: str, default_buy: bool, default_rent: bool):
    """Renders grouped modules for a scenario in the sidebar and returns parameter dictionary."""
    st.sidebar.subheader(f"📊 {scenario_label}")
   
    # --- MODULE 1: TAKE A LOAN ---
    with st.sidebar.expander("🏦 Take a Loan", expanded=default_buy):
        enable_loan = st.checkbox("Enable Loan Module", value=default_buy, key=f"{key_prefix}_loan_active")
        if enable_loan:
            prop_price = st.number_input("Property Price (€)", min_value=10000, value=250000, step=5000, key=f"{key_prefix}_price")
            down_payment = st.number_input("Down Payment / Initial Cash (€)", min_value=0, value=50000, step=5000, key=f"{key_prefix}_down")
            interest_rate = st.number_input("Annual Interest Rate (%)", min_value=0.1, max_value=15.0, value=3.5, step=0.1, key=f"{key_prefix}_rate")
            loan_term = st.number_input("Repayment Time (Years)", min_value=1, max_value=35, value=20, step=1, key=f"{key_prefix}_term")
        else:
            prop_price, down_payment, interest_rate, loan_term = 0, 0, 0, 0

    # --- MODULE 2: RENT ---
    with st.sidebar.expander("🔑 Rent", expanded=default_rent):
        enable_rent = st.checkbox("Enable Rent Module", value=default_rent, key=f"{key_prefix}_rent_active")
        if enable_rent:
            monthly_rent = st.number_input("Monthly Rent Cost (€)", min_value=0, value=900, step=50, key=f"{key_prefix}_rent")
            rent_duration = st.number_input("Rent Duration (Years)", min_value=1, max_value=35, value=horizon_years, step=1, key=f"{key_prefix}_rent_dur")
            annual_repairs = st.number_input("Estimated Owner/Repair Costs per Year (€)", min_value=0, value=500, step=100, key=f"{key_prefix}_repairs")
        else:
            monthly_rent, rent_duration, annual_repairs = 0, 0, 0

    # --- MODULE 3: INVEST IN STOCKS ---
    with st.sidebar.expander("📈 Invest in Stocks", expanded=True):
        enable_stocks = st.checkbox("Enable Stock Module", value=True, key=f"{key_prefix}_stock_active")
        if enable_stocks:
            stock_initial = st.number_input("Original Lump Sum (€)", min_value=0, value=10000 if default_buy else 50000, step=2500, key=f"{key_prefix}_s_init")
            stock_monthly = st.number_input("Amount Invested per Month (€)", min_value=0, value=300, step=50, key=f"{key_prefix}_s_month")
            stock_return = st.number_input("Expected Avg. Annual Growth (%)", min_value=0.0, max_value=20.0, value=7.0, step=0.5, key=f"{key_prefix}_s_ret")
        else:
            stock_initial, stock_monthly, stock_return = 0, 0, 0

    return {
        "enable_loan": enable_loan,
        "prop_price": prop_price,
        "down_payment": down_payment,
        "interest_rate": interest_rate / 100,
        "loan_term": loan_term,
        "enable_rent": enable_rent,
        "monthly_rent": monthly_rent,
        "rent_duration": rent_duration,
        "annual_repairs": annual_repairs,
        "enable_stocks": enable_stocks,
        "stock_initial": stock_initial,
        "stock_monthly": stock_monthly,
        "stock_return": stock_return / 100,
    }

# Render Sidebar Scenario Input Groups
s1_params = render_scenario_builder("Scenario A (e.g., Buy Property)", "s1", default_buy=True, default_rent=False)
st.sidebar.divider()
s2_params = render_scenario_builder("Scenario B (e.g., Rent & Invest)", "s2", default_buy=False, default_rent=True)

# --- SIMULATION ENGINE ---
def calculate_simulation(params, total_years, prop_apprec_rate):
    total_months = total_years * 12
    months = np.arange(1, total_months + 1)
   
    # Mortgage Payment Calculation
    monthly_mortgage = 0
    loan_amount = max(0, params["prop_price"] - params["down_payment"])
    if params["enable_loan"] and loan_amount > 0:
        r = params["interest_rate"] / 12
        n = params["loan_term"] * 12
        monthly_mortgage = loan_amount * (r * (1 + r)**n) / ((1 + r)**n - 1) if r > 0 else loan_amount / n

    monthly_stock_rate = (1 + params["stock_return"])**(1/12) - 1
    monthly_prop_rate = (1 + prop_apprec_rate)**(1/12) - 1

    property_val = params["prop_price"] if params["enable_loan"] else 0
    loan_balance = loan_amount if params["enable_loan"] else 0
    stock_val = params["stock_initial"] if params["enable_stocks"] else 0
   
    records = []
   
    for m in months:
        # Loan payment & Property Value updates
        if params["enable_loan"]:
            property_val *= (1 + monthly_prop_rate)
            if m <= params["loan_term"] * 12 and loan_balance > 0:
                r_loan = params["interest_rate"] / 12
                interest_pay = loan_balance * r_loan
                principal_pay = min(loan_balance, monthly_mortgage - interest_pay)
                loan_balance = max(0, loan_balance - principal_pay)
            else:
                active_mortgage = 0
        active_mortgage = monthly_mortgage if (params["enable_loan"] and m <= params["loan_term"] * 12) else 0
       
        # Rent & Maintenance updates
        active_rent = params["monthly_rent"] if (params["enable_rent"] and m <= params["rent_duration"] * 12) else 0
        active_repair = (params["annual_repairs"] / 12) if params["enable_rent"] else 0
       
        # Stock Portfolio accumulation
        if params["enable_stocks"]:
            stock_val = stock_val * (1 + monthly_stock_rate) + params["stock_monthly"]
           
        # Assets & Net Worth
        property_equity = property_val - loan_balance if params["enable_loan"] else 0
        total_net_worth = property_equity + stock_val
        total_monthly_outflow = active_mortgage + active_rent + active_repair + (params["stock_monthly"] if params["enable_stocks"] else 0)
       
        records.append({
            "Month": m,
            "Year": m / 12,
            "Property Equity (€)": property_equity,
            "Stock Portfolio (€)": stock_val,
            "Total Net Worth (€)": total_net_worth,
            "Monthly Outflow (€)": total_monthly_outflow
        })
       
    return pd.DataFrame(records)

df_s1 = calculate_simulation(s1_params, horizon_years, property_appreciation_rate)
df_s2 = calculate_simulation(s2_params, horizon_years, property_appreciation_rate)

# --- DASHBOARD SUMMARY METRICS ---
st.header("📌 Comparison Dashboard")

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Scenario A Overview")
    final_nw_a = df_s1["Total Net Worth (€)"].iloc[-1]
    avg_outflow_a = df_s1["Monthly Outflow (€)"].mean()
    st.metric("Final Net Worth", f"€{final_nw_a:,.0f}")
    st.metric("Avg. Monthly Outflow", f"€{avg_outflow_a:,.0f}")
    st.metric("Property Equity", f"€{df_s1['Property Equity (€)'].iloc[-1]:,.0f}")
    st.metric("Stock Value", f"€{df_s1['Stock Portfolio (€)'].iloc[-1]:,.0f}")

with col_b:
    st.subheader("Scenario B Overview")
    final_nw_b = df_s2["Total Net Worth (€)"].iloc[-1]
    avg_outflow_b = df_s2["Monthly Outflow (€)"].mean()
    st.metric("Final Net Worth", f"€{final_nw_b:,.0f}", delta=f"€{final_nw_b - final_nw_a:,.0f} vs A")
    st.metric("Avg. Monthly Outflow", f"€{avg_outflow_b:,.0f}", delta=f"€{avg_outflow_b - avg_outflow_a:,.0f} vs A", delta_color="inverse")
    st.metric("Property Equity", f"€{df_s2['Property Equity (€)'].iloc[-1]:,.0f}")
    st.metric("Stock Value", f"€{df_s2['Stock Portfolio (€)'].iloc[-1]:,.0f}")

st.divider()

# --- COMPARISON CHARTS ---
st.subheader("📈 Net Worth Growth Trajectory Over Time")

df_chart = pd.DataFrame({
    "Year": df_s1["Year"],
    "Scenario A Net Worth": df_s1["Total Net Worth (€)"],
    "Scenario B Net Worth": df_s2["Total Net Worth (€)"]
}).set_index("Year")

st.line_chart(df_chart)

st.subheader("💳 Monthly Cash Outflow Comparison")
df_outflow = pd.DataFrame({
    "Year": df_s1["Year"],
    "Scenario A Outflow": df_s1["Monthly Outflow (€)"],
    "Scenario B Outflow": df_s2["Monthly Outflow (€)"]
}).set_index("Year")

st.line_chart(df_outflow)

# --- DETAILED DATA TABLES ---
with st.expander("🔍 View Detailed Amortization & Investment Breakdown"):
    tab1, tab2 = st.tabs(["Scenario A Details", "Scenario B Details"])
    with tab1:
        st.dataframe(df_s1.style.format("€{:.2f}"))
    with tab2:
        st.dataframe(df_s2.style.format("€{:.2f}"))