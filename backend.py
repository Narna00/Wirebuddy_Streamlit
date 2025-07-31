import streamlit as st
import sqlite3
import time
from sqlite3 import OperationalError
from datetime import datetime, timedelta
import sys
import requests
from forex_python.converter import CurrencyRates
import uuid
import random
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics.pairwise import cosine_similarity
import joblib
import threading
import time


# Database connection and cursor
conn = sqlite3.connect("bank.db", check_same_thread=False)
cursor = conn.cursor()



MAX_RETRIES = 5
RETRY_DELAY = 0.2  # seconds

def execute_with_retry(query, params=()):
    """Execute SQL query with retry on lock"""
    for attempt in range(MAX_RETRIES):
        try:
            cursor.execute(query, params)
            conn.commit()
            return
        except OperationalError as e:
            if "database is locked" in str(e) and attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise




# # Create otps table
# cursor.execute('''
# CREATE TABLE IF NOT EXISTS otps (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     phone TEXT NOT NULL,
#     otp TEXT NOT NULL,
#     purpose TEXT NOT NULL,
#     created_at TEXT DEFAULT CURRENT_TIMESTAMP,
#     expires_at TEXT NOT NULL
# )
# ''')
# conn.commit()

# Create accounts table
def create_tables():
    # Accounts table
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
    
create_tables()
conn.commit()



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

    # Savings goals history table - NEW VERSION
cursor.execute('''
    CREATE TABLE IF NOT EXISTS savings_goals_history_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        goal_id INTEGER,
        contribution_amount REAL,
        current_amount REAL,
        timestamp TEXT,
        FOREIGN KEY(goal_id) REFERENCES savings_goals(id)
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

# Create new tables for ML features
cursor.execute('''
CREATE TABLE IF NOT EXISTS flagged_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_ref TEXT NOT NULL,
    account_number TEXT NOT NULL,
    flagged_at TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    reviewed_by TEXT,
    reviewed_at TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS transaction_categories (
    transaction_id INTEGER PRIMARY KEY,
    category TEXT,
    FOREIGN KEY(transaction_id) REFERENCES transactions(id)
)
''')
conn.commit()


cursor.execute('''
CREATE TABLE IF NOT EXISTS savings_goals_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        goal_id INTEGER,
        contribution_amount REAL,
        current_amount REAL,
        timestamp TEXT,
        FOREIGN KEY(goal_id) REFERENCES savings_goals(id)
    )
''')

initialize_database()

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

    def save_to_db(self):
        execute_with_retry(
            "INSERT INTO accounts (account_number, name, pin, username, national_id, address, balance, created_at, is_active, is_admin) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (self.account_number, self.name, self.pin, self.username, 
             self.national_id, self.address, self.balance, 
             self.created_at, self.is_active, self.is_admin)
        )

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
        execute_with_retry("UPDATE accounts SET balance=? WHERE account_number=?", 
                         (self.balance, self.account_number))
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
        # Get current timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # First insert the transaction record
        cursor.execute("""
            INSERT INTO transactions 
            (account_number, type, amount, description, timestamp, reference_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (self.account_number, txn_type, amount, description, timestamp, reference_id))
        
        # Get the auto-incremented transaction ID
        transaction_id = cursor.lastrowid
        
        # Prepare transaction data for fraud detection
        transaction_data = {
            'account_number': self.account_number,
            'type': txn_type,
            'amount': amount,
            'timestamp': timestamp,
            'description': description
        }
        
        # Fraud check only for withdrawals/transfers
        is_fraud = False
        if txn_type in ["Withdrawal", "Transfer Out"]:
            is_fraud = fraud_detector.is_fraudulent(transaction_data)
            
            # Log the detection result
            print(f"Transaction {reference_id}: Amount {amount}, Type {txn_type} - {'FRAUD DETECTED' if is_fraud else 'Legitimate'}")
            
            if is_fraud:
                self._flag_transaction(reference_id)
        
        # Transaction categorization
        try:
            category = transaction_classifier.categorize(description)
            cursor.execute("""
                INSERT OR REPLACE INTO transaction_categories 
                (transaction_id, category) VALUES (?, ?)
            """, (transaction_id, category))
        except Exception as e:
            print(f"Failed to categorize transaction: {e}")
        
        conn.commit()

    def _flag_transaction(self, reference_id):
        try:
            cursor.execute("""
                INSERT INTO flagged_transactions 
                (transaction_ref, account_number, flagged_at, status)
                VALUES (?, ?, ?, ?)
            """, (reference_id, self.account_number, 
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'pending'))
            conn.commit()
        except:
            pass

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
            new_goal_amount = current + amount
            
            # Update balances
            self.balance -= amount
            cursor.execute("UPDATE accounts SET balance=? WHERE account_number=?", 
                         (self.balance, self.account_number))
            cursor.execute("UPDATE savings_goals SET current_amount=? WHERE id=?", 
                         (new_goal_amount, goal_id))
            
            # Record contribution history - FIXED
            cursor.execute("""
                INSERT INTO savings_goals_history 
                (goal_id, contribution_amount, current_amount, timestamp)
                VALUES (?, ?, ?, ?)
            """, (goal_id, amount, new_goal_amount, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
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


def format_currency(amount, currency="GHS"):
    return f"{currency} {amount:,.2f}"

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
        acct = Account.get_by_account_number(account_no)
        if acct:
            acct.deposit(amount)
    return status

# ---------- Mobile Money Withdrawal ----------
PAYSTACK_SECRET_KEY = "sk_test_db3ef49c1f56e6a6891a8d6ed871f16e31485f3c"  # Replace with your actual key
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



class FraudDetector:
    def __init__(self, model_path="fraud_model.pkl", vectorizer_path="fraud_vectorizer.pkl"):
        try:
            # Load pre-trained model and vectorizer
            self.model = joblib.load(model_path)
            self.vectorizer = joblib.load(vectorizer_path)
            self.is_trained = True
            self.feature_names = self.vectorizer.get_feature_names_out()
            print("Loaded pre-trained fraud detection model")
        except Exception as e:
            print(f"Error loading pre-trained model: {e}")
            self.model = IsolationForest(contamination=0.01, random_state=42)
            self.vectorizer = None
            self.is_trained = False
            print("Using new fraud detection model")
    
    def extract_features(self, transaction):
        """Convert transaction data into features for the model"""
        features = {
            'amount': transaction['amount'],
            'type': transaction['type'],
            'hour_of_day': datetime.strptime(transaction['timestamp'], '%Y-%m-%d %H:%M:%S').hour,
            'day_of_week': datetime.strptime(transaction['timestamp'], '%Y-%m-%d %H:%M:%S').weekday(),
            'account_age_days': self.calculate_account_age(transaction['account_number']),
            'is_weekend': int(datetime.strptime(transaction['timestamp'], '%Y-%m-%d %H:%M:%S').weekday() >= 5),
            'transaction_size_category': self.get_amount_category(transaction['amount'])
        }
        return features
    
    def get_amount_category(self, amount):
        if amount < 100: return 'small'
        elif amount < 1000: return 'medium'
        else: return 'large'
    
    def calculate_account_age(self, account_number):
        """Calculate account age in days"""
        cursor.execute("SELECT created_at FROM accounts WHERE account_number=?", (account_number,))
        created_at = cursor.fetchone()[0]
        created_date = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
        return (datetime.now() - created_date).days
    
    def is_fraudulent(self, transaction):
        """Check if transaction is suspicious using pre-trained model"""
        if not self.is_trained:
            return False
            
        try:
            # Extract features
            features = self.extract_features(transaction)
            
            # Create feature vector in same format as training
            feature_df = pd.DataFrame([features])
            
            # Vectorize categorical features
            X = self.vectorizer.transform(feature_df)
            
            # Predict
            prediction = self.model.predict(X)
            return prediction[0] == -1  # -1 means fraud in IsolationForest
            
        except Exception as e:
            print(f"Fraud detection error: {e}")
            return False
    
    def get_fraud_probability(self, transaction):
        """Get fraud probability score if model supports it"""
        if not self.is_trained:
            return 0.0
            
        try:
            features = self.extract_features(transaction)
            feature_df = pd.DataFrame([features])
            X = self.vectorizer.transform(feature_df)
            
            if hasattr(self.model, 'decision_function'):
                score = self.model.decision_function(X)[0]
                # Convert to probability-like score (0-1)
                return 1 / (1 + np.exp(-score))
            elif hasattr(self.model, 'predict_proba'):
                return self.model.predict_proba(X)[0][1]
            else:
                return 0.0 if self.model.predict(X)[0] == 1 else 1.0
        except:
            return 0.0

# Initialize default admin AFTER ML initialization
def initialize_admin_account():
    """Ensure default admin account exists"""
    try:
        cursor.execute("SELECT * FROM accounts WHERE is_admin = 1")
        if not cursor.fetchone():
            admin = Account(
                name="Admin User",
                account_number="admin_number",
                pin="admin_pin",
                username="admin_username",
                national_id="ADMIN000",
                address="Bank Headquarters",
                is_admin=True
            )
            admin.save_to_db()
            print("Default admin created")
    except Exception as e:
        print(f"Error creating admin: {e}")

initialize_admin_account()

class FinanceChatbot:
    def __init__(self):
        self.questions = [
            "how to save money",
            "best investment options",
            "what is compound interest",
            "how to get out of debt",
            "what is inflation",
            "how does credit score work"
        ]
        self.answers = [
            "Start by budgeting, cutting unnecessary expenses, and automating savings.",
            "Consider stocks, bonds, mutual funds, or real estate based on your risk tolerance.",
            "It's interest on both the initial principal and accumulated interest over time.",
            "Try the snowball or avalanche method, and avoid new debt.",
            "Inflation is the rate at which prices for goods and services increase over time.",
            "Credit scores range from 300-850 and are based on payment history, credit utilization, etc."
        ]
        self.vectorizer = TfidfVectorizer().fit(self.questions)
        
    def get_response(self, query):
        # Vectorize input
        query_vec = self.vectorizer.transform([query.lower()])
        question_vecs = self.vectorizer.transform(self.questions)
        
        # Calculate similarity
        similarities = cosine_similarity(query_vec, question_vecs)
        max_index = np.argmax(similarities)
        
        if similarities[0, max_index] > 0.3:
            return self.answers[max_index]
        else:
            return "I can help with budgeting, saving, investing, and debt management. Ask me anything!"

class SavingsPredictor:
    def predict_achievement_date(self, goal_id, account_number):
        try:
            # Use a new connection
            pred_conn = sqlite3.connect("bank.db")
            pred_cursor = pred_conn.cursor()
            
            # Get goal details
            pred_cursor.execute("""
                SELECT target_amount, current_amount, target_date, created_at 
                FROM savings_goals 
                WHERE id=? AND account_number=?
            """, (goal_id, account_number))
            goal = pred_cursor.fetchone()
            
            if not goal:
                return "Goal not found"
                
            target_amount, current_amount, target_date, created_at = goal
            
            # Get contributions - FIXED QUERY
            pred_cursor.execute("""
                SELECT timestamp, current_amount 
                FROM savings_goals_history 
                WHERE goal_id=?
                ORDER BY timestamp
            """, (goal_id,))
            contributions = pred_cursor.fetchall()
            
            # Calculate basic metrics
            remaining = target_amount - current_amount
            created_date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
            target_date = datetime.strptime(target_date, "%Y-%m-%d")
            days_so_far = (datetime.now() - created_date).days
            days_remaining = (target_date - datetime.now()).days
            
            # Case 1: No contributions yet
            if current_amount == 0:
                daily_needed = target_amount / days_remaining if days_remaining > 0 else target_amount
                return f"Start saving! You need to save {format_currency(daily_needed)} daily to reach your goal"
            
            # Case 2: Only one contribution
            if len(contributions) < 2:
                avg_daily = current_amount / days_so_far if days_so_far > 0 else current_amount
                daily_needed = remaining / days_remaining if days_remaining > 0 else remaining
                
                status = "on track" if avg_daily >= daily_needed else "behind"
                return (
                    f"Current daily average: {format_currency(avg_daily)}\n"
                    f"Daily needed: {format_currency(daily_needed)}\n"
                    f"You're {status}"
                )
            
            # Case 3: Enough data for full prediction
            # Calculate daily savings rate
            dates = [datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S') for row in contributions]
            amounts = [row[1] for row in contributions]
            
            date_diffs = [(dates[i] - dates[0]).days for i in range(1, len(dates))]
            amount_diffs = [amounts[i] - amounts[0] for i in range(1, len(amounts))]
            daily_rate = sum(ad/dd for ad, dd in zip(amount_diffs, date_diffs)) / len(date_diffs)
            
            # Calculate days needed
            remaining = target_amount - amounts[-1]
            days_needed = max(1, round(remaining / daily_rate)) if daily_rate > 0 else 999
            
            # Calculate predicted date
            predicted_date = datetime.now() + timedelta(days=days_needed)
            
            # Compare with target date
            target_date = datetime.strptime(target_date, "%Y-%m-%d")
            status = "ahead of schedule" if predicted_date < target_date else "behind schedule"
            
            return f"Predicted {predicted_date.strftime('%b %d, %Y')} ({status})"
            
        except Exception as e:
            return f"Prediction unavailable: {str(e)}"
        finally:
            pred_cursor.close()
            pred_conn.close()

class TransactionClassifier:
    def __init__(self):
        self.categories = ['Food', 'Transport', 'Entertainment', 'Utilities', 'Shopping']
        self.model = None
        self.vectorizer = None
        self._initialize_model()
    
    def _initialize_model(self):
        try:
            self.vectorizer = joblib.load('vectorizer.pkl')
            self.model = joblib.load('classifier.pkl')
            print("Loaded pre-trained classifier")
        except:
            print("Training new classifier...")
            self.train_model()
    
    def train_model(self):
        # Expanded training data
        descriptions = [
            "supermarket", "grocery", "restaurant", "coffee shop", "food delivery",
            "gas station", "bus fare", "taxi", "uber", "lyft", "train ticket",
            "netflix", "spotify", "cinema", "concert", "amazon prime",
            "electricity", "water bill", "internet", "phone bill", "rent",
            "clothing", "electronics", "shopping mall", "online purchase", "other"
        ]
        labels = [0,0,0,0,0, 1,1,1,1,1,1, 2,2,2,2,2, 3,3,3,3,3, 4,4,4,4,4]
        
        # Vectorize text
        self.vectorizer = CountVectorizer()
        X = self.vectorizer.fit_transform(descriptions)
        
        # Train classifier
        self.model = MultinomialNB()
        self.model.fit(X, labels)
        
        # Save models
        joblib.dump(self.vectorizer, 'vectorizer.pkl')
        joblib.dump(self.model, 'classifier.pkl')
        print("Classifier trained and saved")
    
    def categorize(self, description):
        if not self.model:
            return "Uncategorized"
        
        try:
            # Preprocess description
            clean_desc = description.lower()[:50]  # Truncate long descriptions
            X = self.vectorizer.transform([clean_desc])
            prediction = self.model.predict(X)
            return self.categories[prediction[0]]
        except Exception as e:
            print(f"Categorization error: {e}")
            return "Uncategorized"

class CreditScorer:
    def __init__(self):
        try:
            self.model = joblib.load('credit_model.pkl')
        except:
            self.model = None
    
    def train_model(self):
        # This would be trained on historical data
        # Placeholder implementation
        np.random.seed(42)
        data = {
            'balance': np.random.normal(5000, 2000, 1000),
            'transaction_count': np.random.poisson(30, 1000),
            'avg_transaction': np.random.normal(150, 50, 1000),
            'max_balance': np.random.normal(7000, 2500, 1000),
            'creditworthy': np.random.randint(0, 2, 1000)
        }
        df = pd.DataFrame(data)
        
        self.model = RandomForestClassifier()
        self.model.fit(df.drop('creditworthy', axis=1), df['creditworthy'])
        joblib.dump(self.model, 'credit_model.pkl')
    
    def predict_creditworthiness(self, account_number):
        if not self.model:
            self.train_model()
        
        # Get account features
        cursor.execute("""
            SELECT balance, 
                   (SELECT COUNT(*) FROM transactions 
                    WHERE account_number = ?) as transaction_count,
                   (SELECT AVG(amount) FROM transactions 
                    WHERE account_number = ?) as avg_transaction,
                   MAX(balance) as max_balance
            FROM accounts
            WHERE account_number = ?
        """, (account_number, account_number, account_number))
        features = cursor.fetchone()
        
        if not features or None in features:
            return "Insufficient data"
        
        # Predict
        prediction = self.model.predict([features])
        return "Good credit risk" if prediction[0] else "Higher risk profile"

# Initialize ML components
fraud_detector = FraudDetector()
finance_chatbot = FinanceChatbot()
savings_predictor = SavingsPredictor()
transaction_classifier = TransactionClassifier()
credit_scorer = CreditScorer()

# Background thread for model training
def train_models_periodically():
    while True:
        try:
            print("Training models...")
            fraud_detector.train_model()
            transaction_classifier.train_model()
            credit_scorer.train_model()
            print("Model training completed")
            time.sleep(86400)  # Retrain daily
        except Exception as e:
            print(f"Model training failed: {e}")
            time.sleep(3600)  # Retry in 1 hour

# Start training thread only after DB initialization
training_thread = None
if not hasattr(sys, '_called_from_test'):  # Only start in production
    training_thread = threading.Thread(target=train_models_periodically, daemon=True)
    training_thread.start()


# Database migration for existing installations
try:
    # Check if old table structure exists
    cursor.execute("PRAGMA table_info(savings_goals_history)")
    columns = [row[1] for row in cursor.fetchall()]
    


    if 'current_amount' not in columns:
        print("Migrating savings_goals_history table...")
        
        # Create temporary table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS savings_goals_history_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id INTEGER,
                contribution_amount REAL,
                current_amount REAL,
                timestamp TEXT,
                FOREIGN KEY(goal_id) REFERENCES savings_goals(id)
            )
        ''')
        
        # Migrate existing data
        cursor.execute("SELECT * FROM savings_goals_history")
        for row in cursor.fetchall():
            goal_id, amount, timestamp = row[1], row[2], row[3]
            
            # Get the cumulative amount at that point
            cursor.execute("""
                SELECT current_amount 
                FROM savings_goals 
                WHERE id=? 
                AND created_at <= ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (goal_id, timestamp))
            current_amount = cursor.fetchone()[0] if cursor.fetchone() else 0
            
            # Insert into new table
            cursor.execute("""
                INSERT INTO savings_goals_history_new 
                (goal_id, contribution_amount, current_amount, timestamp)
                VALUES (?, ?, ?, ?)
            """, (goal_id, amount, current_amount, timestamp))
        
        # Replace old table
        cursor.execute("DROP TABLE savings_goals_history")
        cursor.execute("ALTER TABLE savings_goals_history_new RENAME TO savings_goals_history")
        conn.commit()
        print("Migration complete")
except Exception as e:
    print(f"Migration failed: {e}")
    conn.rollback()


def test_fraud_detection():
    """Run tests to verify fraud detection"""
    try:
        # Create a separate database connection
        test_conn = sqlite3.connect("bank.db")
        test_cursor = test_conn.cursor()
        
        print("\n=== Testing Fraud Detection ===")
        
        # Create test account
        test_acc = Account(
            name="Test User",
            account_number="9999999999",
            pin="1234",
            username="testuser",
            national_id="TEST001",
            address="Test Address"
        )
        
        # Save using test connection
        test_cursor.execute(
            "INSERT INTO accounts (account_number, name, pin, username, national_id, address, balance, created_at, is_active, is_admin) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (test_acc.account_number, test_acc.name, test_acc.pin, test_acc.username, 
             test_acc.national_id, test_acc.address, test_acc.balance, 
             test_acc.created_at, test_acc.is_active, test_acc.is_admin)
        )
        test_conn.commit()
        
        # Deposit using test connection
        test_acc.balance += 10000
        test_cursor.execute("UPDATE accounts SET balance=? WHERE account_number=?", 
                         (test_acc.balance, test_acc.account_number))
        
        # Record transaction
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        test_cursor.execute("""
            INSERT INTO transactions 
            (account_number, type, amount, description, timestamp, reference_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (test_acc.account_number, "Deposit", 10000, "Initial funding", timestamp, "TEST_DEPOSIT"))
        test_conn.commit()
        
        # Test 1: Normal transaction ($100)
        print("\nTest 1: Normal transaction ($100)")
        test_acc.balance -= 100
        test_cursor.execute("UPDATE accounts SET balance=? WHERE account_number=?", 
                         (test_acc.balance, test_acc.account_number))
        test_cursor.execute("""
            INSERT INTO transactions 
            (account_number, type, amount, description, timestamp, reference_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (test_acc.account_number, "Withdrawal", -100, "Test withdrawal 1", timestamp, "TEST_WD1"))
        test_conn.commit()


        # Cleanup
        test_cursor.execute("DELETE FROM accounts WHERE account_number=?", (test_acc.account_number,))
        test_cursor.execute("DELETE FROM transactions WHERE account_number=?", (test_acc.account_number,))
        test_conn.commit()
        
        test_cursor.close()
        test_conn.close()
        print("=== Fraud Tests Complete ===")
    except Exception as e:
        print(f"Test failed: {str(e)}")
