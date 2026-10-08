import streamlit as st
import pandas as pd

# Set page configuration
st.set_page_config(page_title="Flat Investment Simulator", layout="centered")

st.title("🏡 Flat Investment Simulator")
st.write("Adjust the parameters in the sidebar to simulate your real estate investment and calculate your mortgage details.")

# --- SIDEBAR INPUTS ---
st.sidebar.header("Investment Parameters")

property_price = st.sidebar.number_input("Property Price (€)", min_value=10000, value=250000, step=5000)
down_payment = st.sidebar.number_input("Initial Cash / Down Payment (€)", min_value=0, value=50000, step=5000)

interest_rate = st.sidebar.slider("Annual Interest Rate (%)", min_value=0.1, max_value=10.0, value=3.5, step=0.1)
loan_term_years = st.sidebar.slider("Credit Time (Years)", min_value=5, max_value=35, value=20, step=1)

# --- CALCULATIONS ---
loan_amount = property_price - down_payment

if loan_amount <= 0:
    st.success("Your initial cash covers the entire property price! You don't need a loan.")
    st.metric("Total Project Cost", f"€{property_price:,.2f}")
else:
    # Math for mortgage
    monthly_rate = (interest_rate / 100) / 12
    num_payments = loan_term_years * 12
    
    # Standard mortgage formula: M = P [ i(1 + i)^n ] / [ (1 + i)^n - 1 ]
    if monthly_rate > 0:
        monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate)**num_payments) / ((1 + monthly_rate)**num_payments - 1)
    else:
        monthly_payment = loan_amount / num_payments

    total_paid_to_bank = monthly_payment * num_payments
    total_interest_cost = total_paid_to_bank - loan_amount
    total_project_cost = property_price + total_interest_cost

    # --- DISPLAY RESULTS ---
    st.header("Financial Summary")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Loan Amount", f"€{loan_amount:,.0f}")
    col2.metric("Monthly Payment", f"€{monthly_payment:,.2f}")
    col3.metric("Total Interest Cost", f"€{total_interest_cost:,.0f}")
    
    st.info(f"**Total Cost of the Project (Property + Credit Cost): €{total_project_cost:,.0f}**")

    # --- AMORTIZATION SCHEDULE ---
    st.subheader("Amortization Schedule")
    
    balance = loan_amount
    schedule = []
    
    for month in range(1, num_payments + 1):
        interest_payment = balance * monthly_rate
        principal_payment = monthly_payment - interest_payment
        balance -= principal_payment
        
        # Prevent negative balance display due to floating point errors on the last month
        balance = max(0, balance) 
        
        schedule.append([month, principal_payment, interest_payment, balance])

    # Create a DataFrame for charts and tables
    df_schedule = pd.DataFrame(schedule, columns=["Month", "Principal", "Interest", "Remaining Balance"])
    df_schedule.set_index("Month", inplace=True)

    # Display chart
    st.write("### Remaining Balance Over Time")
    st.line_chart(df_schedule[["Remaining Balance"]])

    # Expandable detailed table
    with st.expander("Show Detailed Amortization Table"):
        st.dataframe(df_schedule.style.format("€{:.2f}"))