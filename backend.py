import sqlite3
from datetime import datetime
import requests
from forex_python.converter import CurrencyRates
import uuid
import streamlit as st

# Database connection and cursor
conn = sqlite3.connect("bank.db", check_same_thread=False)
cursor = conn.cursor()

# Create accounts table
cursor.execute('''
CREATE TABLE IF NOT EXISTS accounts (
    account_number TEXT PRIMARY KEY,
    name TEXT,
    pin TEXT,
    username TEXT UNIQUE,
    national_id TEXT,
    address TEXT,
    balance REAL DEFAULT 0.0,
    created_at TEXT,
    is_active BOOLEAN DEFAULT 1,
    is_admin BOOLEAN DEFAULT 0
)
''')

# Create transactions table
cursor.execute('''
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_number TEXT,
    type TEXT,
    amount REAL,
    description TEXT,
    timestamp TEXT,
    reference_id TEXT,
    FOREIGN KEY(account_number) REFERENCES accounts(account_number)
)
''')

# Create savings_goals table
cursor.execute('''
CREATE TABLE IF NOT EXISTS savings_goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_number TEXT,
    goal_name TEXT,
    target_amount REAL,
    current_amount REAL DEFAULT 0.0,
    target_date TEXT,
    created_at TEXT,
    FOREIGN KEY(account_number) REFERENCES accounts(account_number)
)
''')

# Create payments table for real deposits
cursor.execute('''
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_number TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'GHS',
    method TEXT NOT NULL,
    reference TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(account_number) REFERENCES accounts(account_number)
)
''')
conn.commit()

# Create disbursements table for withdrawals
cursor.execute('''
CREATE TABLE IF NOT EXISTS disbursements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_number TEXT NOT NULL,
    amount REAL NOT NULL,
    method TEXT NOT NULL,
    reference TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(account_number) REFERENCES accounts(account_number)
)
''')
conn.commit()

class Account:
    def __init__(self, name, account_number, pin, username, national_id, address,
                 balance=0.0, created_at=None, is_active=True, is_admin=False):
        self.name = name
        self.account_number = account_number
        self.pin = pin
        self.username = username
        self.national_id = national_id
        self.address = address
        self.balance = balance
        self.created_at = created_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.is_active = is_active
        self.is_admin = is_admin

    # Initialize default admin
cursor.execute("SELECT * FROM accounts WHERE is_admin = 1")
if not cursor.fetchone():
    admin = Account(
        name="Admin User",
        account_number= st.secrets["admin_number"],
        pin= st.secrets["admin_pin"],
        username= st.secrets["admin_username"],
        national_id="ADMIN000",
        address="Bank Headquarters",
        is_admin=True
    )
    admin.save_to_db()

    def save_to_db(self):
        cursor.execute(
            "INSERT INTO accounts (account_number, name, pin, username, national_id, address, balance, created_at, is_active, is_admin) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (self.account_number, self.name, self.pin, self.username, self.national_id, self.address, self.balance, self.created_at, self.is_active, self.is_admin)
        )
        conn.commit()

    @staticmethod
    def find_by_login(username, account_number, pin):
        cursor.execute(
            "SELECT name, account_number, pin, username, national_id, address, balance, created_at, is_active, is_admin FROM accounts WHERE username=? AND account_number=? AND pin=?",
            (username, account_number, pin)
        )
        row = cursor.fetchone()
        return Account(*row) if row else None
    
    @staticmethod
    def get_all_accounts():
        cursor.execute("""
            SELECT name, account_number, pin, username, national_id, address, 
                   balance, created_at, is_active, is_admin 
            FROM accounts
        """)
        return [Account(*row) for row in cursor.fetchall()]
    

    @staticmethod
    def get_by_account_number(account_number):
        cursor.execute(
            "SELECT name, account_number, pin, username, national_id, address, balance, created_at, is_active, is_admin FROM accounts WHERE account_number=?",
            (account_number,)
        )
        row = cursor.fetchone()
        return Account(*row) if row else None

    def deposit(self, amount):
        self.balance += amount
        cursor.execute("UPDATE accounts SET balance=? WHERE account_number=?", (self.balance, self.account_number))
        ref = str(uuid.uuid4())[:8]
        self._record_transaction("Deposit", amount, "Deposit made", ref)
        conn.commit()
        return ref

    @staticmethod
    def get_all_accounts():
        cursor.execute("""
            SELECT name, account_number, pin, username, national_id, address, 
                   balance, created_at, is_active, is_admin 
            FROM accounts
        """)
        return [Account(*row) for row in cursor.fetchall()]
    

    def withdraw(self, amount):
        if self.balance >= amount:
            self.balance -= amount
            cursor.execute("UPDATE accounts SET balance=? WHERE account_number=?", 
                         (self.balance, self.account_number))
            reference_id = str(uuid.uuid4())[:8]
            self._record_transaction("Withdrawal", amount, "Withdrawal made", reference_id)
            conn.commit()
            return reference_id
        return None

    def send_money(self, recipient_acc_no, amount):
        try:
            recipient = Account.get_by_account_number(recipient_acc_no)
            if not recipient:
                return None, "Recipient not found"
            if not recipient.is_active:
                return None, "Recipient account is frozen"
            if self.balance < amount:
                return None, "Insufficient funds"
                
            self.balance -= amount
            recipient.balance += amount
            
            cursor.execute("UPDATE accounts SET balance=? WHERE account_number=?", 
                         (self.balance, self.account_number))
            cursor.execute("UPDATE accounts SET balance=? WHERE account_number=?", 
                         (recipient.balance, recipient.account_number))
            
            reference_id = str(uuid.uuid4())[:8]
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Sender transaction
            cursor.execute("""
                INSERT INTO transactions 
                (account_number, type, amount, description, timestamp, reference_id)
                VALUES (?, 'Transfer Out', ?, ?, ?, ?)
            """, (self.account_number, -amount, f"To: {recipient_acc_no}", timestamp, reference_id))
            
            # Recipient transaction
            cursor.execute("""
                INSERT INTO transactions 
                (account_number, type, amount, description, timestamp, reference_id)
                VALUES (?, 'Transfer In', ?, ?, ?, ?)
            """, (recipient_acc_no, amount, f"From: {self.account_number}", timestamp, reference_id))
            
            conn.commit()
            return reference_id, "Transfer successful"
            
        except Exception as e:
            conn.rollback()
            return None, str(e)

    def _record_transaction(self, txn_type, amount, description, reference_id):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            INSERT INTO transactions 
            (account_number, type, amount, description, timestamp, reference_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (self.account_number, txn_type, amount, description, timestamp, reference_id))
        conn.commit()

    def get_transaction_history(self, limit=None):
        query = """
            SELECT type, amount, description, timestamp, reference_id 
            FROM transactions 
            WHERE account_number=? 
            ORDER BY timestamp DESC
        """
        if limit:
            query += f" LIMIT {limit}"
        cursor.execute(query, (self.account_number,))
        return cursor.fetchall()

    def get_transaction_by_reference(self, reference_id):
        cursor.execute("""
            SELECT type, amount, description, timestamp, reference_id 
            FROM transactions 
            WHERE account_number=? AND reference_id=?
        """, (self.account_number, reference_id))
        return cursor.fetchone()

    def update_profile_in_db(self):
        cursor.execute("""
            UPDATE accounts
            SET name=?, username=?, address=?, national_id=?, pin=?, is_active=?
            WHERE account_number=?
        """, (
            self.name, self.username, self.address, 
            self.national_id, self.pin, self.is_active,
            self.account_number
        ))
        conn.commit()

    def toggle_account_status(self):
        self.is_active = not self.is_active
        cursor.execute("""
            UPDATE accounts
            SET is_active=?
            WHERE account_number=?
        """, (self.is_active, self.account_number))
        conn.commit()
        return self.is_active

    # Savings goals methods
    def create_savings_goal(self, goal_name, target_amount, target_date):
        cursor.execute("""
            INSERT INTO savings_goals 
            (account_number, goal_name, target_amount, target_date, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            self.account_number, goal_name, target_amount, 
            target_date, datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        conn.commit()
        return cursor.lastrowid

    def get_savings_goals(self):
        cursor.execute("""
            SELECT id, goal_name, target_amount, current_amount, target_date, created_at
            FROM savings_goals
            WHERE account_number=?
            ORDER BY target_date
        """, (self.account_number,))
        return cursor.fetchall()

    def contribute_to_goal(self, goal_id, amount):
        if amount <= 0:
            return False, "Amount must be positive"
        if self.balance < amount:
            return False, "Insufficient funds in main account"
        
        try:
            # Get current goal amount
            cursor.execute("SELECT current_amount FROM savings_goals WHERE id=?", (goal_id,))
            current = cursor.fetchone()[0]
            
            # Update balances
            self.balance -= amount
            new_goal_amount = current + amount
            
            cursor.execute("UPDATE accounts SET balance=? WHERE account_number=?", 
                         (self.balance, self.account_number))
            cursor.execute("UPDATE savings_goals SET current_amount=? WHERE id=?", 
                         (new_goal_amount, goal_id))
            
            # Record transaction
            reference_id = str(uuid.uuid4())[:8]
            self._record_transaction(
                "Savings Contribution", 
                amount, 
                f"Contribution to goal ID: {goal_id}", 
                reference_id
            )
            
            conn.commit()
            return True, f"Successfully added {format_currency(amount)} to goal"
        except Exception as e:
            conn.rollback()
            return False, str(e)

    def withdraw_from_goal(self, goal_id, amount):
        try:
            # Check goal balance first
            cursor.execute("""
                SELECT current_amount FROM savings_goals
                WHERE id=? AND account_number=?
            """, (goal_id, self.account_number))
            current_amount = cursor.fetchone()[0]
            
            if current_amount < amount:
                return False, "Insufficient funds in goal"
                
            # Perform withdrawal
            self.balance += amount
            cursor.execute("UPDATE accounts SET balance=? WHERE account_number=?", 
                         (self.balance, self.account_number))
            
            cursor.execute("""
                UPDATE savings_goals
                SET current_amount = current_amount - ?
                WHERE id=? AND account_number=?
            """, (amount, goal_id, self.account_number))
            
            # Record transaction
            reference_id = str(uuid.uuid4())[:8]
            self._record_transaction(
                "Savings Withdrawal", 
                amount, 
                f"Withdrawal from goal ID: {goal_id}", 
                reference_id
            )
            
            conn.commit()
            return True, f"Successfully withdrew {format_currency(amount)} from goal"
        except Exception as e:
            conn.rollback()
            return False, str(e)

    def delete_savings_goal(self, goal_id):
        cursor.execute("""
            DELETE FROM savings_goals
            WHERE id=? AND account_number=?
        """, (goal_id, self.account_number))
        conn.commit()
        return cursor.rowcount > 0
    

class FinanceChatbot:
    @staticmethod
    def get_response(query):
        responses = {
            "how to save money": "Start by budgeting, cutting unnecessary expenses, and automating savings.",
            "best investment options": "Consider stocks, bonds, mutual funds, or real estate based on your risk tolerance.",
            "what is compound interest": "It's interest on both the initial principal and accumulated interest over time.",
            "how to get out of debt": "Try the snowball or avalanche method, and avoid new debt.",
            "default": "I can help with budgeting, saving, investing, and debt management. Ask me anything!"
        }
        
        query = query.lower()
        for key in responses:
            if key in query:
                return responses[key]
        return responses["default"]


class CurrencyConverter:
    SUPPORTED_CURRENCIES = ["USD", "EUR", "GBP", "KES", "GHS"]
    
    @staticmethod
    def get_rates():
        try:
            response = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=3)
            rates = response.json()['rates']
            if "GHS" not in rates:
                rates["GHS"] = 11.50
            return rates
        except:
            try:
                c = CurrencyRates()
                return {currency: c.get_rate("USD", currency) for currency in CurrencyConverter.SUPPORTED_CURRENCIES}
            except:
                return {
                    'USD': 1.0,
                    'EUR': 0.93,
                    'GBP': 0.79,
                    'KES': 141.50,
                    'GHS': 11.90
                }

    @staticmethod
    def convert(amount, from_currency, to_currency):
        rates = CurrencyConverter.get_rates()
        if from_currency not in rates or to_currency not in rates:
            raise ValueError("Unsupported currency")
        usd_value = amount / rates[from_currency]
        return usd_value * rates[to_currency]


class ReceiptGenerator:
    @staticmethod
    def generate_receipt(transaction_data, account):
        receipt = f"""
        ╔══════════════════════════════════╗
        ║        SMARTBANK RECEIPT         ║
        ╠══════════════════════════════════╣
        ║ Date: {transaction_data[3]:<25}║
        ║ Transaction: {transaction_data[0]:<16}║
        ║ Account: {account.account_number:<20}║
        ║ Name: {account.name:<23}║
        ╠══════════════════════════════════╣
        ║ Amount: {format_currency(abs(transaction_data[1])):<21}║
        ║ Reference: {transaction_data[4]:<17}║
        ╠══════════════════════════════════╣
        ║ Description:                     ║
        ║ {transaction_data[2]:<30}║
        ╚══════════════════════════════════╝
        """
        return receipt

# ---------- Paystack Integration ----------
PAYSTACK_SECRET = st.secrets["api_key"]
HEADERS = {"Authorization": f"Bearer {PAYSTACK_SECRET}"}

def initiate_deposit(account, amount, method="card"):
    payload = {
        "email": f"{account.username}@example.com",
        "amount": int(amount * 100),
        "currency": "GHS",
        "metadata": {"account_number": account.account_number}
    }
    resp = requests.post(
        "https://api.paystack.co/transaction/initialize",
        json=payload, headers=HEADERS, timeout=5
    )
    data = resp.json()
    if not data.get("status"):
        raise Exception("Paystack init error: " + data.get("message", ""))
    ref = data["data"]["reference"]
    auth_url = data["data"]["authorization_url"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO payments (account_number, amount, currency, method, reference, status, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
        (account.account_number, amount, "GHS", method, ref, "pending", now, now)
    )
    conn.commit()
    return auth_url, ref

def initiate_deposit(account, amount, method="card"):
    payload = {
        "email": f"{account.username}@example.com",
        "amount": int(amount * 100),
        "currency": "GHS",
        "metadata": {"account_number": account.account_number}
    }
    resp = requests.post(
        "https://api.paystack.co/transaction/initialize",
        json=payload, headers=HEADERS, timeout=5
    )
    data = resp.json()
    if not data.get("status"):
        raise Exception("Paystack init error: " + data.get("message", ""))
    ref = data["data"]["reference"]
    auth_url = data["data"]["authorization_url"]
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute(
        "INSERT OR IGNORE INTO payments (account_number, amount, currency, method, reference, status, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
        (account.account_number, amount, "GHS", method, ref, "pending", now, now)
    )
    conn.commit()
    return auth_url, ref


def verify_payment(reference):
    # Fetch existing status to prevent duplicate credits
    cursor.execute("SELECT status FROM payments WHERE reference=?", (reference,))
    row = cursor.fetchone()
    old_status = row[0] if row else None

    # Verify transaction status with Paystack
    resp = requests.get(
        f"https://api.paystack.co/transaction/verify/{reference}",
        headers=HEADERS, timeout=5
    )
    data = resp.json()
    if not data.get("status"):  # API-level failure
        raise Exception("Verification error: " + data.get("message", ""))
    status = data["data"]["status"]
    amount = data["data"]["amount"] / 100  # convert back
    meta = data["data"]["metadata"]
    account_no = meta.get("account_number")
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Update payment record
    cursor.execute(
        "UPDATE payments SET status=?, updated_at=? WHERE reference=?",
        (status, now, reference)
    )
    conn.commit()

    # If successful and was not already credited, credit user's balance
    if status == 'success' and old_status != 'success':
        from backend_update import Account
        acct = Account.get_by_account_number(account_no)
        if acct:
            acct.deposit(amount)
    return status

# ---------- Mobile Money Withdrawal ----------
# Add at the top
PAYSTACK_SECRET_KEY = st.secrets["api_key"]  # Replace with your actual key
headers = {
    "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
    "Content-Type": "application/json"
}

def create_transfer_recipient(name, account_number, bank_code):
    url = "https://api.paystack.co/transferrecipient"
    data = {
        "type": "mobile_money",
        "name": name,
        "account_number": account_number,
        "bank_code": bank_code,
        "currency": "GHS"
    }
    res = requests.post(url, json=data, headers=headers)
    res_data = res.json()
    if res_data.get("status"):
        return res_data["data"]["recipient_code"]
    else:
        raise Exception(f"Recipient creation failed: {res_data.get('message')}")

def initiate_withdrawal(account, amount, momo_number):
    transfer_ref = str(uuid.uuid4())
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Create recipient (use a sample bank_code for MoMo, e.g. MTN = "MTN")
    recipient_code = create_transfer_recipient(account.name, momo_number, "MTN")

    # Initiate transfer
    transfer_url = "https://api.paystack.co/transfer"
    transfer_data = {
        "source": "balance",
        "amount": int(amount * 100),  # Convert to kobo
        "recipient": recipient_code,
        "reason": f"Withdrawal to {momo_number}",
        "reference": transfer_ref
    }
    res = requests.post(transfer_url, json=transfer_data, headers=headers)
    res_data = res.json()

    if not res_data.get("status"):
        raise Exception(f"Transfer failed: {res_data.get('message')}")

    # Record disbursement request
    cursor.execute(
        "INSERT OR IGNORE INTO disbursements (account_number, amount, method, reference, status, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
        (account.account_number, amount, "momo", transfer_ref, "pending", now, now)
    )

    # Deduct balance immediately
    account.balance -= amount
    cursor.execute("UPDATE accounts SET balance=? WHERE account_number=?", (account.balance, account.account_number))

    # Record transaction
    withdraw_ref = str(uuid.uuid4())[:8]
    cursor.execute(
        "INSERT INTO transactions (account_number, type, amount, description, timestamp, reference_id) VALUES (?,?,?,?,?,?)",
        (account.account_number, "Withdrawal", -amount, f"MoMo to {momo_number}", now, withdraw_ref)
    )
    conn.commit()
    return transfer_ref

def verify_withdrawal(reference):
    url = f"https://api.paystack.co/transfer/verify/{reference}"
    res = requests.get(url, headers=headers)
    res_data = res.json()
    if res_data.get("status"):
        status = res_data["data"]["status"]
    else:
        raise Exception("Verification failed: Unable to fetch status")

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute(
        "UPDATE disbursements SET status=?, updated_at=? WHERE reference=?",
        (status, now, reference)
    )
    conn.commit()
    return status
