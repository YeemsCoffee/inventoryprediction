-- Migration: Add customer_id column to bronze.square_orders
-- This fixes the fact_sales query to join directly without expensive subquery

-- Add customer_id column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='bronze' AND table_name='square_orders' AND column_name='customer_id'
    ) THEN
        ALTER TABLE bronze.square_orders ADD COLUMN customer_id VARCHAR(255);
        RAISE NOTICE 'Added customer_id column to bronze.square_orders';
    ELSE
        RAISE NOTICE 'customer_id column already exists in bronze.square_orders';
    END IF;
END $$;

-- Create index for faster joins
CREATE INDEX IF NOT EXISTS idx_bronze_orders_customer ON bronze.square_orders(customer_id);

-- Update existing orders with customer_id if needed (usually GUEST for anonymous)
-- UPDATE bronze.square_orders SET customer_id = 'GUEST' WHERE customer_id IS NULL;
