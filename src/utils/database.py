"""
Database connector for Amazon RDS (PostgreSQL/MySQL).
"""

import os
import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from typing import Optional, Dict, List
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RDSConnector:
    """Connect to Amazon RDS and manage sales data."""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize RDS connector.

        Args:
            database_url: Database connection string (if None, reads from environment)
                         Format: postgresql://user:password@host:port/database
                         or: mysql+pymysql://user:password@host:port/database
        """
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError(
                "Database URL is required. Set DATABASE_URL environment variable.\n"
                "Format: postgresql://user:password@host:port/database"
            )

        self.engine: Optional[Engine] = None
        self._connect()

    def _connect(self):
        """Establish database connection."""
        try:
            self.engine = create_engine(
                self.database_url,
                pool_pre_ping=True,  # Verify connections before using
                pool_recycle=3600,   # Recycle connections after 1 hour
                echo=False           # Set to True for SQL debugging
            )
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection established successfully")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {str(e)}")
            raise

    def test_connection(self) -> Dict:
        """
        Test the database connection.

        Returns:
            Dictionary with connection status
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).fetchone()

                # Get database info
                inspector = inspect(self.engine)
                tables = inspector.get_table_names()

                return {
                    'success': True,
                    'message': 'Connected to database successfully',
                    'database': self.engine.url.database,
                    'host': self.engine.url.host,
                    'tables': tables,
                    'table_count': len(tables)
                }
        except Exception as e:
            return {
                'success': False,
                'message': f'Connection failed: {str(e)}'
            }

    def create_sales_table(self, table_name: str = 'sales_transactions'):
        """
        Create sales transactions table if it doesn't exist.

        Args:
            table_name: Name of the table to create
        """
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id SERIAL PRIMARY KEY,
            order_id VARCHAR(255),
            date TIMESTAMP NOT NULL,
            customer_id VARCHAR(255),
            location_id VARCHAR(255),
            product VARCHAR(255),
            item_type VARCHAR(50),
            amount INTEGER,
            price DECIMAL(10, 2),
            category VARCHAR(255),
            variation_id VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_date ON {table_name}(date);
        CREATE INDEX IF NOT EXISTS idx_customer ON {table_name}(customer_id);
        CREATE INDEX IF NOT EXISTS idx_product ON {table_name}(product);
        """

        try:
            with self.engine.begin() as conn:
                conn.execute(text(create_table_sql))
            logger.info(f"✅ Table '{table_name}' created successfully")
        except Exception as e:
            logger.error(f"❌ Failed to create table: {str(e)}")
            raise

    def insert_dataframe(self, df: pd.DataFrame, table_name: str = 'sales_transactions',
                        if_exists: str = 'append') -> int:
        """
        Insert DataFrame into database table.

        Args:
            df: DataFrame to insert
            table_name: Target table name
            if_exists: How to behave if table exists ('fail', 'replace', 'append')

        Returns:
            Number of rows inserted
        """
        try:
            rows_inserted = df.to_sql(
                name=table_name,
                con=self.engine,
                if_exists=if_exists,
                index=False,
                chunksize=1000  # Insert in chunks for better performance
            )
            logger.info(f"✅ Inserted {len(df)} rows into '{table_name}'")
            return len(df)
        except Exception as e:
            logger.error(f"❌ Failed to insert data: {str(e)}")
            raise

    def query_to_dataframe(self, query: str) -> pd.DataFrame:
        """
        Execute SQL query and return results as DataFrame.

        Args:
            query: SQL query to execute

        Returns:
            DataFrame with query results
        """
        try:
            df = pd.read_sql_query(query, self.engine)
            logger.info(f"✅ Query returned {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"❌ Query failed: {str(e)}")
            raise

    def get_sales_data(self, start_date: Optional[str] = None,
                      end_date: Optional[str] = None,
                      table_name: str = 'sales_transactions') -> pd.DataFrame:
        """
        Retrieve sales data from database.

        Args:
            start_date: Start date (YYYY-MM-DD) - optional
            end_date: End date (YYYY-MM-DD) - optional
            table_name: Table to query from

        Returns:
            DataFrame with sales data
        """
        query = f"SELECT * FROM {table_name}"

        conditions = []
        if start_date:
            conditions.append(f"date >= '{start_date}'")
        if end_date:
            conditions.append(f"date <= '{end_date}'")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY date"

        return self.query_to_dataframe(query)

    def sync_square_to_database(self, square_connector, start_date: str,
                               end_date: str, table_name: str = 'sales_transactions'):
        """
        Fetch data from Square and insert into database.

        Args:
            square_connector: SquareDataConnector instance
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            table_name: Target table name
        """
        logger.info(f"📡 Fetching Square data from {start_date} to {end_date}...")

        # Fetch from Square
        orders_df = square_connector.fetch_orders(start_date, end_date)

        if orders_df.empty:
            logger.warning("⚠️  No data fetched from Square")
            return 0

        logger.info(f"✅ Fetched {len(orders_df)} transactions from Square")

        # Create table if it doesn't exist
        self.create_sales_table(table_name)

        # Insert into database
        rows_inserted = self.insert_dataframe(orders_df, table_name, if_exists='append')

        logger.info(f"✅ Synced {rows_inserted} rows to database")
        return rows_inserted

    def get_table_stats(self, table_name: str = 'sales_transactions') -> Dict:
        """
        Get statistics about a table.

        Args:
            table_name: Table to analyze

        Returns:
            Dictionary with table statistics
        """
        query = f"""
        SELECT
            COUNT(*) as total_rows,
            COUNT(DISTINCT customer_id) as unique_customers,
            COUNT(DISTINCT product) as unique_products,
            MIN(date) as earliest_date,
            MAX(date) as latest_date,
            SUM(amount) as total_items_sold,
            SUM(price) as total_revenue
        FROM {table_name}
        """

        try:
            result = pd.read_sql_query(query, self.engine)
            return result.to_dict('records')[0]
        except Exception as e:
            logger.error(f"❌ Failed to get stats: {str(e)}")
            return {}

    def export_to_csv(self, table_name: str = 'sales_transactions',
                     output_path: str = 'data/raw/from_database.csv',
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None):
        """
        Export database table to CSV file.

        Args:
            table_name: Table to export
            output_path: Where to save CSV
            start_date: Optional start date filter
            end_date: Optional end date filter
        """
        df = self.get_sales_data(start_date, end_date, table_name)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_csv(output_path, index=False)

        logger.info(f"💾 Exported {len(df)} rows to {output_path}")
        return df

    def close(self):
        """Close database connection."""
        if self.engine:
            self.engine.dispose()
            logger.info("✅ Database connection closed")
