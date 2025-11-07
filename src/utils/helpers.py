"""
Helper functions for the application.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Union, List


def validate_dataframe(df: pd.DataFrame, required_columns: List[str]) -> bool:
    """
    Validate that a DataFrame has required columns.

    Args:
        df: DataFrame to validate
        required_columns: List of required column names

    Returns:
        True if valid, raises ValueError if not
    """
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    return True


def date_to_season(date: Union[datetime, pd.Timestamp]) -> str:
    """
    Convert a date to its corresponding season.

    Args:
        date: Date to convert

    Returns:
        Season name (Winter, Spring, Summer, Fall)
    """
    month = date.month

    if month in [12, 1, 2]:
        return 'Winter'
    elif month in [3, 4, 5]:
        return 'Spring'
    elif month in [6, 7, 8]:
        return 'Summer'
    else:
        return 'Fall'


def calculate_growth_rate(current: float, previous: float) -> float:
    """
    Calculate percentage growth rate.

    Args:
        current: Current value
        previous: Previous value

    Returns:
        Growth rate as percentage
    """
    if previous == 0:
        return 0.0

    return ((current - previous) / previous) * 100


def format_currency(amount: float, currency: str = '$') -> str:
    """
    Format a number as currency.

    Args:
        amount: Amount to format
        currency: Currency symbol

    Returns:
        Formatted currency string
    """
    return f"{currency}{amount:,.2f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Format a number as percentage.

    Args:
        value: Value to format
        decimals: Number of decimal places

    Returns:
        Formatted percentage string
    """
    return f"{value:.{decimals}f}%"


def calculate_date_range_days(start_date: datetime, end_date: datetime) -> int:
    """
    Calculate number of days between two dates.

    Args:
        start_date: Start date
        end_date: End date

    Returns:
        Number of days
    """
    return (end_date - start_date).days


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero.

    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value if division by zero

    Returns:
        Result of division or default
    """
    if denominator == 0:
        return default

    return numerator / denominator


def round_to_significant_figures(value: float, sig_figs: int = 3) -> float:
    """
    Round a number to specified significant figures.

    Args:
        value: Value to round
        sig_figs: Number of significant figures

    Returns:
        Rounded value
    """
    if value == 0:
        return 0

    return round(value, -int(np.floor(np.log10(abs(value)))) + (sig_figs - 1))


def get_date_range_label(start_date: datetime, end_date: datetime) -> str:
    """
    Create a readable label for a date range.

    Args:
        start_date: Start date
        end_date: End date

    Returns:
        Formatted date range string
    """
    return f"{start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
