-- Truncate all tables for clean resync
-- Run this in pgAdmin before resyncing data

-- Gold layer first (due to foreign key dependencies)
TRUNCATE gold.fact_sales CASCADE;
TRUNCATE gold.customer_metrics CASCADE;
TRUNCATE gold.dim_customer CASCADE;
TRUNCATE gold.dim_product CASCADE;
TRUNCATE gold.dim_location CASCADE;

-- Silver layer
TRUNCATE silver.transactions CASCADE;
TRUNCATE silver.customers CASCADE;
TRUNCATE silver.products CASCADE;
TRUNCATE silver.locations CASCADE;

-- Bronze layer
TRUNCATE bronze.sales_transactions CASCADE;
TRUNCATE bronze.square_orders CASCADE;
TRUNCATE bronze.square_line_items CASCADE;

-- Success message (will appear in pgAdmin output)
SELECT 'All tables truncated successfully - ready for clean resync' as status;
