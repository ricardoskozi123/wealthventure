#!/usr/bin/env python3
"""
Test Backup System for Stanford Capital
Quick test to verify backup functionality
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

def test_database_connection():
    """Test if we can connect to the database"""
    print("🔍 Testing database connection...")
    
    # Test PostgreSQL connection
    try:
        cmd = [
            'pg_isready',
            '-h', 'db',
            '-p', '5432',
            '-U', 'omcrm_user',
            '-d', 'omcrm_trading'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Database connection successful")
            return True
        else:
            print(f"❌ Database connection failed: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("❌ pg_isready command not found. Installing postgresql-client...")
        try:
            subprocess.run(['apt-get', 'update'], check=True)
            subprocess.run(['apt-get', 'install', '-y', 'postgresql-client'], check=True)
            print("✅ PostgreSQL client installed")
            return test_database_connection()  # Retry
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install postgresql-client: {e}")
            return False

def test_backup_directory():
    """Test if backup directory is accessible"""
    print("📁 Testing backup directory...")
    
    backup_dir = Path("/app/backup")
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Test write permissions
        test_file = backup_dir / "test_write.txt"
        test_file.write_text("test")
        test_file.unlink()
        
        print("✅ Backup directory is writable")
        return True
        
    except Exception as e:
        print(f"❌ Backup directory test failed: {e}")
        return False

def test_pg_dump():
    """Test if pg_dump is available and working"""
    print("🗃️  Testing pg_dump...")
    
    try:
        # Test pg_dump version
        result = subprocess.run(['pg_dump', '--version'], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ pg_dump available: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ pg_dump test failed: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("❌ pg_dump not found")
        return False

def run_test_backup():
    """Run a test backup"""
    print("🚀 Running test backup...")
    
    try:
        # Import and run backup
        sys.path.append('/app/scripts')
        from backup_system import BackupManager
        
        backup_manager = BackupManager('backup_config.json')
        backup_file = backup_manager.create_backup()
        
        if backup_file and backup_file.exists():
            file_size = backup_file.stat().st_size
            print(f"✅ Test backup successful!")
            print(f"   File: {backup_file.name}")
            print(f"   Size: {file_size / 1024 / 1024:.2f} MB")
            print(f"   Location: {backup_file}")
            return True
        else:
            print("❌ Test backup failed - no backup file created")
            return False
            
    except Exception as e:
        print(f"❌ Test backup failed: {e}")
        return False

def main():
    """Run all backup tests"""
    print("🧪 Stanford Capital Backup System Test")
    print("=" * 50)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Backup Directory", test_backup_directory),
        ("pg_dump Tool", test_pg_dump),
        ("Full Backup Test", run_test_backup)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        if test_func():
            passed += 1
        else:
            print(f"⚠️  {test_name} failed - check configuration")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Backup system is ready.")
        return True
    else:
        print("⚠️  Some tests failed. Please fix issues before production use.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

