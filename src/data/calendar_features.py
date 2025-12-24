#!/usr/bin/env python3
"""
Calendar and location-based feature generation for demand forecasting.
Includes holidays, weekends, and school proximity data.
"""

import pandas as pd
import logging
from datetime import datetime
from typing import Dict, List, Optional
import requests
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

logger = logging.getLogger(__name__)


# LA-specific holidays (in addition to federal holidays)
LA_HOLIDAYS = {
    # Add major LA-specific events/holidays
    "2022-01-01": "New Year's Day",
    "2023-01-01": "New Year's Day",
    "2024-01-01": "New Year's Day",
    "2025-01-01": "New Year's Day",
}


def get_us_federal_holidays(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Get US federal holidays between start_date and end_date using the holidays library.

    Args:
        start_date: Start date in 'YYYY-MM-DD' format
        end_date: End date in 'YYYY-MM-DD' format

    Returns:
        DataFrame with columns: date, holiday_name, is_holiday
    """
    try:
        import holidays
    except ImportError:
        logger.error("holidays library not installed. Run: pip install holidays")
        raise

    # Get US federal holidays
    us_holidays = holidays.US(years=range(
        pd.to_datetime(start_date).year,
        pd.to_datetime(end_date).year + 1
    ))

    # Create date range
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')

    # Create DataFrame
    holiday_data = []
    for date in date_range:
        date_str = date.strftime('%Y-%m-%d')
        if date in us_holidays:
            holiday_data.append({
                'date': date,
                'holiday_name': us_holidays[date],
                'is_holiday': 1
            })
        elif date_str in LA_HOLIDAYS:
            holiday_data.append({
                'date': date,
                'holiday_name': LA_HOLIDAYS[date_str],
                'is_holiday': 1
            })
        else:
            holiday_data.append({
                'date': date,
                'holiday_name': None,
                'is_holiday': 0
            })

    return pd.DataFrame(holiday_data)


def add_weekend_indicator(df: pd.DataFrame, date_col: str = 'date') -> pd.DataFrame:
    """
    Add weekend indicator (1 for Sat/Sun, 0 for weekdays).

    Args:
        df: DataFrame with date column
        date_col: Name of date column

    Returns:
        DataFrame with is_weekend column added
    """
    df = df.copy()
    df['is_weekend'] = df[date_col].dt.dayofweek.isin([5, 6]).astype(int)
    return df


def geocode_zipcode(zipcode: str) -> Optional[tuple]:
    """
    Convert ZIP code to (latitude, longitude) using Nominatim.

    Args:
        zipcode: US ZIP code

    Returns:
        Tuple of (latitude, longitude) or None if geocoding fails
    """
    try:
        geolocator = Nominatim(user_agent="yeems_coffee_forecasting")
        location = geolocator.geocode(f"{zipcode}, USA")
        if location:
            return (location.latitude, location.longitude)
        return None
    except Exception as e:
        logger.error(f"Error geocoding {zipcode}: {e}")
        return None


def get_schools_near_location(
    zipcode: str,
    radius_miles: float = 10.0
) -> List[Dict]:
    """
    Get colleges and universities within radius of a ZIP code using Overpass API.
    Note: Excludes K-12 schools, only includes colleges and universities.

    Args:
        zipcode: US ZIP code
        radius_miles: Search radius in miles

    Returns:
        List of dictionaries with college/university information
    """
    # Geocode the ZIP code
    coords = geocode_zipcode(zipcode)
    if not coords:
        logger.error(f"Could not geocode ZIP code: {zipcode}")
        return []

    lat, lon = coords
    radius_meters = radius_miles * 1609.34  # Convert miles to meters

    # Overpass API query for ONLY colleges and universities (excludes K-12 schools)
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json];
    (
      node["amenity"="university"](around:{radius_meters},{lat},{lon});
      way["amenity"="university"](around:{radius_meters},{lat},{lon});
      node["amenity"="college"](around:{radius_meters},{lat},{lon});
      way["amenity"="college"](around:{radius_meters},{lat},{lon});
    );
    out center;
    """

    try:
        # Try up to 3 times with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    overpass_url,
                    data={'data': overpass_query},
                    timeout=60  # Increased timeout to 60 seconds
                )
                response.raise_for_status()
                data = response.json()
                break  # Success, exit retry loop
            except (requests.exceptions.Timeout, requests.exceptions.HTTPError) as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                    import time
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} attempts failed for ZIP {zipcode}")
                    raise

        schools = []
        for element in data.get('elements', []):
            # Get coordinates
            if element['type'] == 'node':
                school_lat = element['lat']
                school_lon = element['lon']
            elif 'center' in element:
                school_lat = element['center']['lat']
                school_lon = element['center']['lon']
            else:
                continue

            # Calculate distance
            distance_miles = geodesic((lat, lon), (school_lat, school_lon)).miles

            school_info = {
                'name': element.get('tags', {}).get('name', 'Unknown'),
                'type': element.get('tags', {}).get('amenity', 'school'),
                'latitude': school_lat,
                'longitude': school_lon,
                'distance_miles': round(distance_miles, 2)
            }
            schools.append(school_info)

        # Sort by distance
        schools.sort(key=lambda x: x['distance_miles'])

        logger.info(f"Found {len(schools)} colleges/universities within {radius_miles} miles of ZIP {zipcode}")
        return schools

    except Exception as e:
        logger.error(f"Error querying Overpass API: {e}")
        return []


def create_school_proximity_features(
    postal_codes: Dict[str, str],
    radius_miles: float = 10.0
) -> pd.DataFrame:
    """
    Create college/university proximity features for each location.
    Note: Only includes colleges and universities, not K-12 schools.

    Args:
        postal_codes: Dict mapping location_name -> postal_code
        radius_miles: Search radius in miles

    Returns:
        DataFrame with location, postal_code, college_count, nearest_college_distance, etc.
    """
    location_features = []

    for location_name, zipcode in postal_codes.items():
        try:
            logger.info(f"Finding colleges/universities near {location_name} (ZIP: {zipcode})...")
            schools = get_schools_near_location(zipcode, radius_miles)

            feature = {
                'location': location_name,
                'postal_code': zipcode,
                'college_count': len(schools),  # Total colleges/universities
                'nearest_college_distance': schools[0]['distance_miles'] if schools else None,
                'universities_count': sum(1 for s in schools if s['type'] == 'university'),
                'colleges_within_5mi': sum(1 for s in schools if s['distance_miles'] <= 5.0)
            }
            location_features.append(feature)

            # Log top 5 nearest colleges/universities
            for i, school in enumerate(schools[:5], 1):
                logger.info(f"  {i}. {school['name']} ({school['type']}) - {school['distance_miles']} mi")

        except Exception as e:
            logger.error(f"Failed to get school data for {location_name}: {e}")
            # Add feature with null values if API call fails
            feature = {
                'location': location_name,
                'postal_code': zipcode,
                'college_count': 0,
                'nearest_college_distance': None,
                'universities_count': 0,
                'colleges_within_5mi': 0
            }
            location_features.append(feature)

    return pd.DataFrame(location_features)


def generate_all_calendar_features(
    start_date: str,
    end_date: str,
    postal_codes: Optional[Dict[str, str]] = None,
    school_radius_miles: float = 10.0
) -> Dict[str, pd.DataFrame]:
    """
    Generate all calendar and location-based features.

    Args:
        start_date: Start date in 'YYYY-MM-DD' format
        end_date: End date in 'YYYY-MM-DD' format
        postal_codes: Optional dict mapping location_name -> postal_code for school proximity
        school_radius_miles: Radius for school search

    Returns:
        Dictionary with DataFrames for different feature types
    """
    logger.info(f"Generating calendar features from {start_date} to {end_date}")

    # Generate holiday features
    holidays_df = get_us_federal_holidays(start_date, end_date)
    holidays_df = add_weekend_indicator(holidays_df)

    result = {
        'holidays': holidays_df
    }

    # Generate school proximity features if postal codes provided
    if postal_codes:
        schools_df = create_school_proximity_features(postal_codes, school_radius_miles)
        result['schools'] = schools_df

    return result


if __name__ == '__main__':
    # Example usage
    logging.basicConfig(level=logging.INFO)

    # Test with Yeems Coffee locations
    postal_codes = {
        'Location 1': '90020',  # Ktown
        'Location 2': '90249'   # Gardena
    }

    # Generate features
    features = generate_all_calendar_features(
        start_date='2022-07-01',
        end_date='2025-12-31',
        postal_codes=postal_codes,
        school_radius_miles=10.0
    )

    # Display results
    print("\n📅 Holiday Features Sample:")
    print(features['holidays'].head(10))
    print(f"\nTotal holidays: {features['holidays']['is_holiday'].sum()}")

    print("\n🏫 School Proximity Features:")
    print(features['schools'])
