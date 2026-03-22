"""
Budget Calculator - Computes free-to-spend and spending breakdown
"""
import json
from datetime import datetime
from typing import Dict, Optional

import database


def get_current_month() -> str:
    return datetime.now().strftime("%Y-%m")


def get_budget_status(month: Optional[str] = None) -> Dict:
    """
    Calculate current budget status for the given month.

    Returns:
        {
            month, income, fixed_bills, total_fixed,
            spending_by_category, total_variable, free_to_spend
        }
    """
    if not month:
        month = get_current_month()

    # Configured monthly income
    income_config = database.get_config("monthly_income")
    configured_income = float(income_config) if income_config else 4800.0

    # Use the higher of configured income or actual deposits this month
    actual_income = database.get_income(month)
    income = actual_income if actual_income > 0 else configured_income

    # Fixed bills from config
    fixed_bills_json = database.get_config("fixed_bills")
    fixed_bills: Dict[str, float] = json.loads(fixed_bills_json) if fixed_bills_json else {}
    total_fixed = sum(fixed_bills.values())

    # Variable spending this month by category
    spending_by_category = database.get_spending_by_category(month)
    total_variable = sum(spending_by_category.values())

    free_to_spend = income - total_fixed - total_variable

    return {
        "month": month,
        "income": round(income, 2),
        "fixed_bills": fixed_bills,
        "total_fixed": round(total_fixed, 2),
        "spending_by_category": spending_by_category,
        "total_variable": round(total_variable, 2),
        "free_to_spend": round(free_to_spend, 2),
    }


def format_balance_message(status: Dict) -> str:
    """Format the budget status as a WhatsApp-friendly message."""
    month_label = datetime.strptime(status["month"], "%Y-%m").strftime("%B %Y")
    ftsp = status["free_to_spend"]
    if ftsp > 200:
        emoji = "✅"
    elif ftsp > 0:
        emoji = "⚠️"
    else:
        emoji = "🚨"

    lines = [
        f"*Budget Status - {month_label}*",
        "",
        f"💰 Income: ${status['income']:,.2f}",
        f"🏠 Fixed Bills: ${status['total_fixed']:,.2f}",
        f"🛍 Variable Spending: ${status['total_variable']:,.2f}",
        "",
        f"{emoji} *Free to Spend: ${ftsp:,.2f}*",
    ]
    return "\n".join(lines)


def format_spending_breakdown(status: Dict) -> str:
    """Format spending breakdown by category for WhatsApp."""
    month_label = datetime.strptime(status["month"], "%Y-%m").strftime("%B %Y")
    lines = [f"*Spending Breakdown - {month_label}*", ""]

    if not status["spending_by_category"]:
        lines.append("No variable spending recorded this month.")
    else:
        for category, amount in status["spending_by_category"].items():
            lines.append(f"• {category}: ${amount:,.2f}")
        lines.append("")
        lines.append(f"*Total: ${status['total_variable']:,.2f}*")

    return "\n".join(lines)
