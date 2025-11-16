"""
Debug date calculation for sync script
"""
from datetime import datetime, timedelta

def test_date_logic():
    """Test the date range calculation"""

    print("=" * 70)
    print("🔍 TESTING DATE CALCULATION LOGIC")
    print("=" * 70)
    print()

    # Current date
    now = datetime.now()
    print(f"Today's date: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Test oldest_first=True with 90 days
    days_back = 90
    oldest_first = True

    if oldest_first:
        start_date = now - timedelta(days=1095)  # 3 years ago
        end_date = start_date + timedelta(days=days_back)
    else:
        end_date = now
        start_date = end_date - timedelta(days=days_back)

    print(f"🎯 With --days {days_back} --oldest:")
    print(f"   Start: {start_date.strftime('%Y-%m-%d')}")
    print(f"   End:   {end_date.strftime('%Y-%m-%d')}")
    print(f"   Range: {(end_date - start_date).days} days")
    print()

    # Calculate what months this covers
    print("📅 Expected months:")
    current = start_date
    months = set()
    while current <= end_date:
        months.add(current.strftime('%Y-%m'))
        current += timedelta(days=30)

    for month in sorted(months):
        print(f"   - {month}")
    print()

    # Test if this matches user's expectation
    print("❓ Expected results:")
    print(f"   Should pull data from: {start_date.strftime('%B %Y')} to {end_date.strftime('%B %Y')}")
    print(f"   Should be approximately 3 years ago from today")
    print()

    # Check if Oct-Nov 2025 would make sense
    oct_2025 = datetime(2025, 10, 1)
    nov_2025 = datetime(2025, 11, 30)

    print("🚨 If seeing Oct-Nov 2025 dates:")
    print(f"   Oct 2025 is {(oct_2025 - now).days} days from today")
    print(f"   Nov 2025 is {(nov_2025 - now).days} days from today")

    if oct_2025 > now:
        print(f"   ⚠️  These are FUTURE dates! This should not happen.")
    print()

    # Test what Square API would receive
    print("📡 What gets sent to Square API:")
    print(f"   start_date='{start_date.strftime('%Y-%m-%d')}'")
    print(f"   end_date='{end_date.strftime('%Y-%m-%d')}'")
    print()

if __name__ == "__main__":
    test_date_logic()
