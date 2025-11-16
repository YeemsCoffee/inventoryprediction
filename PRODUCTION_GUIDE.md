# Production Deployment Guide

Complete guide to deploying your Business Intelligence platform to production.

## 📋 Table of Contents

1. [Connect Real Data](#connect-real-data)
2. [Deploy the Dashboard](#deploy-the-dashboard)
3. [Automate Data Updates](#automate-data-updates)
4. [Security & Authentication](#security--authentication)
5. [Monitoring & Maintenance](#monitoring--maintenance)
6. [Scaling & Performance](#scaling--performance)

---

## 🔌 Connect Real Data

### Option 1: Square API Integration (Automated)

**Step 1: Get Square Access Token**

1. Go to https://developer.squareup.com/apps
2. Create an application
3. Get your **Production Access Token**

**Step 2: Create `.env` file**

```bash
# In your project root
SQUARE_ACCESS_TOKEN=your_production_token_here
SQUARE_ENVIRONMENT=production
```

**Step 3: Set up automated daily sync**

Create `sync_square_daily.py`:

```python
from src.integrations.square_connector import SquareDataConnector
from datetime import datetime, timedelta
import schedule
import time

def sync_data():
    """Sync yesterday's data from Square."""
    connector = SquareDataConnector()

    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    today = datetime.now().strftime('%Y-%m-%d')

    print(f"Syncing Square data for {yesterday}...")
    connector.sync_to_csv(
        start_date=yesterday,
        end_date=today,
        output_path='data/raw/square_sales.csv'
    )
    print("✅ Sync complete!")

# Run daily at 1 AM
schedule.every().day.at("01:00").do(sync_data)

# Or run immediately for backfill
if __name__ == "__main__":
    # Initial backfill - last 90 days
    connector = SquareDataConnector()
    start = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    end = datetime.now().strftime('%Y-%m-%d')
    connector.sync_to_csv(start, end, 'data/raw/square_sales.csv')

    # Then run scheduled updates
    print("Starting scheduled sync...")
    while True:
        schedule.run_pending()
        time.sleep(60)
```

Run it:
```bash
python sync_square_daily.py
```

### Option 2: CSV Upload (Manual)

Put your CSV files in `data/raw/` and modify the dashboard to use them:

```python
# In examples/run_dashboard.py
dashboard = create_simple_dashboard('data/raw/your_sales.csv')
```

---

## 🌐 Deploy the Dashboard

### Option 1: Deploy to Cloud (Recommended)

#### A. Deploy to Heroku (Easiest)

**Step 1: Create `Procfile`**

```
web: gunicorn src.dashboard.simple_dashboard:server
```

**Step 2: Update `requirements.txt`**

Add:
```
gunicorn>=21.2.0
```

**Step 3: Modify dashboard for Heroku**

```python
# In src/dashboard/simple_dashboard.py, add at the end:
server = app.server  # Expose Flask server for gunicorn

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8050)))
```

**Step 4: Deploy**

```bash
# Install Heroku CLI
# Then:
heroku login
heroku create your-bi-dashboard
git push heroku claude/ml-customer-trends-011CUu4anbpoMjhk4jFeo5qE:main
heroku open
```

#### B. Deploy to AWS EC2

**Step 1: Launch EC2 Instance**
- Choose Ubuntu 22.04 LTS
- t2.medium or larger (for ML)
- Open port 8050 in security group

**Step 2: SSH and Setup**

```bash
ssh -i your-key.pem ubuntu@your-ec2-ip

# Install dependencies
sudo apt update
sudo apt install python3-pip python3-venv git -y

# Clone repo
git clone https://github.com/YeemsCoffee/inventoryprediction.git
cd inventoryprediction
git checkout claude/ml-customer-trends-011CUu4anbpoMjhk4jFeo5qE

# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run dashboard
python examples/run_dashboard.py
```

**Step 3: Keep it running with systemd**

Create `/etc/systemd/system/bi-dashboard.service`:

```ini
[Unit]
Description=Business Intelligence Dashboard
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/inventoryprediction
Environment="PATH=/home/ubuntu/inventoryprediction/venv/bin"
ExecStart=/home/ubuntu/inventoryprediction/venv/bin/python examples/run_dashboard.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl enable bi-dashboard
sudo systemctl start bi-dashboard
sudo systemctl status bi-dashboard
```

#### C. Deploy to DigitalOcean App Platform

1. Push code to GitHub
2. Connect DigitalOcean to your repo
3. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Run Command**: `python examples/run_dashboard.py`
4. Deploy!

### Option 2: Run Locally (Development/Internal Use)

**Step 1: Create startup script**

`start_dashboard.bat` (Windows):
```batch
@echo off
cd C:\Users\natha\Desktop\inventoryprediction
call venv\Scripts\activate
python examples\run_dashboard.py
pause
```

`start_dashboard.sh` (Mac/Linux):
```bash
#!/bin/bash
cd ~/inventoryprediction
source venv/bin/activate
python examples/run_dashboard.py
```

**Step 2: Run on startup**

Windows: Put shortcut in Startup folder
Mac/Linux: Add to crontab

---

## 🔄 Automate Data Updates

### Option 1: Scheduled Square Sync

**Using Task Scheduler (Windows)**

1. Open Task Scheduler
2. Create Basic Task
3. **Trigger**: Daily at 1 AM
4. **Action**: Start a program
   - Program: `C:\Users\natha\Desktop\inventoryprediction\venv\Scripts\python.exe`
   - Arguments: `sync_square_daily.py`
   - Start in: `C:\Users\natha\Desktop\inventoryprediction`

**Using Cron (Mac/Linux)**

```bash
crontab -e

# Add:
0 1 * * * cd /path/to/inventoryprediction && /path/to/venv/bin/python sync_square_daily.py
```

### Option 2: Real-time Updates

For real-time dashboard updates, use a database:

**Step 1: Set up PostgreSQL**

```bash
# Install PostgreSQL
# Create database
createdb inventory_bi

# Update .env
DATABASE_URL=postgresql://user:password@localhost/inventory_bi
```

**Step 2: Modify dashboard to use database**

```python
from sqlalchemy import create_engine
import os

engine = create_engine(os.getenv('DATABASE_URL'))

# Load data from database instead of CSV
data = pd.read_sql('SELECT * FROM transactions', engine)
```

---

## 🔐 Security & Authentication

### Add Password Protection

**Using Dash Basic Auth:**

```python
# Add to requirements.txt
dash-auth>=2.0.0

# In simple_dashboard.py
import dash_auth

VALID_USERNAME_PASSWORD_PAIRS = {
    'admin': 'your-secure-password',
    'viewer': 'viewer-password'
}

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
auth = dash_auth.BasicAuth(app, VALID_USERNAME_PASSWORD_PAIRS)
```

### Secure Square API Token

**Never commit tokens to git!**

```bash
# Use environment variables
export SQUARE_ACCESS_TOKEN="your-token"

# Or use a secrets manager
# AWS Secrets Manager, Azure Key Vault, etc.
```

### HTTPS/SSL

For production, always use HTTPS:

**Option 1: Use a reverse proxy (nginx)**

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8050;
        proxy_set_header Host $host;
    }
}
```

Then use Let's Encrypt for SSL:
```bash
sudo certbot --nginx -d your-domain.com
```

---

## 📊 Monitoring & Maintenance

### Set Up Monitoring

**1. Application Monitoring**

```python
# Add logging
import logging

logging.basicConfig(
    filename='dashboard.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logging.info('Dashboard started')
```

**2. Error Notifications**

Use a service like Sentry:

```bash
pip install sentry-sdk

# In dashboard
import sentry_sdk
sentry_sdk.init(dsn="your-sentry-dsn")
```

**3. Uptime Monitoring**

Use services like:
- UptimeRobot (free)
- Pingdom
- StatusCake

### Regular Maintenance

**Weekly:**
- Check logs for errors
- Review dashboard performance
- Verify data sync is working

**Monthly:**
- Update dependencies: `pip install -r requirements.txt --upgrade`
- Retrain ML models with new data
- Review and optimize slow queries

**Quarterly:**
- Full security audit
- Performance optimization
- Feature updates based on feedback

---

## ⚡ Scaling & Performance

### For Large Datasets (100K+ transactions)

**1. Use Database Instead of CSV**

```python
# Much faster for large data
data = pd.read_sql('''
    SELECT * FROM transactions
    WHERE date >= CURRENT_DATE - INTERVAL '90 days'
''', engine)
```

**2. Cache Computations**

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_analysis():
    return ml_app.analyze_seasonal_trends()
```

**3. Use Aggregated Data**

Pre-aggregate daily/weekly instead of processing every transaction:

```python
# Instead of processing 1M transactions
# Pre-aggregate to 365 daily records
daily_agg = data.groupby('date').agg({
    'amount': 'sum',
    'customer_id': 'nunique'
}).reset_index()
```

**4. Background Processing**

Run heavy ML computations in background:

```python
from celery import Celery

app = Celery('tasks', broker='redis://localhost:6379')

@app.task
def update_forecasts():
    # Run ML models
    # Save results to database
    pass
```

---

## 🎯 Production Checklist

### Before Going Live

- [ ] Real data connected (Square or CSV)
- [ ] Environment variables configured (`.env`)
- [ ] Dashboard running on server
- [ ] HTTPS/SSL enabled
- [ ] Authentication enabled
- [ ] Automated data sync working
- [ ] Monitoring set up
- [ ] Backups configured
- [ ] Error logging enabled
- [ ] Documentation updated

### Post-Launch

- [ ] Test all features with real users
- [ ] Monitor performance metrics
- [ ] Set up alerts for errors
- [ ] Schedule weekly data reviews
- [ ] Plan for ML model retraining
- [ ] Create user guide for team

---

## 💡 Quick Start Commands

### Local Development
```bash
# Daily workflow
cd inventoryprediction
venv\Scripts\activate  # Windows
python examples/run_dashboard.py
```

### Production Server
```bash
# Deploy
git pull origin main
pip install -r requirements.txt
sudo systemctl restart bi-dashboard
```

### Data Sync
```bash
# Manual sync
python sync_square_daily.py

# Check status
tail -f dashboard.log
```

---

## 🆘 Troubleshooting

### Dashboard won't start
- Check logs: `cat dashboard.log`
- Verify port 8050 is available: `netstat -an | grep 8050`
- Check venv is activated

### Data not updating
- Verify Square API token is valid
- Check sync logs
- Ensure file permissions are correct

### Slow performance
- Check data size (limit to last 90 days)
- Enable database caching
- Upgrade server resources

---

## 📞 Support

For issues:
1. Check logs first
2. Review this guide
3. Check GitHub issues
4. Create new issue with logs and error details

---

**You're ready for production! Start with Square integration and local deployment, then scale up as needed.** 🚀
