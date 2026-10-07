# ⚡ Smart Electricity Bill Analyzer (VoltWise)

> A full-stack web application designed to help households track, predict, understand, and reduce electricity costs with exact slab calculations, appliance power estimation, OCR bill parsing, statistical machine learning forecasting, and downloadable PDF reports.

---

## 🌟 Key Features

1. **Accurate Slab-Wise Bill Engine**:
   - Calculates energy charge line-by-line according to configurable slab tiers (e.g. MSEDCL LT-I Residential: 0-100 @ ₹5, 101-300 @ ₹10, 301+ @ ₹14).
   - Fixed charges, electricity duty percentage, and rebate deductions.
   - Saves immutable tariff snapshots with each bill record.

2. **OCR & Document Extraction (PDF / Image)**:
   - Supports text PDFs (`pdfplumber`) and scanned bills / image formats (`pytesseract` + Pillow).
   - Extracts billing period, meter readings, units consumed, and total amounts.
   - **Interactive Verification Review**: All OCR extractions are displayed in a verification modal for user review and manual edits prior to saving.

3. **Interactive Graphical Dashboard (`Chart.js`)**:
   - **KPI Cards**: Latest units, bill amount, MoM % change, avg cost/kWh, and next-month predicted bill.
   - **Trend Line Chart**: Monthly kWh progression and ₹ expenditure.
   - **Comparison Bar Chart**: Month-over-month costs.
   - **Appliance Share Doughnut Chart**: Highlighting high-load power consumers.
   - **Bill Composition Stacked Bar**: Energy vs Fixed vs Duty taxes.

4. **Machine Learning & Statistical Forecasting**:
   - 3-Month Moving Average for 3–5 billing records.
   - Ordinary Least Squares (OLS) Linear Regression for 6+ billing records with $\pm 8-12\%$ confidence intervals.
   - Forecasted units are passed through the slab calculator for slab-accurate predicted ₹ amounts.

5. **Appliance-Wise Cost Estimator**:
   - Formula: $\text{Monthly kWh} = \frac{\text{Watts} \times \text{Hours/Day} \times \text{Days/Month} \times \text{Qty}}{1000}$.
   - Preset catalog of common household appliances (Inverter AC, Refrigerator, Geysers, BLDC Fans, LEDs, Washing Machine, Smart TV).
   - Flags appliances accounting for $\ge 25\%$ of household load.

6. **Actionable Energy Saving Tips**:
   - Rule-based personalization tailored to top appliances, slab jump proximity (e.g., within 15 units of higher tier), and MoM consumption spikes.
   - Shows estimated monthly ₹ savings per action.

7. **Publication-Quality PDF Reports**:
   - Downloadable PDF report (`ReportLab`) with embedded historical consumption trend charts (`Matplotlib`), slab breakdown table, appliance ranking, and saving recommendations.

8. **In-App Notification Alerts**:
   - High usage threshold alerts.
   - Budget overrun notifications.
   - Consumption surge warnings.

---

## 🏗️ Technical Architecture

- **Backend**: Python 3.10+, Flask, Flask-CORS, Flask-JWT-Extended
- **Database**: MongoDB (Local or Atlas via PyMongo) with MongoMock standalone engine
- **Frontend**: Responsive HTML5, Vanilla CSS Glassmorphism Design System, Vanilla JS (ES6+ Modules), Chart.js
- **PDF Engine**: ReportLab + Matplotlib
- **Document OCR**: pdfplumber, pytesseract, Pillow

---

## 🚀 Quick Start Guide

### 1. Install Dependencies
```bash
py -m pip install -r backend/requirements.txt
```

### 2. Start the Server
```bash
py backend/app.py
```
Open your browser and navigate to:
👉 **`http://127.0.0.1:5000`**

---

## 🔑 Demo Account Credentials

A pre-populated demo account with **6 months of realistic billing history**, tracked appliances, and alerts is seeded automatically:

- **Email**: `demo@voltwise.com`
- **Password**: `password123`

*(You can also register a new account anytime from the registration page)*

---

## 🧪 Running Automated Tests

Run the full pytest suite (11 test cases covering slab calculation boundaries, prediction fallbacks, and full API integration flows):

```bash
py -m pytest backend/tests/ -v
```

---

## 📡 REST API Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register` | Register new user account |
| `POST` | `/api/v1/auth/login` | Log in and receive JWT token |
| `GET` | `/api/v1/auth/me` | Retrieve profile and alert settings |
| `PUT` | `/api/v1/auth/me` | Update thresholds and budget settings |
| `POST` | `/api/v1/bills/calculate` | Stateless "what-if" bill calculator |
| `POST` | `/api/v1/bills/upload` | Upload PDF/image bill for OCR parsing |
| `GET` | `/api/v1/bills` | List historical bills with filters |
| `POST` | `/api/v1/bills` | Save new bill and trigger alert checks |
| `GET` | `/api/v1/bills/<id>` | Fetch detailed bill breakdown |
| `PUT` | `/api/v1/bills/<id>` | Update bill and recalculate |
| `DELETE` | `/api/v1/bills/<id>` | Delete bill record |
| `GET` | `/api/v1/analytics/summary` | Summary KPIs and MoM metrics |
| `GET` | `/api/v1/analytics/charts` | Dataset endpoints for Chart.js |
| `GET` | `/api/v1/predict` | Next billing cycle consumption forecast |
| `GET` | `/api/v1/appliances` | List tracked appliances and summary |
| `POST` | `/api/v1/appliances` | Add appliance to inventory |
| `GET` | `/api/v1/tips` | Generate personalized energy saving tips |
| `GET` | `/api/v1/alerts` | List in-app alerts and notifications |
| `GET` | `/api/v1/reports/pdf` | Download detailed monthly PDF analysis report |
