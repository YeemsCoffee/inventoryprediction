# Square API Setup Guide

Quick guide to get your Square API credentials configured for production.

## 🔑 Getting Your Square Access Token

### Step 1: Create Square Developer Account

1. Go to https://developer.squareup.com/
2. Sign in with your Square account (the same one you use for your POS)
3. Accept the developer terms if prompted

### Step 2: Create an Application

1. Click **"Applications"** in the top menu
2. Click **"+ New Application"**
3. Give it a name (e.g., "Inventory BI Dashboard")
4. Click **"Create Application"**

### Step 3: Get Your Access Token

1. Click on your newly created application
2. In the left sidebar, click **"Credentials"**
3. You'll see two environments:
   - **Sandbox** (for testing with fake data)
   - **Production** (for real data)

4. For testing first, use **Sandbox**:
   - Copy the **Sandbox Access Token**
   - Set `SQUARE_ENVIRONMENT=sandbox` in your .env file

5. For production, use **Production**:
   - Copy the **Production Access Token**
   - Set `SQUARE_ENVIRONMENT=production` in your .env file

### Step 4: Configure Your .env File

Create a `.env` file in your project root (if it doesn't exist):

```bash
# Square API Configuration
SQUARE_ACCESS_TOKEN=EAAAl...your-actual-token-here
SQUARE_ENVIRONMENT=sandbox  # or 'production' for real data

# Dashboard Configuration
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8050
DASHBOARD_DEBUG=False
DASHBOARD_DATA_PATH=data/raw/square_sales.csv

# Logging
LOG_LEVEL=INFO
```

**IMPORTANT**: Never commit the .env file to git! It's already in .gitignore.

### Step 5: Test Your Connection

```powershell
# Activate your virtual environment first
venv\Scripts\activate

# Test the Square connection
python examples/square_integration_example.py
```

You should see:
```
✅ Successfully connected to Square API!
Location: Your Store Name
Business Name: Your Business
```

### Step 6: Backfill Your Data

Once the connection test succeeds:

```powershell
# Get last 30 days of data (good for testing)
python sync_square_daily.py backfill 30

# Or get 90 days for more historical data
python sync_square_daily.py backfill 90
```

## 🔄 Sandbox vs Production

### Use Sandbox When:
- Testing the integration for the first time
- Developing new features
- You don't want to affect your live data

### Use Production When:
- Ready to deploy for real business use
- Need actual sales data for analytics
- Running daily automated syncs

## 🚨 Troubleshooting

### 401 Unauthorized Error
- Your access token is invalid or expired
- You're using a sandbox token with `SQUARE_ENVIRONMENT=production` (or vice versa)
- The token was copied incorrectly (check for extra spaces)
- **Fix**: Generate a new token from the Square Developer Portal

### 403 Forbidden Error
- Your application doesn't have the required permissions
- **Fix**: In Square Developer Portal, go to OAuth → Scopes and enable:
  - `ORDERS_READ`
  - `ITEMS_READ`
  - `MERCHANT_PROFILE_READ`

### Connection Timeout
- Check your internet connection
- Square API might be down (check https://status.squareup.com/)

### No Data Returned
- The date range you specified has no transactions
- You're using sandbox environment (which has no real data)
- **Fix**: Create test data in Square sandbox, or switch to production

## 📝 Next Steps After Setup

Once Square is connected:

1. **Run automated daily sync**:
   ```powershell
   python sync_square_daily.py
   ```

2. **Start the production dashboard**:
   ```powershell
   python start_production.py
   ```

3. **Access your dashboard**:
   - Open browser to: http://localhost:8050
   - Or http://your-server-ip:8050 if deployed to cloud

## 🎯 Alternative: Deploy Without Square First

If you want to test production deployment before setting up Square:

1. The dashboard will use sample data automatically if no Square data exists
2. Deploy and test all features with sample data
3. Add Square integration later when ready

This lets you:
- Test the deployment process
- Show the dashboard to stakeholders
- Verify performance and hosting
- Then connect real data when ready

---

**Ready to proceed?** Follow the steps above to get your Square token, or deploy with sample data first to test the infrastructure.
