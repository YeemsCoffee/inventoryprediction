-- ============================================================================
-- Database Schema Setup for Inventory BI
-- Medallion Architecture: Bronze → Silver → Gold → Features → Predictions
-- ============================================================================

-- Create schemas
CREATE SCHEMA IF NOT EXISTS bronze;  -- Raw data from Square API
CREATE SCHEMA IF NOT EXISTS silver;  -- Cleaned, typed, deduplicated
CREATE SCHEMA IF NOT EXISTS gold;    -- Analytics-ready dimensional model
CREATE SCHEMA IF NOT EXISTS features; -- ML feature tables
CREATE SCHEMA IF NOT EXISTS predictions; -- ML model outputs
CREATE SCHEMA IF NOT EXISTS metadata; -- System metadata (sync logs, etc.)

-- Set search path
SET search_path TO bronze, silver, gold, features, predictions, metadata, public;

-- Comments
COMMENT ON SCHEMA bronze IS 'Raw immutable data from Square API';
COMMENT ON SCHEMA silver IS 'Cleaned and typed data with business logic applied';
COMMENT ON SCHEMA gold IS 'Analytics-ready star schema for BI and reporting';
COMMENT ON SCHEMA features IS 'ML feature tables for model training and inference';
COMMENT ON SCHEMA predictions IS 'ML model outputs and scores';
COMMENT ON SCHEMA metadata IS 'System metadata, sync logs, and data lineage';
