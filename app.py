# frontend.py
import streamlit as st
from backend import fraud_detector, transaction_classifier, credit_scorer, savings_predictor, finance_chatbot, Account, CurrencyConverter, ReceiptGenerator, verify_payment, initiate_deposit, initiate_withdrawal, verify_withdrawal
import time
from datetime import datetime
import pandas as pd
import os
from streamlit.components.v1 import html
from io import StringIO
import streamlit as st
import streamlit.components.v1 as components

def validate_phone(phone):
    """Validates Ghanaian phone numbers (10 digits starting with 0)"""
    phone = str(phone).strip()
    return len(phone) == 10 and phone.startswith('0') and phone.isdigit()

def validate_pin(pin):
    """Validates 4-digit numeric PIN"""
    return str(pin).isdigit() and len(str(pin)) == 4


# Configuration
st.set_page_config(page_title="Wirebuddy", layout="wide", page_icon="🏦")
st.title("Wirebuddy")



# Custom CSS for professional banking UI
st.markdown("""
    <style>
        /* Main Theme */
        :root {
            --primary: #005f73;
            --primary-dark: #0a9396;
            --secondary: #94d2bd;
            --accent: #ee9b00;
            --danger: #ae2012;
            --light: #e9d8a6;
            --dark: #001219;
            --card-bg: #ffffff;
            --app-bg: #f8f9fa;
        }
        
        /* Stronger App Container */
        .stApp {
            background: var(--app-bg);
            font-family: 'Segoe UI', system-ui, sans-serif;
        }
        
        /* Professional Headers */
        h1 {
            color: var(--primary) !important;
            font-weight: 700 !important;
            border-bottom: 2px solid var(--secondary);
            padding-bottom: 8px;
        }
        
        h2 {
            color: var(--primary-dark) !important;
            font-weight: 600 !important;
        }
        
        /* Enhanced Cards */
        .card {
            background: var(--card-bg);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            border: 1px solid rgba(0,0,0,0.08);
            margin-bottom: 20px;
            transition: all 0.3s ease;
        }
        
        .card:hover {
            box-shadow: 0 6px 12px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }
        
        /* Strong Buttons */
        .stButton>button {
            border-radius: 8px !important;
            padding: 10px 24px !important;
            font-weight: 600 !important;
            transition: all 0.2s !important;
            border: none !important;
        }
        
        .stButton>button.primary {
            background: var(--primary) !important;
            color: white !important;
        }
        
        .stButton>button.primary:hover {
            background: var(--primary-dark) !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        
        /* Improved Sidebar */
        .sidebar .sidebar-content {
            background: linear-gradient(180deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: white;
        }
        
        .sidebar .stButton>button {
            width: 100%;
            margin: 8px 0;
            text-align: left;
            padding-left: 20px;
            background: rgba(255,255,255,0.1);
            color: white;
        }
        
        .sidebar .stButton>button:hover {
            background: rgba(255,255,255,0.2);
        }
        
        /* Transaction Items */
        .transaction-item {
            display: flex;
            align-items: center;
            padding: 12px 16px;
            margin: 8px 0;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            transition: all 0.2s;
        }
        
        .transaction-item:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        
        /* Form Styling */
        .stTextInput>div>div>input, 
        .stNumberInput>div>div>input,
        .stTextArea>div>div>textarea,
        .stSelectbox>div>div>select {
            border-radius: 18px !important;
            padding: 10px 12px !important;
            border: 2px solid #ddd !important;
        }
        
        /* Metrics Cards */
        .metric-card {
            background: white;
            border-radius: 10px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            border-left: 4px solid var(--primary);
        }
    </style>
""", unsafe_allow_html=True)


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

if 'force_page' not in st.session_state:
    st.session_state.force_page = None

# Helper functions
from datetime import datetime
import pytz

def get_time_of_day():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"

def get_transaction_icon(txn_type):
    icons = {
        "Deposit": "💰",
        "Withdrawal": "🏧",
        "Transfer": "↔️",
        "Savings Contribution": "🎯",
        "Payment": "💳"
    }
    return icons.get(txn_type, "📝")

def format_currency(amount):
    return f"₵{abs(amount):,.2f}" if amount >= 0 else f"-₵{abs(amount):,.2f}"

# ─── NAVIGATION ──────────────────────────────────────────────────────────────
# ─── NEW NAVIGATION SYSTEM ──────────────────────────────────────────────────────
if st.session_state.logged_in_user:
    # Define navigation items
    nav_items = [
        ("🏠", "Home"),
        ("👤", "Profile"),
        ("💱", "₵ Converter"),
        ("🎯", "Planner"),
        ("💡", "Finbot")
    ]
    
    if st.session_state.logged_in_user.is_admin:
        nav_items.append(("🔒", "Admin Panel"))
    
    nav_items.append(("🚪", "Logout"))
    
    # Create navigation columns
    nav_cols = st.columns(len(nav_items))
    
    # Render navigation buttons
    for i, (icon, label) in enumerate(nav_items):
        with nav_cols[i]:
            if st.button(f"{icon} {label}", key=f"nav_{label.lower().replace(' ', '_')}"):
                if label == "Logout":
                    st.session_state.logged_in_user = None
                    st.session_state.page = "login"
                    st.success("Logged out successfully.")
                    st.rerun()
                else:
                    st.session_state.page = label.lower().replace(" ", "_")
                    st.rerun()

else:
    # Login/Register navigation
    auth_cols = st.columns(2)
    with auth_cols[0]:
        if st.button("Register", key="nav_register"):
            st.session_state.page = "register"
            st.rerun()
    with auth_cols[1]:
        if st.button("Login", key="nav_login"):
            st.session_state.page = "login"
            st.rerun()

        

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
# Login Page
elif st.session_state.page == "login":
    col1, col2 = st.columns([1,2])
    with col1:
        st.image("assets/wb.png", width=150)  # Add your logo
        st.markdown("""
            <h2 style='color: #2563eb;'>Welcome Back</h2>
            <p style='color: #64748b;'>Securely access your accounts</p>
        """, unsafe_allow_html=True)
    with col2:
        with st.container(border=True):
            st.markdown("#### Sign In")
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="Enter your username")
                account_number = st.text_input("Account Number", placeholder="10-digit account number")
                pin = st.text_input("PIN", type="password", placeholder="4-digit PIN", max_chars=4)
                
                if st.form_submit_button("Login", type="primary"):
                    user = Account.find_by_login(username, account_number, pin)
                    if user:
                        if not user.is_active:
                            st.error("Account is frozen. Please contact support.")
                        else:
                            st.session_state.logged_in_user = user
                            st.session_state.page = "dashboard"
                            st.rerun()
                    else:
                        st.error("Invalid credentials. Please try again.")
            
            st.markdown("---")
            st.markdown("""
                <div style='text-align: center;'>
                    <p>Don't have an account? <a href='#' onclick='window.streamlit:componentBridge.setValue("register")'>Sign up</a></p>
                    <p><a href='#'>Forgot PIN?</a></p>
                </div>
            """, unsafe_allow_html=True)


elif st.session_state.logged_in_user and st.session_state.page == "home":
    user = st.session_state.logged_in_user

    
    carousel_html = """
    <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    /* Allow overflow so off-screen slides aren’t clipped */
    body {
        height: 100vh;
        display: grid;
        place-items: center;
    }

    main {
        position: relative;
        width: 100%;
        height: 100%;
        box-shadow: 0 3px 10px rgba(0,0,0,0.3);
        overflow: visible;
    }

    .slider {
        position: relative;
        list-style: none;
        height: 100%;
    }


    .item {
        width: 200px;
        height: 300px;
        position: absolute;
        top: 50%;
        transform: translateY(-50%);
        background-position: center;
        background-size: cover;
        border-radius: 20px;
        box-shadow: 0 20px 30px rgba(255,255,255,0.3) inset;
        transition: transform 0.1s, left 0.75s, top 0.75s, width 0.75s, height 0.75s;
    }

    /* Center slide styling */
    .item:nth-child(1),
    .item:nth-child(2) {
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        transform: none;
        border-radius: 0;
        box-shadow: none;
        opacity: 1;
    }

    .item:nth-child(3) { left: 50%; }
    .item:nth-child(4) { left: calc(50% + 220px); }
    .item:nth-child(5) { left: calc(50% + 440px); }
    .item:nth-child(6) { left: calc(50% + 660px); opacity: 0; }

    .content {
        width: min(30vw,400px);
        position: absolute;
        top: 50%;
        left: 3rem;
        transform: translateY(-50%);
        font: 400 0.85rem helvetica,sans-serif;
        color: white;
        text-shadow: 0 3px 8px rgba(0,0,0,0.5);
        opacity: 0;
        display: none;
    }

    .content .title {
        font-family: 'arial-black';
        text-transform: uppercase;
    }

    .content .description {
        line-height: 1.7;
        margin: 1rem 0 1.5rem;
        font-size: 0.8rem;
    }

    .content button {
        width: fit-content;
        background-color: rgba(0,0,0,0.1);
        color: white;
        border: 2px solid white;
        border-radius: 0.25rem;
        padding: 0.75rem;
        cursor: pointer;
    }

    .item:nth-of-type(2) .content {
        display: block;
        animation: show 0.75s ease-in-out 0.3s forwards;
    }

    @keyframes show {
        0% {
        filter: blur(5px);
        transform: translateY(calc(-50% + 75px));
        }
        100% {
        opacity: 1;
        filter: blur(0);
        }
    }

    .nav {
        position: absolute;
        bottom: 2rem;
        left: 50%;
        transform: translateX(-50%);
        z-index: 5;
        user-select: none;
    }

    .nav .btn {
        background-color: rgba(255,255,255,0.5);
        color: rgba(0,0,0,0.7);
        border: 2px solid rgba(0,0,0,0.6);
        margin: 0 0.25rem;
        padding: 0.75rem;
        border-radius: 50%;
        cursor: pointer;
    }

    .nav .btn:hover {
        background-color: rgba(255,255,255,0.3);
    }
    </style>


    <main>
    <ul class='slider'>
        <li class='item' style="background-image: url('https://media.istockphoto.com/id/2198966747/photo/couple-closing-real-estate-contract-with-real-estate-agent.jpg?s=1024x1024&w=is&k=20&c=Xs0AKdbMB9nXlhkPY_O0_POt0Zf7cTCe5gv5bjJhm4w=')">
        <div class='content'>
            <h2 class='title'>"Lossless Youths"</h2>
            <p class='description'>Lorem ipsum dolor sit amet consectetur adipisicing elit. Tempore fuga voluptatum...</p>
            <button>Read More</button>
        </div>
        </li>
        <li class='item' style="background-image: url('https://media.istockphoto.com/id/2179769227/photo/loan-and-lending-cash-for-asset-purchase-concept-digital-interface-featuring-loan-and.webp?b=1&s=612x612&w=0&k=20&c=0zaWGsC4mlxULh4xjvxEN-KvagynsDaq5r1Rr2dxtuQ=')">
        <div class='content'>
            <h2 class='title'>"Estrange Bond"</h2>
            <p class='description'>Lorem ipsum dolor sit amet consectetur adipisicing elit. Tempore fuga voluptatum...</p>
            <button>Read More</button>
        </div>
        </li>
        <li class='item' style="background-image: url('https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTJ8fGJhbmtpbmd8ZW58MHwwfDB8fHwy')">
        <div class='content'>
            <h2 class='title'>"The Gate Keeper"</h2>
            <p class='description'>Lorem ipsum dolor sit amet consectetur adipisicing elit. Tempore fuga voluptatum...</p>
            <button>Read More</button>
        </div>
        </li>
        <li class='item' style="background-image: url('https://cdn.pixabay.com/photo/2017/08/30/07/56/clock-2696234_640.jpg')">
        <div class='content'>
            <h2 class='title'>"Last Trace Of Us"</h2>
            <p class='description'>Lorem ipsum dolor sit amet consectetur adipisicing elit. Tempore fuga voluptatum...</p>
            <button>Read More</button>
        </div>
        </li>
        <li class='item' style="background-image: url('https://www.pexels.com/photo/man-couple-love-woman-7768204/')">
        <div class='content'>
            <h2 class='title'>"Urban Decay"</h2>
            <p class='description'>Lorem ipsum dolor sit amet consectetur adipisicing elit. Tempore fuga voluptatum...</p>
            <button>Read More</button>
        </div>
        </li>
        <li class='item' style="background-image: url('https://da.se/app/uploads/2015/09/simon-december1994.jpg')">
        <div class='content'>
            <h2 class='title'>"The Migration"</h2>
            <p class='description'>Lorem ipsum dolor sit amet consectetur adipisicing elit. Tempore fuga voluptatum...</p>
            <button>Read More</button>
        </div>
        </li>
    </ul>
    <nav class='nav'>
        <ion-icon class='btn prev' name="arrow-back-outline"></ion-icon>
        <ion-icon class='btn next' name="arrow-forward-outline"></ion-icon>
    </nav>
    </main>

    <script type="module" src="https://unpkg.com/ionicons@7.1.0/dist/ionicons/ionicons.esm.js"></script>
    <script nomodule src="https://unpkg.com/ionicons@7.1.0/dist/ionicons/ionicons.js"></script>
    <script>
    const slider = document.querySelector('.slider');
    function activate(e) {
        const items = document.querySelectorAll('.item');
        if (e.target.matches('.next')) slider.append(items[0]);
        if (e.target.matches('.prev')) slider.prepend(items[items.length-1]);
    }
    document.addEventListener('click', activate, false);
    </script>
    """

    # Embed with enough height to show the full width
    components.html(carousel_html, height=400, scrolling=True)

    st.markdown(f"""
        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;'>
            <div>
                <h1 style='margin-bottom: 0;'>Good {get_time_of_day()}, {user.name.split()[0]}</h1>
                <p style='color: #666; margin-top: 4px;'>
                    Account: {user.account_number} | Last login: {datetime.now().strftime('%b %d, %Y %I:%M %p')}
                </p>
            </div>
            <div style='background: var(--primary); color: white; padding: 12px 20px; border-radius: 10px; text-align: center;'>
                <p style='margin: 0; font-size: 14px;'>Available Balance</p>
                <h2 style='margin: 0; color: white;'>{format_currency(user.balance)}</h2>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    


    
    # Quick Actions with Icon Buttons
    st.subheader("Quick Actions")
    action_cols = st.columns(3)
    with action_cols[0]:
        if st.button("💳 Deposit", key="quick_deposit", use_container_width=True):
            st.session_state.page = "deposit"
            st.rerun()
    with action_cols[1]:
        if st.button("🏧 Withdraw", key="quick_withdraw", use_container_width=True):
            st.session_state.page = "withdraw"
            st.rerun()
    with action_cols[2]:
        if st.button("↗️ Transfer", key="quick_transfer", use_container_width=True):
            st.session_state.page = "transfer"
            st.rerun()

    
    # Account Overview Section
    st.markdown("---")
    st.subheader("Account Overview")
    
    col1, col2 = st.columns(2)
    with col1:
        with st.container():
            st.markdown("#### 💸 Spending Analytics")
            cursor.execute("""
                SELECT strftime('%Y-%m', timestamp) as month, 
                       SUM(amount) as total 
                FROM transactions 
                WHERE account_number=? AND amount < 0
                GROUP BY strftime('%Y-%m', timestamp)
                ORDER BY month DESC
                LIMIT 6
            """, (user.account_number,))
            spending_data = cursor.fetchall()
            
            if spending_data:
                df = pd.DataFrame(spending_data, columns=['Month', 'Amount'])
                df['Amount'] = df['Amount'].abs()
                df['Month'] = pd.to_datetime(df['Month'])
                
                # Use native Streamlit chart with style enhancements
                st.area_chart(
                    df.set_index('Month'), 
                    color="#ae2012",
                    use_container_width=True,
                    height=200
                )
            else:
                st.info("No spending data available")

    with col2:
        with st.container():
            st.markdown("#### 💰 Income Analytics")
            cursor.execute("""
                SELECT strftime('%Y-%m', timestamp) as month, 
                       SUM(amount) as total 
                FROM transactions 
                WHERE account_number=? AND amount > 0
                GROUP BY strftime('%Y-%m', timestamp)
                ORDER BY month DESC
                LIMIT 6
            """, (user.account_number,))
            income_data = cursor.fetchall()
            
            if income_data:
                df = pd.DataFrame(income_data, columns=['Month', 'Amount'])
                df['Month'] = pd.to_datetime(df['Month'])
                
                st.area_chart(
                    df.set_index('Month'), 
                    color="#0a9396",
                    use_container_width=True,
                    height=200
                )
            else:
                st.info("No income data available")
    
    # Recent Transactions with Enhanced UI
    st.markdown("---")
    st.subheader("Recent Transactions")
    
    history = user.get_transaction_history(5)
    if history:
        for txn in history:
            txn_type, amt, desc, ts, ref = txn
            color = "#0a9396" if amt > 0 else "#ae2012"
            icon = get_transaction_icon(txn_type)
            
            st.markdown(f"""
                <div class='transaction-item'>
                    <div style='font-size: 24px; margin-right: 16px;'>{icon}</div>
                    <div style='flex: 1;'>
                        <div style='font-weight: 600;'>{txn_type}</div>
                        <div style='font-size: 14px; color: #666;'>{desc}</div>
                        <div style='font-size: 12px; color: #999;'>{ts}</div>
                    </div>
                    <div style='
                        font-weight: 700;
                        color: {color};
                        font-size: 18px;
                    '>
                        {format_currency(amt)}
                    </div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No transactions yet")

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
                    st.success(f"Payment successful! New balance: ₵{user.balance:,.2f}")
                else:
                    st.warning(f"Payment status: {status}")
            except Exception as e:
                st.error(f"Verification failed: {e}")

# Withdrawal Page

elif st.session_state.logged_in_user and st.session_state.page == "withdraw":
    user = st.session_state.logged_in_user
    st.header("Withdraw Money to Mobile Money")

    st.write(f"Available Balance: {user.balance:,.2f} ₵")
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
                    st.success(f"Withdrawal successful! New balance: {user.balance:,.2f} ₵")
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

            pin = st.text_input("Enter 4‑digit PIN", type="password", max_chars=4, key="deposit_pin")
            
            submitted = st.form_submit_button("Send Money")
            
            if submitted:
                if not Account.find_by_login(user.username, user.account_number, pin):
                    st.error("Invalid PIN. Deposit cancelled.")

                elif not recipient_acc.isdigit() or len(recipient_acc) != 10:
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
elif st.session_state.logged_in_user and st.session_state.page == "planner":
    user = st.session_state.logged_in_user
    st.header("Savings Goals")
    
    tab1, tab2 = st.tabs(["My Goals", "New Goal"])

    with tab1:
        goals = user.get_savings_goals()
        if goals:
            for goal in goals:
                goal_id, name, target, current, target_date, created_at = goal
                progress = min(current / target * 100, 100)
                remaining = max(0, target - current)
                days_remaining = (datetime.strptime(target_date, "%Y-%m-%d") - datetime.now()).days
                
                with st.expander(f"{name} - {progress:.1f}% complete"):
                    st.write(f"**Target:** {format_currency(target)} by {target_date}")
                    st.write(f"**Saved:** {format_currency(current)}")
                    st.write(f"**Remaining:** {format_currency(remaining)}")
                    st.progress(int(progress))
                    
                    # Add prediction
                    prediction = savings_predictor.predict_achievement_date(goal_id, user.account_number)
    
                    if "Current daily average" in prediction:
                        parts = prediction.split("\n")
                        st.info(f"**{parts[0]}**")
                        st.info(f"**{parts[1]}**")
                        if "on track" in parts[2]:
                            st.success(f"**Status:** {parts[2]}")
                        else:
                            st.warning(f"**Status:** {parts[2]}")
                    else:
                        st.info(f"**Prediction:** {prediction}")
                    
                    # Daily savings needed calculation
                    if days_remaining > 0:
                        daily_needed = remaining / days_remaining
                        st.warning(f"**Daily savings needed:** {format_currency(daily_needed)}")
                    else:
                        st.error("Target date has passed!")
                    
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
    
    tab1, tab2, tab3 = st.tabs(["Accounts", "System", "Fraud"])
    
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
        st.markdown("---")
        st.subheader("🔄 Replace database file")
        uploaded_db = st.file_uploader(
            "Upload new SQLite DB file",
            type=["db"],
            help="Uploading will overwrite the current bank.db. Changes are ephemeral on redeploy.")
        if uploaded_db:
            # Write the uploaded bytes directly to bank.db
            with open("bank.db", "wb") as f:
                f.write(uploaded_db.getbuffer())
            st.success("✅ New database file uploaded! Please refresh the app to load changes.")


        
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

    with tab3:  # Fraud Monitoring tab
        st.header("Comprehensive Fraud Detection")
        
        # 1. System-wide Fraud Dashboard
        st.subheader("System-wide Fraud Analytics")
        
        # Get all flagged transactions with account info
        cursor.execute("""
            SELECT f.id, f.transaction_ref, a.name, a.account_number, 
                   t.amount, t.type, t.timestamp, t.description,
                   f.status, f.flagged_at, f.reviewed_by, f.reviewed_at
            FROM flagged_transactions f
            JOIN transactions t ON f.transaction_ref = t.reference_id
            JOIN accounts a ON t.account_number = a.account_number
            ORDER BY f.flagged_at DESC
        """)
        all_flagged = cursor.fetchall()
        
        # 2. Fraud Metrics Cards
        col1, col2, col3, col4 = st.columns(4)
        
        # Total flagged transactions
        total_flagged = len(all_flagged)
        col1.metric("🚨 Flagged Transactions", total_flagged)
        
        # Pending review count
        pending = sum(1 for txn in all_flagged if txn[8] == 'pending')
        col2.metric("⏳ Pending Review", pending, 
                   help="Transactions awaiting manual review")
        
        # Confirmed fraud
        confirmed = sum(1 for txn in all_flagged if txn[8] == 'confirmed')
        col3.metric("✅ Confirmed Fraud", confirmed, 
                   delta=f"{confirmed/total_flagged*100:.1f}%" if total_flagged > 0 else 0)
        
        # False positives
        false_pos = sum(1 for txn in all_flagged if txn[8] == 'approved')
        col4.metric("❌ False Alarms", false_pos, 
                   delta=f"{false_pos/total_flagged*100:.1f}%" if total_flagged > 0 else 0)
        
        # 3. Interactive Fraud Analysis
        st.subheader("📈 Fraud Patterns Analysis")
        
        # Convert to DataFrame for analysis
        if all_flagged:
            fraud_df = pd.DataFrame(all_flagged, columns=[
                "id", "reference", "name", "account", "amount", 
                "type", "timestamp", "description", "status", 
                "flagged_at", "reviewed_by", "reviewed_at"
            ])
            
            # Time-based analysis
            fraud_df['date'] = pd.to_datetime(fraud_df['timestamp']).dt.date
            fraud_df['hour'] = pd.to_datetime(fraud_df['timestamp']).dt.hour
            
            tab1, tab2, tab3 = st.tabs(["By Time", "By Type", "By Account"])
            
            with tab1:
                # Fraud by day
                st.write("**Fraud Cases by Day**")
                daily_fraud = fraud_df.groupby('date').size().reset_index(name='count')
                st.line_chart(daily_fraud.set_index('date'))
                
                # Fraud by hour
                st.write("**Fraud Cases by Hour of Day**")
                hourly_fraud = fraud_df.groupby('hour').size().reset_index(name='count')
                st.bar_chart(hourly_fraud.set_index('hour'))
            
            with tab2:
                # Fraud by transaction type
                st.write("**Fraud by Transaction Type**")
                type_fraud = fraud_df.groupby('type').agg({
                    'amount': ['count', 'mean', 'sum'],
                    'status': lambda x: (x == 'confirmed').mean()
                }).reset_index()
                type_fraud.columns = ['Type', 'Count', 'Avg Amount', 'Total Amount', 'Confirmation Rate']
                st.dataframe(type_fraud.sort_values('Count', ascending=False))
                
                # Amount distribution by type
                st.write("**Amount Distribution by Type**")
                st.bar_chart(fraud_df, x='type', y='amount')
            
            with tab3:
                # High-risk accounts
                st.write("**High-Risk Accounts**")
                account_fraud = fraud_df.groupby(['account', 'name']).agg({
                    'amount': ['count', 'sum'],
                    'status': lambda x: (x == 'confirmed').mean()
                }).reset_index()
                account_fraud.columns = ['Account', 'Name', 'Count', 'Total Amount', 'Confirmation Rate']
                st.dataframe(account_fraud.sort_values('Count', ascending=False))
                
                # Account age vs fraud
                st.write("**Account Age vs Fraud Cases**")
                cursor.execute("""
                    SELECT a.account_number, 
                           julianday('now') - julianday(a.created_at) as age_days,
                           COUNT(f.id) as fraud_count
                    FROM accounts a
                    LEFT JOIN flagged_transactions f ON f.account_number = a.account_number
                    GROUP BY a.account_number
                """)
                age_data = cursor.fetchall()
                age_df = pd.DataFrame(age_data, columns=['account', 'age_days', 'fraud_count'])
                st.scatter_chart(age_df, x='age_days', y='fraud_count')
        
        # 4. Detailed Transaction Review
        st.subheader("🔍 Transaction Review Queue")
        
        if all_flagged:
            # Filter options
            col1, col2 = st.columns(2)
            with col1:
                show_status = st.selectbox(
                    "Filter by Status",
                    ["All", "Pending", "Confirmed", "Approved"]
                )
            with col2:
                min_amount = st.number_input(
                    "Minimum Amount", 
                    min_value=0, 
                    value=0
                )
            
            # Apply filters
            filtered = fraud_df
            if show_status != "All":
                filtered = filtered[filtered['status'] == show_status.lower()]
            filtered = filtered[filtered['amount'] >= min_amount]
            
            # Display filtered transactions
            for _, row in filtered.iterrows():
                with st.expander(f"{row['type']} - {row['amount']:.2f} - {row['status']}"):
                    col1, col2 = st.columns([3,1])
                    with col1:
                        st.write(f"**Account:** {row['name']} ({row['account']})")
                        st.write(f"**Amount:** {row['amount']:.2f}")
                        st.write(f"**Date:** {row['timestamp']}")
                        st.write(f"**Description:** {row['description']}")
                        st.write(f"**Flagged At:** {row['flagged_at']}")
                        
                        if pd.notna(row['reviewed_at']):
                            st.write(f"**Reviewed By:** {row['reviewed_by']} at {row['reviewed_at']}")
                    
                    with col2:
                        # Action buttons
                        if row['status'] == 'pending':
                            if st.button("✅ Confirm Fraud", key=f"confirm_{row['id']}"):
                                cursor.execute("""
                                    UPDATE flagged_transactions 
                                    SET status='confirmed', 
                                        reviewed_by=?,
                                        reviewed_at=datetime('now')
                                    WHERE id=?
                                """, (st.session_state.logged_in_user.username, row['id']))
                                conn.commit()
                                st.success("Marked as confirmed fraud")
                                st.rerun()
                            
                            if st.button("👍 Approve", key=f"approve_{row['id']}"):
                                cursor.execute("""
                                    UPDATE flagged_transactions 
                                    SET status='approved', 
                                        reviewed_by=?,
                                        reviewed_at=datetime('now')
                                    WHERE id=?
                                """, (st.session_state.logged_in_user.username, row['id']))
                                conn.commit()
                                st.success("Transaction approved")
                                st.rerun()
                        
                        if st.button("🗑️ Delete Flag", key=f"delete_{row['id']}"):
                            cursor.execute("DELETE FROM flagged_transactions WHERE id=?", (row['id'],))
                            conn.commit()
                            st.warning("Flag removed")
                            st.rerun()
        else:
            st.info("No flagged transactions in the system")
        
        # 5. Proactive Fraud Detection
        st.subheader("🕵️ Proactive Detection")
        
        if st.button("Scan Recent Transactions for Fraud"):
            with st.spinner("Scanning last 500 transactions..."):
                # Get recent transactions
                cursor.execute("""
                    SELECT t.account_number, t.type, t.amount, t.timestamp, t.reference_id, a.name
                    FROM transactions t
                    JOIN accounts a ON t.account_number = a.account_number
                    ORDER BY t.timestamp DESC
                    LIMIT 500
                """)
                recent_txns = cursor.fetchall()
                
                # Check each transaction
                new_flags = 0
                for txn in recent_txns:
                    txn_data = {
                        'account_number': txn[0],
                        'type': txn[1],
                        'amount': txn[2],
                        'timestamp': txn[3],
                        'description': f"Proactive scan: {txn[1]}"
                    }
                    
                    # Skip if already flagged
                    cursor.execute("SELECT 1 FROM flagged_transactions WHERE transaction_ref=?", (txn[4],))
                    if cursor.fetchone():
                        continue
                    
                    if fraud_detector.is_fraudulent(txn_data):
                        try:
                            cursor.execute("""
                                INSERT INTO flagged_transactions 
                                (transaction_ref, account_number, flagged_at, status)
                                VALUES (?, ?, datetime('now'), 'pending')
                            """, (txn[4], txn[0]))
                            new_flags += 1
                        except:
                            pass
                
                conn.commit()
                st.success(f"Scan complete! Found {new_flags} new suspicious transactions")
                st.rerun()
 
# Currency Converter Page
elif st.session_state.logged_in_user and st.session_state.page == "₵_converter":
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

elif st.session_state.logged_in_user and st.session_state.page == "finbot":
    st.subheader("Financial Literacy Bot")
    
    user_input = st.text_input("Ask me about saving, investing, or debt:")
    
    if user_input:
        response = finance_chatbot.get_response(user_input)
        st.markdown(f"""
        <div style="background:#f0f2f6; padding:10px; border-radius:5px;">
            <strong>AI Assistant:</strong> {response}
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("**Try asking:**")
    st.markdown("- How to save money?")
    st.markdown("- Best investment options?")
    st.markdown("- What is compound interest?")
    st.markdown("- How to get out of debt?")
    st.markdown("- Explain inflation")
    st.markdown("- How does credit score work?")

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
        /* Make all Streamlit buttons a bit smaller */
        .stButton>button {
            width: 100%;
            border-radius: 5px;
            font-weight: bold;
            font-size: 13px !important;    /* <-- added */
            padding: 4px 8px !important;    /* optional: tighten spacing */
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



st.markdown("""
<style>
@import url("https://fonts.googleapis.com/css?family=IBM%20Plex%20Sans:500|IBM%20Plex%20Sans:300");

:root {
  --m: 4rem;
}
* {
  box-sizing: border-box;
  scroll-behavior: smooth;
}
body {
  background-color: black;
  color: white;
  font-family: "IBM Plex Sans";
  font-weight: 300;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 190vh;
  margin: 0;
  color: #d5d5d5;
  font-size: calc(0.3 * var(--m));
}
h2 {
  font-weight: 500;
  text-align: center;
  font-size: var(--m);
  margin: 0;
}
h3 {
  font-weight: 500;
  font-size: calc(0.6 * var(--m));
  margin: 0;
}
.card {
  height: calc(8 * var(--m));
  width: calc(12 * var(--m));
  background: linear-gradient(120deg, #ff8064, #725bdc);
  color: black;
  border-radius: calc(0.5 * var(--m));
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: var(--m);
  position: fixed;
  margin: calc(2 * var(--m)) calc(5 * var(--m)) calc(5 * var(--m)) calc(5 * var(--m));
  z-index: 100;
}
button {
  background-color: #000;
  font-size: calc(0.4 * var(--m));
  border: none;
  color: #e5e5e5;
  font-family: "IBM Plex Sans";
  font-weight: 400;
  padding: calc(0.35 * var(--m)) calc(0.8 * var(--m));
  border-radius: calc(0.3 * var(--m));
}
footer {
  margin-top: 90vh;
  z-index: 1;
  width: 100%;
  height: 50vh;
  display: flex;
  flex-direction: row;
  justify-content: space-evenly;
  align-items: flex-end;
  padding: 5rem 2vw;
  position: relative;
}
footer::before {
  content: "";
  position: absolute;
  inset: 0;
  background: #000000;
  z-index: -7;
}
.backdrop {
  z-index: -5;
  position: absolute;
  inset: 0;
  backdrop-filter: blur(40px);
  -webkit-backdrop-filter: blur(40px);
  mask-image: linear-gradient(
    rgba(0, 0, 0, 0),
    rgba(0, 0, 0, 0.5) 10%,
    rgba(0, 0, 0, 0.8) 20%,
    rgba(0, 0, 0, 1) 30%,
    rgb(0, 0, 0)
  );
  -webkit-mask-image: linear-gradient(
    rgba(0, 0, 0, 0),
    rgba(0, 0, 0, 0.5) 10%,
    rgba(0, 0, 0, 0.8) 20%,
    rgba(0, 0, 0, 1) 30%,
    rgb(0, 0, 0)
  );
}
.col {
  flex-direction: column;
  align-items: flex-start;
  justify-content: flex-start;
  padding: calc(0.3 * var(--m)) calc(0.8 * var(--m));
  width: 28%;
}
.col2,
.col3 {
  background-color: #121212;
  border-radius: calc(0.5 * var(--m));
}
img {
  height: calc(0.3 * var(--m));
  object-fit: cover;
}
.social {
  display: flex;
  flex-direction: row;
  justify-content: flex-start;
  gap: 1rem;
}
a {
  text-decoration: none;
  color: inherit;
}
.link {
  width: calc(0.8 * var(--m));
  height: calc(0.8 * var(--m));
  background-color: rgba(255, 255, 255, 0.1);
  border-radius: calc(0.1 * var(--m));
  display: flex;
  justify-content: center;
  align-items: center;
}
@media screen and (max-width: 1000px) {
  :root {
    --m: 3rem;
  }
}
@media screen and (max-width: 700px) {
  footer {
    flex-direction: column;
    padding: 5rem 20vw;
  }
  .col {
    width: 100%;
  }
}
</style>

<footer id="footer">
  <div class="col col1">
    <h3>Wirebuddy</h3>
    <p>Made with <span style="color: #BA6573;">❤</span> by Group3</p>
    <div class="social">
      <a href="https://codepen.io/Juxtopposed" target="_blank" class="link"><img src="https://assets.codepen.io/9051928/codepen_1.png" alt="" /></a>
      <a href="https://twitter.com/juxtopposed" target="_blank" class="link"><img src="https://assets.codepen.io/9051928/x.png" alt="" /></a>
      <a href="https://youtube.com/@juxtopposed" target="_blank" class="link"><img src="https://assets.codepen.io/9051928/youtube_1.png" alt="" /></a>
    </div>
    <p style="color: #818181; font-size: smaller">2025 © All Rights Reserved</p>
  </div>
  <div class="col col2">
    <p>About</p>
    <p>Our mission</p>
    <p>Privacy Policy</p>
    <p>Terms of service</p>
  </div>
  <div class="col col3">
    <p>Services</p>
    <p>Products</p>
    <p>Join our team</p>
    <p>Partner with us</p>
  </div>
  <div class="backdrop"></div>

<style>
  /* Footer text → pure white */
  footer, footer * {
    color: #ffffff !important;
  }

  /* No gap above footer */
  footer {
    margin-top: 0 !important;
    padding-top: 0 !important;   /* if you have any padding on the footer itself */
  }

  /* body or main container adds bottom margin/padding, zero it out */
  .stApp > div:first-child {
    margin-bottom: 0 !important;
    padding-bottom: 0 !important;
  }
</style>

  
</footer>
""", unsafe_allow_html=True)
