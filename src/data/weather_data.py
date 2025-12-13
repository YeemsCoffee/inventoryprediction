"""
Weather data fetcher using Open-Meteo API.
Fetches historical and forecast weather data for store locations.
"""

import sys
import os
import logging
from datetime import date, timedelta

import pandas as pd
import requests
from sqlalchemy import text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils.database import RDSConnector


BASE_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
BASE_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"

# Store location ZIP codes
ZIP_CODES = {
    "Ktown": "90020",
    "Gardena": "90249",
}

# In-process cache for geocoding results to avoid repeated API calls
_GEOCODE_CACHE = {}


def zip_to_latlon(zip_code: str):
    """
    Convert US ZIP code to latitude & longitude using Open-Meteo Geocoding API.

    Uses in-process caching to avoid repeated API calls for the same ZIP code.

    Args:
        zip_code: US ZIP code to geocode

    Returns:
        Tuple of (latitude, longitude)

    Raises:
        RuntimeError: If geocoding API call fails or ZIP cannot be resolved
    """
    # Check cache first
    if zip_code in _GEOCODE_CACHE:
        logger.debug(f"Using cached coordinates for ZIP {zip_code}")
        return _GEOCODE_CACHE[zip_code]

    params = {"name": zip_code, "count": 1, "format": "json"}

    try:
        resp = requests.get(BASE_GEOCODE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(
            f"Failed to geocode ZIP code {zip_code}: {e}"
        ) from e

    if "results" not in data or len(data["results"]) == 0:
        raise RuntimeError(
            f"No geocoding results found for ZIP code: {zip_code}. "
            f"Please verify the ZIP code is valid."
        )

    result = data["results"][0]
    lat, lon = result["latitude"], result["longitude"]

    # Cache the result
    _GEOCODE_CACHE[zip_code] = (lat, lon)
    logger.debug(f"Cached coordinates for ZIP {zip_code}: ({lat}, {lon})")

    return lat, lon


def fetch_weather_for_location(name: str, zip_code: str, start: date, end: date):
    """
    Fetch historical + forecast weather for a ZIP-code-based location.

    Args:
        name: Location name (e.g., "Ktown")
        zip_code: US ZIP code
        start: Start date for weather data
        end: End date for weather data

    Returns:
        DataFrame with weather data

    Raises:
        RuntimeError: If weather API call fails
    """
    lat, lon = zip_to_latlon(zip_code)

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": "America/Los_Angeles",
    }

    try:
        resp = requests.get(BASE_FORECAST_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(
            f"Failed to fetch weather data for {name} (ZIP: {zip_code}): {e}"
        ) from e

    daily = data.get("daily", {})
    df = pd.DataFrame({
        "date": daily.get("time", []),
        "temp_max": daily.get("temperature_2m_max", []),
        "temp_min": daily.get("temperature_2m_min", []),
        "precipitation": daily.get("precipitation_sum", []),
    })

    df["date"] = pd.to_datetime(df["date"])
    df["location"] = name
    df["zip"] = zip_code

    return df


def fetch_and_save_weather(days_back=730, days_forward=14):
    """
    Fetch weather data for all store locations and save to database.

    Args:
        days_back: Number of historical days to fetch
        days_forward: Number of forecast days to fetch

    Returns:
        DataFrame with all fetched weather data

    Raises:
        RuntimeError: If fetching or saving weather data fails
    """
    db = RDSConnector()

    try:
        today = date.today()
        start = today - timedelta(days=days_back)
        end = today + timedelta(days=days_forward)

        logger.info("=" * 70)
        logger.info("🌤️  WEATHER DATA SYNC")
        logger.info("=" * 70)
        logger.info(f"Date range: {start} to {end}")

        frames = []
        for name, zip_code in ZIP_CODES.items():
            logger.info(f"📍 Fetching weather for {name} (ZIP: {zip_code})...")
            df_loc = fetch_weather_for_location(name, zip_code, start, end)
            frames.append(df_loc)
            logger.info(f"   ✅ Got {len(df_loc)} days of weather data")

        weather_df = pd.concat(frames, ignore_index=True)
        weather_df = weather_df.sort_values(["location", "date"])

        logger.info(f"📊 Total weather records: {len(weather_df)}")

        # Create table if not exists
        with db.engine.begin() as conn:
            conn.execute(text("""
                CREATE SCHEMA IF NOT EXISTS gold
            """))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS gold.weather_daily (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    location VARCHAR(50) NOT NULL,
                    zip VARCHAR(10),
                    temp_max DOUBLE PRECISION,
                    temp_min DOUBLE PRECISION,
                    precipitation DOUBLE PRECISION,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, location)
                )
            """))

            # Clear existing data for this date range
            logger.info(f"🗑️  Deleting existing weather data from {start} to {end}")
            result = conn.execute(text("""
                DELETE FROM gold.weather_daily
                WHERE date >= :start_date AND date <= :end_date
            """), {"start_date": start, "end_date": end})
            logger.info(f"   Deleted {result.rowcount} existing records")

        # Save to database with optimized chunking
        logger.info("💾 Saving weather data to database...")
        weather_df.to_sql(
            'weather_daily',
            db.engine,
            schema='gold',
            if_exists='append',
            index=False,
            method='multi',
            chunksize=500
        )

        logger.info("✅ Weather data saved to gold.weather_daily")
        logger.info("=" * 70)

        return weather_df

    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Fetch and save weather data')
    parser.add_argument('--days-back', type=int, default=730, help='Historical days to fetch')
    parser.add_argument('--days-forward', type=int, default=14, help='Forecast days to fetch')

    args = parser.parse_args()

    fetch_and_save_weather(
        days_back=args.days_back,
        days_forward=args.days_forward
    )
