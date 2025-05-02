import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from datetime import datetime
import re

# Get the directory where main.py is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
category_file = os.path.join(SCRIPT_DIR, "categories.json")

st.set_page_config(page_title="UK Finance Dashboard", page_icon="��", layout="wide")

# Define default UK spending categories
DEFAULT_CATEGORIES = {
    "Uncategorized": [],
    "Groceries": ["COOP", "TESCO", "SAINSBURY", "ALDI", "LIDL", "ASDA", "MORRISONS", "WAITROSE"],
    "Dining & Pubs": ["COSTA", "STARBUCKS", "CAFE", "RESTAURANT", "PUB", "BAR", "DORSET ARMS", "MARINERS INN"],
    "Transport": ["TRANSPORT", "TAXI", "UBER", "TRAIN", "BUS", "FUEL", "PARKING"],
    "Shopping": ["AMAZON", "NEXT", "MARKS", "SPENCER", "BOOTS"],
    "Bills & Utilities": ["ELECTRIC", "GAS", "WATER", "COUNCIL TAX", "TV LICENSE", "INTERNET", "PHONE", "GOOGLE ONE"],
    "Entertainment": ["CINEMA", "NETFLIX", "SPOTIFY", "STEAM", "EVE ONLINE"],
    "Health": ["NHS", "PHARMACY", "DENTAL", "OPTICAL"],
    "Rent & Housing": ["RENT", "MORTGAGE", "INSURANCE"],
    "Transfers": ["REVOLUT", "TRANSFER", "BGC", "SAVINGS"],
    "Direct Debits": ["DDR", "DIRECT DEBIT"],
    "Salary": ["ARCADIA EXPR          SALARY"],
    "Bonus": ["ARCADIA EXPR          BONUS"],
    "Interest": ["INTEREST"],
    "Refunds": ["REFUND", "REBATE"],
    "Other Income": []
}

if "categories" not in st.session_state:
    st.session_state.categories = DEFAULT_CATEGORIES
    
if os.path.exists(category_file):
    with open(category_file, "r") as f:
        st.session_state.categories = json.load(f)

def save_categories():
    with open(category_file, "w") as f:
        json.dump(st.session_state.categories, f)

def clean_transaction_details(details):
    # Remove common payment method suffixes and clean up the string
    details = details.upper().strip()
    # Remove payment methods and dates
    suffixes_to_remove = [' CPM', ' CLP', ' BCC', ' DDR', ' BGC', ' STO', ' FT']
    for suffix in suffixes_to_remove:
        if details.endswith(suffix):
            details = details[:-len(suffix)]
    # Remove date patterns like "ON XX XXX"
    details = re.sub(r'\s+ON\s+\d{2}\s+[A-Z]{3}', '', details)
    # Remove multiple spaces
    details = ' '.join(details.split())
    return details

def categorize_transactions(df):
    df["Category"] = "Uncategorized"
    
    for category, keywords in st.session_state.categories.items():
        if category == "Uncategorized" or not keywords:
            continue
        
        for idx, row in df.iterrows():
            # Clean the transaction details before matching
            cleaned_details = clean_transaction_details(row["Details"])
            # Clean and compare keywords
            if any(keyword.upper() in cleaned_details for keyword in keywords):
                df.at[idx, "Category"] = category
                
    return df

def load_transactions(file):
    try:
        df = pd.read_csv(file, skipinitialspace=True)
        df.columns = [col.strip() for col in df.columns]
        
        # Handle Barclays format
        if "Subcategory" in df.columns and "Memo" in df.columns:
            # This is Barclays format
            df = df[["Date", "Amount", "Memo"]]  # Select only needed columns
            df = df.rename(columns={"Memo": "Details"})  # Rename Memo to Details
        
        df["Amount"] = df["Amount"].astype(float)
        df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y")
        df["Debit/Credit"] = df["Amount"].apply(lambda x: "Credit" if x > 0 else "Debit")
        
        # Ensure we have all required columns
        required_columns = ["Date", "Details", "Amount", "Debit/Credit"]
        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"Missing required columns. File must contain: {required_columns}")
        
        df = df[required_columns]  # Ensure columns are in the right order
        
        return categorize_transactions(df)
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None

def extract_keyword(details):
    # Use the same cleaning function for consistency
    return clean_transaction_details(details)

def add_keyword_to_category(category, details):
    keyword = extract_keyword(details).strip().upper()
    if keyword and keyword not in st.session_state.categories[category]:
        st.session_state.categories[category].append(keyword)
        save_categories()
        return True
    return False

# def fix_csv_format(input_file, output_file):
#     # Read the file with a more flexible parser
#     df = pd.read_csv(input_file, skipinitialspace=True, on_bad_lines='skip')
#     
#     # Clean up the data
#     df = df[['Date', 'Amount', 'Memo']]  # Select only needed columns
#     
#     # Rename Memo to Details
#     df = df.rename(columns={'Memo': 'Details'})
#     
#     # Remove any leading/trailing whitespace
#     df['Date'] = df['Date'].str.strip()
#     df['Amount'] = df['Amount'].str.strip() if df['Amount'].dtype == 'object' else df['Amount']
#     df['Details'] = df['Details'].str.strip()
#     
#     # Save in the correct format
#     df.to_csv(output_file, index=False)

def main():
    st.title("UK Finance Dashboard 💷")
    
    uploaded_file = st.file_uploader("Upload your transaction CSV file", type=["csv"])
    
    if uploaded_file is not None:
        df = load_transactions(uploaded_file)
        
        if df is not None:
            debits_df = df[df["Debit/Credit"] == "Debit"].copy()
            credits_df = df[df["Debit/Credit"] == "Credit"].copy()
            
            st.session_state.debits_df = debits_df.copy()
            
            tab1, tab2, tab3 = st.tabs(["Expenses (Debits)", "Income (Credits)", "Analysis"])
            
            with tab1:
                col1, col2 = st.columns([2, 1])
                with col1:
                    new_category = st.text_input("New Category Name")
                with col2:
                    add_button = st.button("Add Category")
                
                if add_button and new_category:
                    st.write(f"Adding new category: {new_category}")
                    if new_category not in st.session_state.categories:
                        st.session_state.categories[new_category] = []
                        save_categories()
                        st.write("Current categories after adding:", st.session_state.categories)
                        st.rerun()
                
                st.subheader("Your Expenses")
                edited_df = st.data_editor(
                    st.session_state.debits_df[["Date", "Details", "Amount", "Category"]],
                    column_config={
                        "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                        "Amount": st.column_config.NumberColumn("Amount", format="£%.2f"),
                        "Category": st.column_config.SelectboxColumn(
                            "Category",
                            options=list(st.session_state.categories.keys())
                        )
                    },
                    hide_index=True,
                    use_container_width=True,
                    key="category_editor"
                )
                
                save_button = st.button("Apply Changes", type="primary")
                if save_button:
                    st.write("Saving changes...")  # Debug info
                    for idx, row in edited_df.iterrows():
                        new_category = row["Category"]
                        old_category = st.session_state.debits_df.at[idx, "Category"]
                        st.write(f"Transaction: {row['Details']}")  # Debug info
                        st.write(f"Old category: {old_category}")  # Debug info
                        st.write(f"New category: {new_category}")  # Debug info
                        
                        if new_category == old_category:
                            continue
                            
                        details = row["Details"]
                        st.session_state.debits_df.at[idx, "Category"] = new_category
                        add_keyword_to_category(new_category, details)
                    
                    # Add this to force save after all changes
                    save_categories()
                    st.write("Current categories:", st.session_state.categories)  # Debug info
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader('Expense Summary')
                    category_totals = st.session_state.debits_df.groupby("Category")["Amount"].sum().reset_index()
                    category_totals = category_totals.sort_values("Amount", ascending=True)
                    
                    fig = go.Figure(go.Bar(
                        x=category_totals["Amount"].abs(),
                        y=category_totals["Category"],
                        orientation='h'
                    ))
                    fig.update_layout(
                        title="Expenses by Category",
                        xaxis_title="Amount (£)",
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    fig = px.pie(
                        category_totals,
                        values="Amount",
                        names="Category",
                        title="Expense Distribution"
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            with tab2:
                st.subheader("Income Summary")
                total_credits = credits_df["Amount"].sum()
                total_debits = debits_df["Amount"].sum()
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Income", f"£{total_credits:,.2f}")
                with col2:
                    st.metric("Total Expenses", f"£{abs(total_debits):,.2f}")
                with col3:
                    net = total_credits + total_debits
                    st.metric("Net Position", f"£{net:,.2f}")
                
                st.write(credits_df)
            
            with tab3:
                st.subheader("Historical Analysis")
                
                # Date range selector
                date_range = st.date_input(
                    "Select Date Range",
                    [df['Date'].min(), df['Date'].max()]
                )
                
                # Monthly Overview
                st.subheader("Monthly Overview")
                monthly_spending, category_trends = analyze_historical_trends(df)
                
                # Plot monthly total spending
                fig = px.line(monthly_spending, 
                              x='Date', 
                              y='Amount',
                              title="Monthly Spending Trends",
                              labels={"Amount": "Amount (£)"})
                st.plotly_chart(fig, use_container_width=True)
                
                # Category breakdown over time
                st.subheader("Category Trends")
                # Melt the category trends for plotting
                category_trends_melted = pd.melt(category_trends, 
                                                id_vars=['Date'], 
                                                var_name='Category', 
                                                value_name='Amount')
                fig = px.line(category_trends_melted, 
                              x='Date', 
                              y='Amount',
                              color='Category',
                              title="Spending by Category Over Time")
                st.plotly_chart(fig, use_container_width=True)
                
                # Savings Projections
                st.subheader("Savings Projections")
                projections = calculate_savings_projections(df)
                
                # Plot projections
                fig = px.line(projections, 
                              title="12-Month Savings Projection",
                              labels={"value": "Projected Savings (£)"})
                st.plotly_chart(fig)
                
                # Savings Goals
                st.subheader("Savings Goals")
                goal_amount = st.number_input("Set Savings Goal (£)", min_value=0.0)
                if goal_amount > 0:
                    current_savings = projections[-1]
                    avg_monthly_net = projections[-1] / 12
                    months_to_goal = (goal_amount - current_savings) / avg_monthly_net
                    st.write(f"At your current rate, you'll reach your goal in {months_to_goal:.1f} months")

                # Budget Tracking
                track_budget_vs_actual(df)

def analyze_historical_trends(df):
    # Monthly spending trends - only look at amounts
    monthly_spending = df.groupby(pd.Grouper(key='Date', freq='M'))['Amount'].sum().reset_index()
    
    # Category trends over time
    category_trends = df.pivot_table(
        index=pd.Grouper(key='Date', freq='M'),
        columns='Category',
        values='Amount',
        aggfunc='sum'
    ).fillna(0).reset_index()
    
    return monthly_spending, category_trends

def calculate_savings_projections(df):
    # Calculate average monthly income and expenses
    monthly_net = df.groupby([df['Date'].dt.year, df['Date'].dt.month])['Amount'].sum()
    avg_monthly_net = monthly_net.mean()
    
    # Project next 12 months
    current_savings = monthly_net.sum()
    projected_savings = [current_savings]
    for _ in range(12):
        projected_savings.append(projected_savings[-1] + avg_monthly_net)
    
    return projected_savings

def save_historical_data(df):
    # Create a directory for historical data if it doesn't exist
    if not os.path.exists('historical_data'):
        os.makedirs('historical_data')
    
    # Save the current month's data
    month_year = df['Date'].max().strftime('%Y_%m')
    df.to_csv(f'historical_data/{month_year}.csv', index=False)

def track_budget_vs_actual(df):
    # Set budget limits per category
    if 'budget_limits' not in st.session_state:
        st.session_state.budget_limits = {}
    
    st.subheader("Budget Tracking")
    for category in df['Category'].unique():
        if category not in st.session_state.budget_limits:
            st.session_state.budget_limits[category] = 0
        
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.budget_limits[category] = st.number_input(
                f"Budget for {category}",
                value=st.session_state.budget_limits[category]
            )
        with col2:
            actual_spending = abs(df[df['Category'] == category]['Amount'].sum())
            progress = actual_spending / st.session_state.budget_limits[category] if st.session_state.budget_limits[category] > 0 else 0
            st.progress(min(progress, 1.0))
            st.write(f"Spent: £{actual_spending:.2f}")

main()

# def fix_csv_format('AutomateFinancesWithPython/barclays april.csv', 'AutomateFinancesWithPython/barclays_april_fixed.csv')
