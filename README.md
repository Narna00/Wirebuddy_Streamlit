# WireBuddy – Smart Transaction App

WireBuddy is an intelligent transaction management and payment app that integrates **Machine Learning** for anomaly detection, savings goals, financial literacy, and more. Built with a clean interface and a secure backend, it is designed for both users and administrators.

---

## Features
- **User Authentication** – Secure login and signup.
- **Transaction Management** – Deposit, withdraw, send money.
- **Transaction History** – Full details with receipts.
- **Savings Goals** – Set and track your savings targets.
- **ML Fraud Detection** – Detect suspicious transactions in real-time.
- **Admin Panel** – View accounts, freeze/unfreeze, reset PINs, view activities.

---

## Project Structure
```
assets/
LICENSE.txt
README.md
app.py
backend.py
fraud_model.pkl
requirements.txt
```

---

## Installation

```bash
# Clone the repository
[https://github.com/Narna00/Wirebuddy_Streamlit.git]
cd Wirebuddy_Streamlit

# Create virtual environment
python -m venv venv
source venv/bin/activate   # On Windows use: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Usage

```bash
# Run the application
streamlit run app.py
```

- Open browser and navigate to: `http://localhost:8501`

---

## Requirements
All dependencies are listed in `requirements.txt`.

---

## Machine Learning Model
- **fraud_model.pkl** is a trained ML model for detecting transaction anomalies.
- Trained using historical transaction data and classification algorithms.

---

## Security
- All transactions are authenticated.
- PIN-based verification before any sensitive action.
- Session-based login to prevent unauthorized access.

---

## Contact
**Developer:** Magnifiers  
**Email:** princeamoakoatta22@gmail.com  
**GitHub:** [Narna00](https://github.com/Narna00)
