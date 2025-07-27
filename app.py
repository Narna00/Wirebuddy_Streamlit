# frontend.py
import streamlit as st
from backend import Account, CurrencyConverter, FinanceChatbot, ReceiptGenerator, verify_payment, initiate_deposit, initiate_withdrawal, verify_withdrawal
from datetime import datetime
import time
import pandas as pd
import os
from streamlit.components.v1 import html
from io import StringIO

# Configuration
st.set_page_config(page_title="Wirebuddy", layout="centered", page_icon="🏦")
st.title("Wirebuddy")

# Error handling for database connection
import sqlite3
try:
    conn = sqlite3.connect("bank.db", check_same_thread=False)
    cursor = conn.cursor()
except Exception as e:
    st.error(f"Database connection error: {str(e)}")
    st.stop()

# Session state management
if 'logged_in_user' not in st.session_state:
    st.session_state.logged_in_user = None
    st.session_state.page = "login"
    st.session_state.last_activity = datetime.now()
    st.session_state.receipt_data = None

# Helper functions
def show_loading():
    with st.spinner("Processing..."):
        time.sleep(1)

def validate_phone(phone):
    return phone.isdigit() and len(phone) == 10

def validate_pin(pin):
    return pin.isdigit() and len(pin) == 4

def format_currency(amount):
    return f"${amount:,.2f}"

# Sidebar navigation
with st.sidebar:
    st.title("Navigation")
    if st.session_state.logged_in_user:
        if st.button("Dashboard"):
            st.session_state.page = "dashboard"
        if st.button("Profile"):
            st.session_state.page = "profile"
        if st.button("Currency Converter"):
            st.session_state.page = "currency_converter"
        if st.button("Savings Goals"):
            st.session_state.page = "savings_goals"
        if st.button("Financial Advice"):
            st.session_state.page = "financial_advice"
        
        if st.session_state.logged_in_user.is_admin:
            if st.button("Admin Panel"):
                st.session_state.page = "admin_panel"
        
        if st.button("Logout"):
            st.session_state.logged_in_user = None
            st.session_state.page = "login"
            st.success("Logged out successfully.")
            st.rerun()
        orientation = "horizontal"
    else:
        if st.button("Register"):
            st.session_state.page = "register"
        if st.button("Login"):
            st.session_state.page = "login"

# Registration Page
if st.session_state.page == "register":
    st.header("Register Account")
    with st.form("registration_form"):
        full_name = st.text_input("Full Name*", max_chars=50)
        username = st.text_input("Username*", max_chars=20)
        national_id = st.text_input("National ID*", max_chars=20)
        phone = st.text_input("Phone (10-digit)*", max_chars=10)
        address = st.text_area("Address", max_chars=100)
        pin = st.text_input("4-digit PIN*", type="password", max_chars=4)
        pin_confirm = st.text_input("Confirm PIN*", type="password", max_chars=4)
        
        submitted = st.form_submit_button("Create Account")
        if submitted:
            if not all([full_name, username, national_id, phone, pin, pin_confirm]):
                st.error("Please fill all required fields (*)")
            elif pin != pin_confirm:
                st.error("PINs don't match!")
            elif not validate_phone(phone):
                st.error("Phone must be 10 digits")
            elif not validate_pin(pin):
                st.error("PIN must be 4 digits")
            else:
                show_loading()
                try:
                    acc = Account(full_name, phone, pin, username, national_id, address)
                    acc.save_to_db()
                    st.success(f"Account created successfully! Your account number is: {phone}")
                    st.session_state.page = "login"
                    st.rerun()
                except Exception as e:
                    st.error(f"Registration failed: {str(e)}")

# Login Page
elif st.session_state.page == "login":
    st.header("Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        phone = st.text_input("Phone")
        pin = st.text_input("PIN", type="password", max_chars=4)
        
        submitted = st.form_submit_button("Login")
        if submitted:
            show_loading()
            user = Account.find_by_login(username, phone, pin)
            if user:
                if not user.is_active:
                    st.error("Account is frozen. Please contact support.")
                else:
                    st.session_state.logged_in_user = user
                    st.session_state.page = "dashboard"
                    st.success(f"Welcome back, {user.name}!")
                    st.rerun()
            else:
                st.error("Invalid credentials. Please try again.")

# Dashboard (after login)
elif st.session_state.logged_in_user and st.session_state.page == "dashboard":
    user = st.session_state.logged_in_user
    st.header(f"Welcome, {user.name}!")
    
    # Account summary
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Account Summary")
        st.write(f"**Account Number:** {user.account_number}")
        st.write(f"**Balance:** {format_currency(user.balance)}")
        
        # Quick balance summary
        st.metric("Available Balance", format_currency(user.balance))
    
    with col2:
        st.subheader("Quick Actions")
        if st.button("Deposit"):
            st.session_state.page = "deposit"
            st.rerun()
        if st.button("Withdraw"):
            st.session_state.page = "withdraw"
            st.rerun()
        if st.button("Transfer"):
            st.session_state.page = "transfer"
            st.rerun()
    
    # Recent transactions
    st.subheader("Recent Transactions")
    history = user.get_transaction_history(5)
    if history:
        for txn_type, amt, desc, ts, ref in history:
            color = "green" if amt > 0 else "red"
            icon = "⬆️" if amt > 0 else "⬇️"
            st.markdown(f"""
            <div style="padding:10px;border-radius:5px;margin:5px 0;background:#f0f2f6">
                <b style="color:{color}">{icon} {txn_type}</b> | 
                <b>{format_currency(abs(amt))}</b> | 
                {desc} | 
                <i>{ts}</i>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No transactions yet.")

# Deposit Page
# Updated Deposit Page with verification
elif st.session_state.logged_in_user and st.session_state.page == "deposit":
    user = st.session_state.logged_in_user
    st.header("Deposit Money")

    method = st.selectbox("Payment Method", ["card", "momo"])
    amount = st.number_input("Amount to Deposit", min_value=0.01, step=0.01, format="%.2f")
    pin = st.text_input("Enter 4‑digit PIN", type="password", max_chars=4, key="deposit_pin")
    if st.button("Proceed to Pay"):
        if not Account.find_by_login(user.username, user.account_number, pin):
            st.error("Invalid PIN. Deposit cancelled.")
        else:
            show_loading()
            auth_url, ref = initiate_deposit(user, amount, method)
            st.session_state.deposit_ref = ref
            st.success("Payment initialized. Complete payment:")
            st.markdown(f"[Pay Now]({auth_url})", unsafe_allow_html=True)
            st.info("After completing payment, click 'Verify Payment' below to update your balance.")

    # Verification step
    if 'deposit_ref' in st.session_state:
        if st.button("Verify Payment"):
            try:
                show_loading()
                status = verify_payment(st.session_state.deposit_ref)
                if status == 'success':
                    # Refresh user object
                    user = Account.get_by_account_number(user.account_number)
                    st.session_state.logged_in_user = user
                    # Once credited, clear the ref to prevent re-verification
                    del st.session_state['deposit_ref']
                    st.success(f"Payment successful! New balance: ${user.balance:,.2f}")
                else:
                    st.warning(f"Payment status: {status}")
            except Exception as e:
                st.error(f"Verification failed: {e}")

# Withdrawal Page

elif st.session_state.logged_in_user and st.session_state.page == "withdraw":
    user = st.session_state.logged_in_user
    st.header("Withdraw Money to Mobile Money")

    st.write(f"Available Balance: {user.balance:,.2f} GHS")
    momo = st.text_input("Mobile Money Number (10 digits)")
    amount = st.number_input("Amount to Withdraw", min_value=0.01, max_value=float(user.balance), step=0.01)
    pin = st.text_input("Enter 4‑digit PIN", type="password", max_chars=4, key="deposit_pin")

    if st.button("Initiate Withdrawal"):
        try:
            if not Account.find_by_login(user.username, user.account_number, pin):
                st.error("Invalid PIN. Deposit cancelled.")
            else:
                show_loading()
                ref = initiate_withdrawal(user, amount, momo)
                st.session_state.withdraw_ref = ref
                st.success("Withdrawal initiated. It may take a few minutes.")
                st.info("Click 'Verify Withdrawal' to update status.")
        except Exception as e:
            st.error(f"Error: {e}")

    if 'withdraw_ref' in st.session_state:
        if st.button("Verify Withdrawal"):
            try:
                show_loading()
                status = verify_withdrawal(st.session_state.withdraw_ref)
                if status.lower() == 'success':
                    del st.session_state['withdraw_ref']
                    user = Account.get_by_account_number(user.account_number)
                    st.session_state.logged_in_user = user
                    st.success(f"Withdrawal successful! New balance: {user.balance:,.2f} GHS")
                else:
                    st.warning(f"Withdrawal status: {status}")
            except Exception as e:
                st.error(f"Verification failed: {e}")

# Transfer Money Page
elif st.session_state.logged_in_user and st.session_state.page == "transfer":
    user = st.session_state.logged_in_user
    st.header("Transfer Money")
    
    if user.balance <= 0:
        st.warning("Your account balance is zero. You cannot make any transfers.")
        if st.button("Back to Dashboard"):
            st.session_state.page = "dashboard"
            st.rerun()
    else:
        st.success(f"Available Balance: {format_currency(user.balance)}")
        
        with st.form("transfer_form"):
            recipient_acc = st.text_input(
                "Recipient Account Number", 
                placeholder="Enter 10-digit account/phone number"
            )
            
            amount = st.number_input(
                "Amount",
                min_value=0.01,
                max_value=float(user.balance),
                step=0.01,
                format="%.2f",
                help=f"Maximum transferable: {format_currency(user.balance)}"
            )
            
            submitted = st.form_submit_button("Send Money")
            
            if submitted:
                if not recipient_acc.isdigit() or len(recipient_acc) != 10:
                    st.error("Account number must be 10 digits")
                elif amount <= 0:
                    st.error("Amount must be positive")
                elif recipient_acc == user.account_number:
                    st.error("Cannot transfer to your own account")
                else:
                    with st.spinner("Processing transfer..."):
                        reference_id, message = user.send_money(recipient_acc, amount)
                        if reference_id:
                            st.success(
                                f"Transfer successful!\n"
                                f"**{format_currency(amount)}** sent to account **{recipient_acc}**"
                            )
                            st.balloons()
                            
                            # Get transaction details for receipt
                            transaction = user.get_transaction_by_reference(reference_id)
                            st.session_state.receipt_data = transaction
                            st.session_state.page = "receipt"
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"Transfer failed: {message}")

# Receipt Page
elif st.session_state.logged_in_user and st.session_state.page == "receipt":
    user = st.session_state.logged_in_user
    transaction = st.session_state.receipt_data
    
    st.header("Transaction Receipt")
    
    if transaction:
        receipt = ReceiptGenerator.generate_receipt(transaction, user)
        st.code(receipt)
        
        # Create downloadable receipt
        receipt_io = StringIO()
        receipt_io.write(receipt)
        st.download_button(
            label="Download Receipt",
            data=receipt_io.getvalue(),
            file_name=f"receipt_{transaction[4]}.txt",
            mime="text/plain"
        )
    
    if st.button("Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

# Profile Page
elif st.session_state.logged_in_user and st.session_state.page == "profile":
    user = st.session_state.logged_in_user
    st.header("My Profile")
    
    with st.form("profile_form"):
        st.subheader("Personal Information")
        
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name", value=user.name)
            username = st.text_input("Username", value=user.username)
            account_number = st.text_input("Account Number", value=user.account_number, disabled=True)
        
        with col2:
            national_id = st.text_input("National ID", value=user.national_id)
            address = st.text_area("Address", value=user.address)
            balance = st.text_input("Account Balance", value=format_currency(user.balance), disabled=True)
        
        st.subheader("Security")
        current_pin = st.text_input("Current PIN", type="password", max_chars=4)
        new_pin = st.text_input("New PIN (leave blank to keep current)", type="password", max_chars=4)
        confirm_pin = st.text_input("Confirm New PIN", type="password", max_chars=4)
        
        if st.form_submit_button("Update Profile"):
            user.name = name
            user.username = username
            user.national_id = national_id
            user.address = address
            
            pin_changed = False
            if new_pin:
                if not current_pin or current_pin != user.pin:
                    st.error("Current PIN is incorrect")
                elif new_pin != confirm_pin:
                    st.error("New PINs don't match")
                elif not validate_pin(new_pin):
                    st.error("PIN must be 4 digits")
                else:
                    user.pin = new_pin
                    pin_changed = True
            
            try:
                user.update_profile_in_db()
                st.success("Profile updated successfully!")
                if pin_changed:
                    st.success("PIN changed successfully!")
                st.session_state.logged_in_user = user
                st.rerun()
            except Exception as e:
                st.error(f"Error updating profile: {str(e)}")

# Savings Goals Page
elif st.session_state.logged_in_user and st.session_state.page == "savings_goals":
    user = st.session_state.logged_in_user
    st.header("Savings Goals")
    
    tab1, tab2 = st.tabs(["My Goals", "New Goal"])
    
    with tab1:
        goals = user.get_savings_goals()
        if goals:
            for goal in goals:
                goal_id, name, target, current, target_date, created_at = goal
                progress = min(current / target * 100, 100)
                
                with st.expander(f"{name} - {progress:.1f}% complete"):
                    st.write(f"**Target:** {format_currency(target)} by {target_date}")
                    st.write(f"**Saved:** {format_currency(current)}")
                    st.progress(int(progress))
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        # Add Funds Button
                        with st.form(key=f"add_form_{goal_id}"):
                            add_amount = st.number_input(
                                "Amount to add",
                                min_value=0.01,
                                max_value=float(user.balance),
                                key=f"add_amount_{goal_id}",
                                step=0.01,
                                format="%.2f"
                            )
                            if st.form_submit_button("Add Funds"):
                                if user.balance < add_amount:
                                    st.error("Insufficient account balance")
                                else:
                                    success, msg = user.contribute_to_goal(goal_id, add_amount)
                                    if success:
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                    
                    with col2:
                        # Withdraw Button - Only show if current balance > 0
                        if current > 0:
                            with st.form(key=f"withdraw_form_{goal_id}"):
                                withdraw_amount = st.number_input(
                                    "Amount to withdraw",
                                    min_value=0.01,
                                    max_value=float(current),
                                    key=f"withdraw_amount_{goal_id}",
                                    step=0.01,
                                    format="%.2f"
                                )
                                if st.form_submit_button("Withdraw"):
                                    if current < withdraw_amount:
                                        st.error("Insufficient funds in goal")
                                    else:
                                        success, msg = user.withdraw_from_goal(goal_id, withdraw_amount)
                                        if success:
                                            st.success(msg)
                                            st.rerun()
                                        else:
                                            st.error(msg)
                        else:
                            st.write("No funds available to withdraw")
                    
                    with col3:
                        if st.button(f"Delete", key=f"delete_{goal_id}"):
                            if user.delete_savings_goal(goal_id):
                                st.success("Goal deleted")
                                st.rerun()
                            else:
                                st.error("Failed to delete goal")
    
    with tab2:
        with st.form("new_goal_form"):
            goal_name = st.text_input("Goal Name", max_chars=30)
            target_amount = st.number_input("Target Amount", min_value=0.01, format="%.2f")
            target_date = st.date_input("Target Date", min_value=datetime.now().date())
            
            if st.form_submit_button("Create Goal"):
                if goal_name and target_amount:
                    goal_id = user.create_savings_goal(
                        goal_name, 
                        target_amount, 
                        target_date.strftime('%Y-%m-%d')
                    )
                    st.success(f"Goal '{goal_name}' created successfully!")
                    st.rerun()
                else:
                    st.error("Please fill all fields")

# Admin Panel
elif st.session_state.logged_in_user and st.session_state.page == "admin_panel" and st.session_state.logged_in_user.is_admin:
    st.header("Admin Panel")
    
    tab1, tab2 = st.tabs(["Account Management", "System Overview"])
    
    with tab1:
        st.subheader("All Accounts")
        accounts = Account.get_all_accounts()
        
        search_term = st.text_input("Search accounts")
        if search_term:
            accounts = [acc for acc in accounts 
                       if search_term.lower() in acc.name.lower() or 
                       search_term in acc.account_number]
        
        if accounts:
            for account in accounts:
                with st.expander(f"{account.name} ({account.account_number})"):
                    st.write(f"**Username:** {account.username}")
                    st.write(f"**Balance:** {format_currency(account.balance)}")
                    st.write(f"**Status:** {'Active' if account.is_active else 'Frozen'}")
                    st.write(f"**Created:** {account.created_at}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"{'Freeze' if account.is_active else 'Unfreeze'} Account", 
                                   key=f"status_{account.account_number}"):
                            new_status = account.toggle_account_status()
                            st.success(f"Account {'frozen' if not new_status else 'unfrozen'}")
                            st.rerun()
                    
                    with col2:
                        if st.button("Reset PIN", key=f"reset_{account.account_number}"):
                            new_pin = "0000"  # Default reset PIN
                            account.pin = new_pin
                            account.update_profile_in_db()
                            st.success(f"PIN reset to 0000 for {account.name}")
                            st.rerun()
        
        else:
            st.info("No accounts found")
    
    with tab2:
        st.subheader("System Statistics")
        
        if accounts:
            total_balance = sum(acc.balance for acc in accounts)
            active_accounts = sum(1 for acc in accounts if acc.is_active)
            frozen_accounts = len(accounts) - active_accounts
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Accounts", len(accounts))
            col2.metric("Active Accounts", active_accounts)
            col3.metric("Frozen Accounts", frozen_accounts)
            
            st.metric("Total System Balance", format_currency(total_balance))
            
            # Transaction statistics
            st.subheader("Recent Transactions")
            all_transactions = []
            for acc in accounts:
                cursor.execute("""
                    SELECT type, amount, description, timestamp, reference_id
                    FROM transactions
                    WHERE account_number=?
                    ORDER BY timestamp DESC
                    LIMIT 5
                """, (acc.account_number,))
                all_transactions.extend(cursor.fetchall())
            
            if all_transactions:
                df = pd.DataFrame(all_transactions, 
                                columns=["Type", "Amount", "Description", "Timestamp", "Reference"])
                st.dataframe(df.sort_values("Timestamp", ascending=False))
            else:
                st.info("No transactions in system")
        else:
            st.warning("No accounts in system")

# Currency Converter Page
elif st.session_state.logged_in_user and st.session_state.page == "currency_converter":
    st.subheader("Currency Converter")
    
    currencies = CurrencyConverter.SUPPORTED_CURRENCIES
    
    col1, col2 = st.columns(2)
    with col1:
        amount = st.number_input("Amount", min_value=0.01, value=1.0, step=0.1)
        from_currency = st.selectbox("From", currencies, index=currencies.index("USD"))
    with col2:
        to_currency = st.selectbox("To", currencies, index=currencies.index("GHS"))
        
    if st.button("Convert"):
        try:
            converted_amount = CurrencyConverter.convert(amount, from_currency, to_currency)
            st.success(f"""
            **{amount:.2f} {from_currency} = {converted_amount:.2f} {to_currency}**
            """)
            
            reverse_amount = CurrencyConverter.convert(1, to_currency, from_currency)
            st.caption(f"1 {to_currency} ≈ {reverse_amount:.4f} {from_currency}")
        except Exception as e:
            st.error(f"Conversion failed: {str(e)}")
    
    st.caption("ℹ Rates update every 24 hours. For investments, verify with your bank.")

# Financial Advice Page
elif st.session_state.logged_in_user and st.session_state.page == "financial_advice":
    st.subheader("Financial Literacy Bot")
    
    user_input = st.text_input("Ask me about saving, investing, or debt:")
    
    if user_input:
        response = FinanceChatbot.get_response(user_input)
        st.markdown(f"""
        <div style="background:#f0f2f6; padding:10px; border-radius:5px;">
            <strong>Bot:</strong> {response}
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("**Try asking:**")
    st.markdown("- How to save money?")
    st.markdown("- Best investment options?")
    st.markdown("- What is compound interest?")
    st.markdown("- How to get out of debt?")

# Session timeout check
if st.session_state.logged_in_user and (datetime.now() - st.session_state.last_activity).seconds > 1800:
    st.session_state.logged_in_user = None
    st.warning("Session timed out due to inactivity. Please login again.")
    st.session_state.page = "login"
    st.rerun()

# Update last activity time on any interaction
st.session_state.last_activity = datetime.now()

# Custom CSS for better styling
st.markdown("""
    <style>
        .stButton>button {
            width: 100%;
            border-radius: 5px;
            font-weight: bold;
        }
        .stTextInput>div>div>input, .stNumberInput>div>div>input {
            border-radius: 5px;
        }
        .stTextArea>div>div>textarea {
            border-radius: 5px;
        }
        .stSelectbox>div>div>select {
            border-radius: 5px;
        }
        .stDateInput>div>div>input {
            border-radius: 5px;
        }
        .stProgress>div>div>div>div {
            background-color: #4CAF50;
        }
    </style>
""", unsafe_allow_html=True)

# Close database connection when Streamlit script ends
def cleanup():
    if 'conn' in globals():
        conn.close()

import atexit
atexit.register(cleanup)

# Display version and footer
st.sidebar.markdown("---")
st.sidebar.markdown("**Wirebuddy v1.2**")
st.sidebar.markdown("© 2025 Wirebuddy Inc.")

st.markdown("---")
st.markdown(
    """
    <div style='text-align: center;'>
        <a href='https://twitter.com/yourhandle' target='_blank'>🐦 Twitter</a> |
        <a href='https://github.com/yourrepo' target='_blank'>💻 GitHub</a> |
        <a href='mailto:youremail@example.com'>📧 Contact</a>
        <p style='font-size: 0.8em;'>© 2025 SmartBank. All rights reserved.</p>
    </div>
    """,
    unsafe_allow_html=True
)
