# 💸 WireBuddy Transaction App

WireBuddy is a modern **banking and financial management web application** built with **Streamlit** and **SQLite**.  
It enables users to **send money, manage savings goals, track transactions, convert currencies, and receive financial advice** — all in one simple, secure interface.

---

## ✨ Features

### 👤 **User Features**
- 🔑 **Secure Authentication**
  - Login & registration with **username, phone number (as account number), and PIN**.
  - Session-based login to keep users authenticated securely.
- 💰 **Transactions**
  - Deposit, withdraw, and send money to other registered accounts.
  - PIN authentication before any transaction.
  - Receipts for each transaction with **downloadable/printable format**.
- 📜 **Transaction History**
  - Filterable and date-sorted transaction list.
  - Displays sender, receiver, amount, date/time, and reference ID.
- 🎯 **Savings Goals / Budgeting Tools**
  - Set financial targets and track progress visually.
- 🌍 **Currency Converter**
  - Live exchange rates for instant currency conversions.
- 📚 **Financial Literacy Assistant**
  - AI-powered chatbot offering financial tips and budgeting advice.

---

### 🛠 **Admin Features**
- 🗂 **Account Management**
  - View all accounts and balances.
  - Freeze/unfreeze accounts.
  - Reset PINs for users.
- 📊 **Activity Monitoring**
  - View recent transactions and user activities.

---

## 🗂 Project Structure

📦 wirebuddy
┣ 📜 app.py # Main Streamlit app
┣ 📜 database.py # SQLite database handling
┣ 📜 auth.py # Authentication & session management
┣ 📜 transactions.py # Deposit, withdraw, send money logic
┣ 📜 savings.py # Savings goals management
┣ 📜 currency.py # Currency conversion functions
┣ 📜 chatbot.py # Financial literacy assistant logic
┣ 📂 templates # HTML templates for receipts
┗ 📂 static # CSS & assets

yaml
Copy
Edit

---

## ⚙️ Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/wirebuddy.git
cd wirebuddy

# Create a virtual environment
python -m venv venv
source venv/bin/activate   # On Mac/Linux
venv\Scripts\activate      # On Windows

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
🖼 Screenshots
Login Page	Dashboard	Transaction History

📜 Usage
Register an Account

Full name

National ID

Phone number (serves as account number)

Address

Username & 4-digit PIN

Login using your account number and PIN.

Perform Transactions

Deposit, withdraw, send money.

Confirm with your PIN before processing.

Track Your Finances

View transaction history.

Set and monitor savings goals.

Convert currencies in real-time.

Get Advice from the financial literacy assistant.

🧠 Machine Learning Integration
WireBuddy includes a Machine Learning-based Anomaly Detection System to detect suspicious transactions.
The model:

Is trained on historical transaction data.

Flags unusual spending patterns.

Helps prevent fraud in real time.

🤝 Contributing
Pull requests are welcome! For major changes:

Fork the repo

Create a new branch

Make your changes

Submit a PR

📄 License
This project is licensed under the MIT License.

📬 Contact
Author: Prince Amoako Atta
Email: your.email@example.com
GitHub: yourusername
