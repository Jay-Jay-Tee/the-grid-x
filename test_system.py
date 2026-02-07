#!/usr/bin/env python3
"""
Grid-X System Test Script
Tests all critical functionality to ensure everything works
"""

import subprocess
import time
import requests
import json
import sys

def test_imports():
    """Test that all modules can be imported"""
    print("\n🧪 Testing imports...")
    
    try:
        sys.path.insert(0, '/home/claude/grid-x-fixed')
        
        # Test common module
        from common import constants, utils, schemas
        print("  ✅ Common module imports successfully")
        
        # Test coordinator modules  
        from coordinator import database, credit_manager, scheduler
        print("  ✅ Coordinator modules import successfully")
        
        # Verify key functions exist
        assert hasattr(utils, 'validate_uuid')
        assert hasattr(utils, 'validate_user_id')
        assert hasattr(utils, 'sanitize_string')
        assert hasattr(constants, 'STATUS_QUEUED')
        print("  ✅ All expected functions are present")
        
        return True
    except Exception as e:
        print(f"  ❌ Import test failed: {e}")
        return False

def test_database():
    """Test database initialization"""
    print("\n🧪 Testing database...")
    
    try:
        sys.path.insert(0, '/home/claude/grid-x-fixed')
        from coordinator.database import init_db, get_db, db_create_job, db_get_job
        from common.utils import generate_job_id
        
        # Initialize database
        init_db()
        print("  ✅ Database initialized successfully")
        
        # Test job creation
        job_id = generate_job_id()
        db_create_job(job_id, "test_user", "print('test')", "python", {})
        print("  ✅ Job created successfully")
        
        # Test job retrieval
        job = db_get_job(job_id)
        assert job is not None
        assert job['user_id'] == 'test_user'
        print("  ✅ Job retrieved successfully")
        
        return True
    except Exception as e:
        print(f"  ❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_validation():
    """Test input validation functions"""
    print("\n🧪 Testing validation...")
    
    try:
        sys.path.insert(0, '/home/claude/grid-x-fixed')
        from common.utils import validate_uuid, validate_user_id, sanitize_string
        
        # Test UUID validation
        assert validate_uuid("550e8400-e29b-41d4-a716-446655440000") == True
        assert validate_uuid("not-a-uuid") == False
        print("  ✅ UUID validation works")
        
        # Test user ID validation
        assert validate_user_id("alice") == True
        assert validate_user_id("alice-123") == True
        assert validate_user_id("alice@test") == False
        print("  ✅ User ID validation works")
        
        # Test sanitization
        clean = sanitize_string("test\x00string", max_length=10)
        assert '\x00' not in clean
        assert len(clean) <= 10
        print("  ✅ String sanitization works")
        
        return True
    except Exception as e:
        print(f"  ❌ Validation test failed: {e}")
        return False

def test_credit_system():
    """Test credit management"""
    print("\n🧪 Testing credit system...")
    
    try:
        sys.path.insert(0, '/home/claude/grid-x-fixed')
        from coordinator.credit_manager import ensure_user, get_balance, deduct, credit
        
        # Ensure user exists
        ensure_user("test_user")
        print("  ✅ User created")
        
        # Check initial balance
        balance = get_balance("test_user")
        assert balance >= 0
        print(f"  ✅ Initial balance: {balance}")
        
        # Test deduction
        initial = get_balance("test_user")
        if deduct("test_user", 1.0):
            new_balance = get_balance("test_user")
            assert new_balance == initial - 1.0
            print("  ✅ Credit deduction works")
        
            # Test credit
            credit("test_user", 1.0)
            final_balance = get_balance("test_user")
            assert final_balance == initial
            print("  ✅ Credit addition works")
        else:
            print("  ⚠️  Insufficient credits for deduction test")
        
        return True
    except Exception as e:
        print(f"  ❌ Credit system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def print_summary():
    """Print test summary"""
    print("\n" + "="*60)
    print("📊 GRID-X SYSTEM TEST SUMMARY")
    print("="*60)
    print("\n✅ All critical components tested successfully!")
    print("\nSystem is ready for deployment.")
    print("\nNext steps:")
    print("1. Start coordinator: cd coordinator && python -m coordinator.main")
    print("2. Start worker: cd worker && python -m worker.main --user test --password test123")
    print("3. Submit jobs and verify end-to-end functionality")
    print("\nSee COMPLETE_SETUP_GUIDE.md for detailed instructions.")
    print("="*60 + "\n")

if __name__ == "__main__":
    print("="*60)
    print("🚀 GRID-X SYSTEM TEST")
    print("="*60)
    
    all_passed = True
    
    # Run tests
    all_passed &= test_imports()
    all_passed &= test_database()
    all_passed &= test_validation()
    all_passed &= test_credit_system()
    
    if all_passed:
        print_summary()
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please review the output above.")
        sys.exit(1)
