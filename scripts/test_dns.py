"""Test DNS resolution for RDS hostname"""
import socket

hostname = "inventorybi.cn4cyew02c9g.us-west-1.rds.amazonaws.com"

try:
    ip = socket.gethostbyname(hostname)
    print(f"✅ DNS resolved: {hostname} -> {ip}")
except socket.gaierror as e:
    print(f"❌ DNS resolution failed: {e}")
    print(f"\nThis could mean:")
    print(f"  1. The RDS instance no longer exists")
    print(f"  2. The hostname is incorrect")
    print(f"  3. Network/DNS is not accessible from this environment")
    print(f"\nPlease verify:")
    print(f"  - Your RDS instance is running in AWS Console")
    print(f"  - The endpoint hostname is correct")
