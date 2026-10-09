import streamlit as st
import pandas as pd
import numpy as np

# Set page configuration
st.set_page_config(page_title="Multi-Scenario Investment Simulator", layout="wide")

st.title("🏡 Multi-Scenario Real Estate & Wealth Simulator")
st.write("Compare complex strategies by adding multiple loans, rentals, and stock portfolios to a single scenario.")

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("⚙️ Global Parameters")
horizon_years = st.sidebar.slider("Simulation Horizon (Years)", min_value=5, max_value=35, value=20, step=1)
property_appreciation_rate = st.sidebar.slider("Annual Property Appreciation (%)", min_value=0.0, max_value=8.0, value=2.0, step=0.5) / 100

def render_scenario_builder(scenario_label: str, key_prefix: str, def_loans: int, def_rents: int, def_stocks: int):
    """Renders dynamic modules for a scenario in the sidebar and returns a structured dictionary of parameters."""
    st.sidebar.subheader(f"📊 {scenario_label}")
    st.sidebar.write("Configure number of modules:")
   
    # Use columns to compactly ask how many of each module the user wants
    cols = st.sidebar.columns(3)
    num_loans = cols[0].number_input("🏦 Loans", 0, 5, def_loans, key=f"{key_prefix}_nl")
    num_rents = cols[1].number_input("🔑 Rents", 0, 5, def_rents, key=f"{key_prefix}_nr")
    num_stocks = cols[2].number_input("📈 Stocks", 0, 5, def_stocks, key=f"{key_prefix}_ns")
   
    params = {"loans": [], "rents": [], "stocks": []}
   
    # --- RENDER LOAN MODULES ---
    for i in range(num_loans):
        with st.sidebar.expander(f"🏦 Loan Module {i+1}", expanded=(i==0)):
            price = st.number_input("Property Price (€)", min_value=10000, value=250000, step=5000, key=f"{key_prefix}_l{i}_price")
            down = st.number_input("Down Payment (€)", min_value=0, value=50000, step=5000, key=f"{key_prefix}_l{i}_down")
            rate = st.number_input("Annual Interest Rate (%)", min_value=0.1, max_value=15.0, value=3.5, step=0.1, key=f"{key_prefix}_l{i}_rate")
            term = st.number_input("Repayment Time (Years)", min_value=1, max_value=35, value=20, step=1, key=f"{key_prefix}_l{i}_term")
            params["loans"].append({"price": price, "down": down, "rate": rate / 100, "term": term})

    # --- RENDER RENT MODULES ---
    for i in range(num_rents):
        with st.sidebar.expander(f"🔑 Rent Module {i+1}", expanded=(i==0)):
            rent = st.number_input("Monthly Rent (€)", min_value=0, value=900, step=50, key=f"{key_prefix}_r{i}_rent")
            dur = st.number_input("Duration (Years)", min_value=1, max_value=35, value=horizon_years, step=1, key=f"{key_prefix}_r{i}_dur")
            repairs = st.number_input("Est. Repairs per Year (€)", min_value=0, value=500, step=100, key=f"{key_prefix}_r{i}_rep")
            params["rents"].append({"rent": rent, "duration": dur, "repairs": repairs})

    # --- RENDER STOCK MODULES ---
    for i in range(num_stocks):
        with st.sidebar.expander(f"📈 Stock Module {i+1}", expanded=(i==0)):
            initial = st.number_input("Original Lump Sum (€)", min_value=0, value=10000, step=2500, key=f"{key_prefix}_s{i}_init")
            monthly = st.number_input("Invested per Month (€)", min_value=0, value=300, step=50, key=f"{key_prefix}_s{i}_month")
            ret = st.number_input("Expected Avg. Growth (%)", min_value=0.0, max_value=20.0, value=7.0, step=0.5, key=f"{key_prefix}_s{i}_ret")
            params["stocks"].append({"initial": initial, "monthly": monthly, "return": ret / 100})

    return params

# Render Sidebar Scenarios
s1_params = render_scenario_builder("Scenario A", "s1", def_loans=1, def_rents=0, def_stocks=0)
st.sidebar.divider()
s2_params = render_scenario_builder("Scenario B", "s2", def_loans=0, def_rents=1, def_stocks=1)

# --- SIMULATION ENGINE ---
def calculate_simulation(params, total_years, prop_apprec_rate):
    total_months = total_years * 12
    months = np.arange(1, total_months + 1)
    monthly_prop_rate = (1 + prop_apprec_rate)**(1/12) - 1
   
    # Initialize states for multiple dynamic assets
    loan_states = []
    for l in params["loans"]:
        amt = max(0, l["price"] - l["down"])
        r = l["rate"] / 12
        n = l["term"] * 12
        pmt = amt * (r * (1 + r)**n) / ((1 + r)**n - 1) if r > 0 else (amt / n if n > 0 else 0)
        loan_states.append({"prop_val": l["price"], "balance": amt, "pmt": pmt, "r": r, "n": n})
       
    stock_states = [{"val": s["initial"]} for s in params["stocks"]]
   
    # Calculate initial upfront outflow (Down payments + Initial stock investments)
    total_outflow_accum = sum(l["down"] for l in params["loans"]) + sum(s["initial"] for s in params["stocks"])
    total_sunk_cost_accum = 0
   
    records = []
   
    for m in months:
        monthly_outflow = 0
        monthly_sunk = 0
        prop_equity_total = 0
       
        # Process all loans
        for i, l in enumerate(params["loans"]):
            state = loan_states[i]
            state["prop_val"] *= (1 + monthly_prop_rate)
           
            if m <= state["n"] and state["balance"] > 0:
                interest = state["balance"] * state["r"]
                principal = min(state["balance"], state["pmt"] - interest)
                state["balance"] -= principal
               
                monthly_outflow += state["pmt"]
                monthly_sunk += interest
               
            prop_equity_total += max(0, state["prop_val"] - state["balance"])
           
        # Process all rents
        for r in params["rents"]:
            if m <= r["duration"] * 12:
                cost = r["rent"] + (r["repairs"] / 12)
                monthly_outflow += cost
                monthly_sunk += cost
               
        # Process all stocks
        stock_total = 0
        for i, s in enumerate(params["stocks"]):
            r_stock = (1 + s["return"])**(1/12) - 1
            stock_states[i]["val"] = stock_states[i]["val"] * (1 + r_stock) + s["monthly"]
            monthly_outflow += s["monthly"]
            stock_total += stock_states[i]["val"]
           
        total_net_worth = prop_equity_total + stock_total
        total_outflow_accum += monthly_outflow
        total_sunk_cost_accum += monthly_sunk
       
        records.append({
            "Month": m,
            "Year": m / 12,
            "Property Equity (€)": prop_equity_total,
            "Stock Portfolio (€)": stock_total,
            "Total Net Worth (€)": total_net_worth,
            "Monthly Outflow (€)": monthly_outflow,
            "Cumulative Outflow (€)": total_outflow_accum,
            "Cumulative Sunk Costs (€)": total_sunk_cost_accum
        })
       
    return pd.DataFrame(records)

df_s1 = calculate_simulation(s1_params, horizon_years, property_appreciation_rate)
df_s2 = calculate_simulation(s2_params, horizon_years, property_appreciation_rate)

# --- DASHBOARD SUMMARY METRICS ---
st.header("📌 Comparison Dashboard")

col_a, col_b = st.columns(2)

def display_metrics(df, title, delta_df=None):
    st.subheader(title)
    nw = df["Total Net Worth (€)"].iloc[-1]
    outflow = df["Cumulative Outflow (€)"].iloc[-1]
    sunk = df["Cumulative Sunk Costs (€)"].iloc[-1]
   
    if delta_df is not None:
        st.metric("Final Net Worth", f"€{nw:,.0f}", delta=f"€{nw - delta_df['Total Net Worth (€)'].iloc[-1]:,.0f} vs A")
        st.metric("Total Cash Outflow (Upfront + Monthly)", f"€{outflow:,.0f}", delta=f"€{outflow - delta_df['Cumulative Outflow (€)'].iloc[-1]:,.0f} vs A", delta_color="inverse")
        st.metric("Total Sunk Costs (Interest, Rent, Repairs)", f"€{sunk:,.0f}", delta=f"€{sunk - delta_df['Cumulative Sunk Costs (€)'].iloc[-1]:,.0f} vs A", delta_color="inverse")
    else:
        st.metric("Final Net Worth", f"€{nw:,.0f}")
        st.metric("Total Cash Outflow (Upfront + Monthly)", f"€{outflow:,.0f}")
        st.metric("Total Sunk Costs (Interest, Rent, Repairs)", f"€{sunk:,.0f}")
       
    st.caption(f"End Property Equity: **€{df['Property Equity (€)'].iloc[-1]:,.0f}** | End Stocks: **€{df['Stock Portfolio (€)'].iloc[-1]:,.0f}**")

with col_a:
    display_metrics(df_s1, "Scenario A Overview")

with col_b:
    display_metrics(df_s2, "Scenario B Overview", delta_df=df_s1)

st.divider()

# --- COMPARISON CHARTS ---
st.subheader("📈 Net Worth Growth Trajectory Over Time")
df_nw = pd.DataFrame({
    "Year": df_s1["Year"],
    "Scenario A": df_s1["Total Net Worth (€)"],
    "Scenario B": df_s2["Total Net Worth (€)"]
}).set_index("Year")
st.line_chart(df_nw)

st.subheader("💸 Cumulative Cost Comparison")
tab_cost1, tab_cost2 = st.tabs(["Total Cash Outflow (Everything)", "Total Sunk Costs (No Equity Built)"])

with tab_cost1:
    df_outflow = pd.DataFrame({
        "Year": df_s1["Year"],
        "Scenario A": df_s1["Cumulative Outflow (€)"],
        "Scenario B": df_s2["Cumulative Outflow (€)"]
    }).set_index("Year")
    st.line_chart(df_outflow)

with tab_cost2:
    df_sunk = pd.DataFrame({
        "Year": df_s1["Year"],
        "Scenario A": df_s1["Cumulative Sunk Costs (€)"],
        "Scenario B": df_s2["Cumulative Sunk Costs (€)"]
    }).set_index("Year")
    st.line_chart(df_sunk)

# --- DETAILED DATA TABLES ---
with st.expander("🔍 View Detailed Financial Breakdown per Month"):
    tab1, tab2 = st.tabs(["Scenario A Details", "Scenario B Details"])
    with tab1:
        st.dataframe(df_s1.style.format("€{:.2f}"))
    with tab2:
        st.dataframe(df_s2.style.format("€{:.2f}"))