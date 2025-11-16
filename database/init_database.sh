#!/bin/bash
# ============================================================================
# Initialize PostgreSQL Database for Inventory BI
# ============================================================================

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}  PostgreSQL Database Initialization for Inventory BI${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo ""

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}ERROR: DATABASE_URL environment variable is not set${NC}"
    echo ""
    echo "Please set DATABASE_URL in your .env file or environment:"
    echo "  export DATABASE_URL='postgresql://user:password@localhost:5432/inventory_bi'"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ DATABASE_URL is set${NC}"
echo ""

# Run schema files in order
SCHEMA_DIR="$(dirname "$0")/schemas"

echo -e "${BLUE}Step 1: Creating schemas...${NC}"
psql "$DATABASE_URL" -f "$SCHEMA_DIR/01_create_schemas.sql"
echo -e "${GREEN}✓ Schemas created${NC}"
echo ""

echo -e "${BLUE}Step 2: Creating bronze tables...${NC}"
psql "$DATABASE_URL" -f "$SCHEMA_DIR/02_bronze_tables.sql"
echo -e "${GREEN}✓ Bronze tables created${NC}"
echo ""

echo -e "${BLUE}Step 3: Creating silver tables...${NC}"
psql "$DATABASE_URL" -f "$SCHEMA_DIR/03_silver_tables.sql"
echo -e "${GREEN}✓ Silver tables created${NC}"
echo ""

echo -e "${BLUE}Step 4: Creating gold tables...${NC}"
psql "$DATABASE_URL" -f "$SCHEMA_DIR/04_gold_tables.sql"
echo -e "${GREEN}✓ Gold tables created${NC}"
echo ""

echo -e "${BLUE}Step 5: Creating features and predictions tables...${NC}"
psql "$DATABASE_URL" -f "$SCHEMA_DIR/05_features_predictions.sql"
echo -e "${GREEN}✓ Features and predictions tables created${NC}"
echo ""

echo -e "${BLUE}Step 6: Populating date dimension...${NC}"
psql "$DATABASE_URL" -f "$SCHEMA_DIR/06_populate_dim_date.sql"
echo -e "${GREEN}✓ Date dimension populated${NC}"
echo ""

echo -e "${BLUE}======================================================================${NC}"
echo -e "${GREEN}✓ Database initialization complete!${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Run CSV migration: python scripts/migrate_csv_to_postgres.py"
echo "  2. Set up incremental sync: python scripts/sync_square_to_postgres.py"
echo "  3. Run dbt transformations: dbt run"
echo ""
