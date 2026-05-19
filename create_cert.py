#!/usr/bin/env python3
"""
Create self-signed SSL certificate for local IP address
"""

import subprocess
import os
import sys

def create_self_signed_cert():
    """Create self-signed certificate for 192.168.1.19"""
    print("🔐 Creating SSL certificate for 192.168.1.19...")
    
    # Check if OpenSSL is available
    try:
        subprocess.run(["openssl", "version"], check=True, capture_output=True)
        print("✅ OpenSSL found")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ OpenSSL not found. Installing...")
        print("Please install OpenSSL first:")
        print("1. Download OpenSSL: https://slproweb.com/products/Win32OpenSSL.html")
        print("2. Or use chocolatey: choco install openssl")
        return False
    
    # Create certificate
    cmd = [
        "openssl", "req", "-x509", "-newkey", "rsa:4096",
        "-keyout", "key.pem",
        "-out", "cert.pem",
        "-days", "365",
        "-nodes",
        "-subj", "/C=IN/ST=State/L=City/O=Organization/CN=192.168.1.19"
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Certificate created successfully!")
        print("📁 Files created: key.pem, cert.pem")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error creating certificate: {e}")
        return False

if __name__ == "__main__":
    success = create_self_signed_cert()
    if success:
        print("\n🎉 SSL certificate ready for HTTPS!")
        print("🌐 Now you can use: https://192.168.1.19:3000")
    else:
        print("\n❌ Failed to create certificate")
    
    sys.exit(0 if success else 1)
