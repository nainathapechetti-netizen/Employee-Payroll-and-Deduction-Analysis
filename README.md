# Employee-Payroll-and-Deduction-Analysis
# Employee Payroll and Deduction Analysis System

A deterministic payroll processing and payslip formatting engine built in Python. It computes employee **Gross Salary** from prorated basic pay, statutory allowances, overtime hours, and performance incentives; applies statutory and **marginal progressive tax deductions**; and renders an itemized **Salary Statement**.

---

## Key Features

- **Attendance-Prorated Earnings:** Automatically adjusts fixed salary components (`Basic`, `HRA`, `DA`, `Special Allowance`) for unpaid leave (Loss of Pay) days.
- **Overtime & Incentive Computation:** Calculates overtime pay using a configurable hourly multiplier (`1.5x` default) on contracted basic hourly rate plus variable performance incentives.
- **Statutory & Progressive Deductions:**
  - **Provident Fund (EPF):** Percentage contribution capped at a configurable wage ceiling.
  - **Professional Tax (PT):** Flat statutory deduction triggered above a gross salary threshold.
  - **Progressive Income Tax (TDS):** Marginal bracket calculation across multiple income slabs after standard and statutory deductions.
- **Formatted Payslip Generator:** Outputs a clean, dual-column salary statement with a full progressive tax slab audit trail.

---

## Payroll Calculation Formula

1. **Attendance Ratio:**
   $$\text{Ratio} = \frac{\text{Working Days} - \text{Unpaid Leave Days}}{\text{Working Days}}$$
2. **Gross Salary:**
   $$\text{Gross Salary} = \text{Earned Basic} + \text{HRA} + \text{DA} + \text{Earned Special Allowance} + \text{Overtime Pay} + \text{Incentives}$$
   where:
   $$\text{Overtime Pay} = \text{Overtime Hours} \times \left(\frac{\text{Contracted Basic}}{\text{Standard Monthly Hours}}\right) \times \text{Multiplier}$$
3. **Monthly Taxable Income:**
   $$\text{Taxable Income} = \max(0,\ \text{Gross Salary} - \text{EPF} - \text{Professional Tax} - \text{Monthly Standard Deduction})$$
4. **Progressive Income Tax:**
   Applied marginally across configured tax brackets (default: `0%` up to `25,000`, `5%` for `25,001–50,000`, `15%` for `50,001–100,000`, and `25%` above `100,000`).
5. **Net Salary Payable:**
   $$\text{Net Salary} = \max(0,\ \text{Gross Salary} - (\text{EPF} + \text{PT} + \text{Income Tax} + \text{Loan EMI}))$$

---

## Project Structure

```text
├── payroll_system.py   # Payroll policy config, calculation engine, progressive tax logic & payslip formatter
└── README.md           # System documentation
