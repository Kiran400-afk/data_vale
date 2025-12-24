#!/usr/bin/env python
"""
NYX Data Validator - Quick Start Script
Run this file to start the application: python run_app.py
"""
import os
import sys
import subprocess

def main():
    # Change to backend directory
    backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
    os.chdir(backend_dir)
    
    print("=" * 60)
    print("🚀 NYX Data Validator - Starting Server")
    print("=" * 60)
    print()
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("⚠️  No .env file found. Creating from .env.example...")
        if os.path.exists('.env.example'):
            import shutil
            shutil.copy('.env.example', '.env')
            print("✅ Created .env file. Please edit it with your API keys.")
        else:
            print("❌ No .env.example found. Creating basic .env...")
            with open('.env', 'w') as f:
                f.write("# NYX Data Validator Configuration\n")
                f.write("GOOGLE_API_KEY=your_api_key_here\n")
                f.write("AUTH_USER1_USERNAME=admin\n")
                f.write("AUTH_USER1_PASSWORD=admin123\n")
                f.write("AUTH_USER2_USERNAME=validator\n")
                f.write("AUTH_USER2_PASSWORD=valid123\n")
                f.write("JWT_SECRET_KEY=nyx-data-validator-secret-key-2024\n")
    
    # Install dependencies if needed
    print("📦 Checking dependencies...")
    try:
        import uvicorn
        import fastapi
        print("✅ Dependencies OK")
    except ImportError:
        print("📥 Installing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("✅ Dependencies installed")
    
    print()
    print("🌐 Server starting at: http://localhost:8000")
    print("📝 Login credentials: admin / admin123")
    print("🛑 Press CTRL+C to stop")
    print()
    print("=" * 60)
    
    # Run uvicorn
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )

if __name__ == "__main__":
    main()
