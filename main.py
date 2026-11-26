from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class TaxSlab:
    """Represents a marginal progressive income tax bracket on monthly taxable income."""
    upper_limit: Optional[float]  # None indicates infinity (highest tax bracket)
    rate_pct: float


@dataclass(frozen=True)
class PayrollPolicy:
    """Defines allowance rules, overtime multipliers, statutory rates, and progressive tax slabs."""
    hra_pct_of_basic: float = 40.0
    da_pct_of_basic: float = 10.0
    standard_monthly_hours: float = 160.0
    overtime_multiplier: float = 1.5

    # Statutory deductions
    pf_pct_of_basic: float = 12.0
    pf_wage_ceiling: float = 15_000.0
    professional_tax_threshold: float = 15_000.0
    professional_tax_amount: float = 200.0
    standard_deduction_monthly: float = 4_166.67  # e.g., 50,000 annual standard deduction

    # Progressive marginal tax slabs (applied to monthly taxable income)
    tax_slabs: List[TaxSlab] = field(
        default_factory=lambda: [
            TaxSlab(upper_limit=25_000.0, rate_pct=0.0),
            TaxSlab(upper_limit=50_000.0, rate_pct=5.0),
            TaxSlab(upper_limit=100_000.0, rate_pct=15.0),
            TaxSlab(upper_limit=None, rate_pct=25.0),
        ]
    )


@dataclass
class EmployeePayrollInput:
    """Monthly attendance, pay components, and incentive inputs for one employee."""
    emp_id: str
    name: str
    department: str
    designation: str
    pay_period: str                 # e.g., "November 2026"
    basic_pay: float
    special_allowance: float = 0.0
    overtime_hours: float = 0.0
    performance_incentive: float = 0.0
    loan_emi_deduction: float = 0.0
    unpaid_leave_days: float = 0.0
    working_days_in_month: int = 22


@dataclass
class TaxBracketBreakdown:
    """Line-item tax computed within a single progressive income slab."""
    bracket_label: str
    taxable_amount: float
    rate_pct: float
    tax_amount: float


@dataclass
class SalaryStatement:
    """Complete itemized payslip with earnings, progressive deductions, and net pay."""
    emp_id: str
    name: str
    department: str
    designation: str
    pay_period: str

    # Earnings
    earned_basic: float
    hra: float
    da: float
    special_allowance: float
    overtime_pay: float
    performance_incentive: float
    gross_salary: float

    # Deductions
    provident_fund: float
    professional_tax: float
    taxable_income: float
    tax_breakdown: List[TaxBracketBreakdown]
    income_tax: float
    loan_emi: float
    total_deductions: float

    # Net Pay
    net_salary: float


class PayrollProcessor:
    """Processes employee earnings, applies progressive deductions, and formats payslips."""

    def __init__(self, policy: Optional[PayrollPolicy] = None):
        base_policy = policy or PayrollPolicy()
        sorted_slabs = sorted(
            base_policy.tax_slabs,
            key=lambda s: float("inf") if s.upper_limit is None else s.upper_limit,
        )
        self.policy = PayrollPolicy(
            hra_pct_of_basic=base_policy.hra_pct_of_basic,
            da_pct_of_basic=base_policy.da_pct_of_basic,
            standard_monthly_hours=base_policy.standard_monthly_hours,
            overtime_multiplier=base_policy.overtime_multiplier,
            pf_pct_of_basic=base_policy.pf_pct_of_basic,
            pf_wage_ceiling=base_policy.pf_wage_ceiling,
            professional_tax_threshold=base_policy.professional_tax_threshold,
            professional_tax_amount=base_policy.professional_tax_amount,
            standard_deduction_monthly=base_policy.standard_deduction_monthly,
            tax_slabs=sorted_slabs,
        )

    def _validate_input(self, emp: EmployeePayrollInput) -> None:
        if emp.basic_pay < 0 or emp.special_allowance < 0 or emp.performance_incentive < 0:
            raise ValueError(f"Pay components cannot be negative ({emp.emp_id}).")
        if emp.overtime_hours < 0 or emp.loan_emi_deduction < 0:
            raise ValueError(f"Overtime hours and loan EMI cannot be negative ({emp.emp_id}).")
        if not (0 <= emp.unpaid_leave_days <= emp.working_days_in_month):
            raise ValueError(f"Invalid unpaid leave days for {emp.emp_id}.")
        if emp.working_days_in_month <= 0:
            raise ValueError("working_days_in_month must be positive.")

    def _compute_progressive_tax(self, taxable_income: float) -> Tuple[float, List[TaxBracketBreakdown]]:
        """Calculates marginal income tax across progressive tax slabs."""
        if taxable_income <= 0:
            return 0.0, []

        remaining = taxable_income
        prev_limit = 0.0
        total_tax = 0.0
        breakdown: List[TaxBracketBreakdown] = []

        for slab in self.policy.tax_slabs:
            if remaining <= 0:
                break

            if slab.upper_limit is None:
                slab_income = remaining
                label = f">{prev_limit:,.0f}"
            else:
                band_width = slab.upper_limit - prev_limit
                if band_width <= 0:
                    raise ValueError("Tax slab upper limits must be strictly increasing.")
                slab_income = min(remaining, band_width)
                label = f"{prev_limit + 1:,.0f} - {slab.upper_limit:,.0f}"
                prev_limit = slab.upper_limit

            slab_tax = slab_income * (slab.rate_pct / 100.0)
            total_tax += slab_tax
            remaining -= slab_income

            breakdown.append(
                TaxBracketBreakdown(
                    bracket_label=label,
                    taxable_amount=round(slab_income, 2),
                    rate_pct=slab.rate_pct,
                    tax_amount=round(slab_tax, 2),
                )
            )

        return round(total_tax, 2), breakdown

    def process_employee(self, emp: EmployeePayrollInput) -> SalaryStatement:
        """Executes full payroll calculation for an employee."""
        self._validate_input(emp)

        # Prorate fixed pay components for Loss of Pay (LOP) leave days
        attendance_ratio = (
            (emp.working_days_in_month - emp.unpaid_leave_days) / emp.working_days_in_month
        )
        earned_basic = emp.basic_pay * attendance_ratio
        hra = earned_basic * (self.policy.hra_pct_of_basic / 100.0)
        da = earned_basic * (self.policy.da_pct_of_basic / 100.0)
        earned_special = emp.special_allowance * attendance_ratio

        # Overtime calculated on contracted hourly basic rate
        hourly_rate = emp.basic_pay / self.policy.standard_monthly_hours
        overtime_pay = emp.overtime_hours * hourly_rate * self.policy.overtime_multiplier

        gross_salary = (
            earned_basic
            + hra
            + da
            + earned_special
            + overtime_pay
            + emp.performance_incentive
        )

        # Statutory deductions
        pf_applicable_wage = min(earned_basic, self.policy.pf_wage_ceiling)
        provident_fund = pf_applicable_wage * (self.policy.pf_pct_of_basic / 100.0)

        professional_tax = (
            self.policy.professional_tax_amount
            if gross_salary >= self.policy.professional_tax_threshold
            else 0.0
        )

        # Progressive Income Tax (TDS)
        taxable_income = max(
            0.0,
            gross_salary - provident_fund - professional_tax - self.policy.standard_deduction_monthly,
        )
        income_tax, tax_breakdown = self._compute_progressive_tax(taxable_income)

        total_deductions = provident_fund + professional_tax + income_tax + emp.loan_emi_deduction
        net_salary = max(0.0, gross_salary - total_deductions)

        return SalaryStatement(
            emp_id=emp.emp_id,
            name=emp.name,
            department=emp.department,
            designation=emp.designation,
            pay_period=emp.pay_period,
            earned_basic=round(earned_basic, 2),
            hra=round(hra, 2),
            da=round(da, 2),
            special_allowance=round(earned_special, 2),
            overtime_pay=round(overtime_pay, 2),
            performance_incentive=round(emp.performance_incentive, 2),
            gross_salary=round(gross_salary, 2),
            provident_fund=round(provident_fund, 2),
            professional_tax=round(professional_tax, 2),
            taxable_income=round(taxable_income, 2),
            tax_breakdown=tax_breakdown,
            income_tax=round(income_tax, 2),
            loan_emi=round(emp.loan_emi_deduction, 2),
            total_deductions=round(total_deductions, 2),
            net_salary=round(net_salary, 2),
        )

    @staticmethod
    def format_salary_statement(stmt: SalaryStatement, currency: str = "INR") -> str:
        """Formats a structured, side-by-side salary statement string."""
        width = 78
        border = "=" * width
        divider = "-" * width

        earnings: List[Tuple[str, float]] = [
            ("Basic Pay (Earned)", stmt.earned_basic),
            ("House Rent Allowance (HRA)", stmt.hra),
            ("Dearness Allowance (DA)", stmt.da),
            ("Special Allowance", stmt.special_allowance),
            ("Overtime Pay", stmt.overtime_pay),
            ("Performance Incentive", stmt.performance_incentive),
        ]

        deductions: List[Tuple[str, float]] = [
            ("Provident Fund (EPF)", stmt.provident_fund),
            ("Professional Tax (PT)", stmt.professional_tax),
            ("Income Tax (TDS)", stmt.income_tax),
            ("Salary Advance / Loan EMI", stmt.loan_emi),
        ]

        lines = [
            border,
            f"{'SALARY STATEMENT / PAYSLIP':^{width}}",
            f"{'Pay Period: ' + stmt.pay_period:^{width}}",
            border,
            f"Employee ID : {stmt.emp_id:<22} Department  : {stmt.department}",
            f"Name        : {stmt.name:<22} Designation : {stmt.designation}",
            divider,
            f"{'EARNINGS':<27} {'AMOUNT':>10} | {'DEDUCTIONS':<27} {'AMOUNT':>10}",
            divider,
        ]

        max_rows = max(len(earnings), len(deductions))
        for i in range(max_rows):
            e_label, e_val = earnings[i] if i < len(earnings) else ("", None)
            d_label, d_val = deductions[i] if i < len(deductions) else ("", None)

            left = f"{e_label:<27} {e_val:>10,.2f}" if e_val is not None else " " * 38
            right = f"{d_label:<27} {d_val:>10,.2f}" if d_val is not None else " " * 38
            lines.append(f"{left} | {right}")

        lines.extend(
            [
                divider,
                f"{'GROSS SALARY':<27} {stmt.gross_salary:>10,.2f} | {'TOTAL DEDUCTIONS':<27} {stmt.total_deductions:>10,.2f}",
                border,
                f"NET SALARY PAYABLE ({currency}): {stmt.net_salary:,.2f}",
                border,
                f"Progressive Tax Breakdown (Monthly Taxable Income: {stmt.taxable_income:,.2f}):",
            ]
        )

        for tb in stmt.tax_breakdown:
            lines.append(
                f"  Slab {tb.bracket_label:<18} | Taxable: {tb.taxable_amount:>9,.2f} "
                f"@ {tb.rate_pct:>4.1f}% = {tb.tax_amount:>8,.2f}"
            )

        lines.append(border)
        return "\n".join(lines)


# --- Example Execution ---
if __name__ == "__main__":
    processor = PayrollProcessor()

    employees = [
        EmployeePayrollInput(
            emp_id="EMP-2041",
            name="Siddharth Nair",
            department="Platform Engineering",
            designation="Senior Backend Engineer",
            pay_period="November 2026",
            basic_pay=60_000.0,
            special_allowance=18_000.0,
            overtime_hours=10.0,
            performance_incentive=12_000.0,
            loan_emi_deduction=3_500.0,
            unpaid_leave_days=0.0,
        ),
        EmployeePayrollInput(
            emp_id="EMP-2089",
            name="Nandini Krishnan",
            department="Product Operations",
            designation="Operations Analyst",
            pay_period="November 2026",
            basic_pay=28_000.0,
            special_allowance=6_000.0,
            overtime_hours=6.0,
            performance_incentive=3_000.0,
            unpaid_leave_days=1.0,
        ),
    ]

    for emp in employees:
        statement = processor.process_employee(emp)
        print(processor.format_salary_statement(statement))
        print()
