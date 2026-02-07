#!/usr/bin/env python3
"""
Grid-X Authentication Fix - Automated Test Script

This script tests the authentication system to verify that:
1. New users can register and connect
2. Existing users can reconnect with correct password
3. Wrong passwords are REJECTED (this is the key fix!)
4. Multiple workers can exist for same user with same password

Run this AFTER deploying the fix.
"""

import subprocess
import time
import sys
import os
import signal
import json
from pathlib import Path

# ANSI colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    """Print a section header."""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text:^60}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def print_test(test_name):
    """Print test name."""
    print(f"{YELLOW}TEST: {test_name}{RESET}")

def print_pass(message):
    """Print success message."""
    print(f"{GREEN}✅ PASS: {message}{RESET}")

def print_fail(message):
    """Print failure message."""
    print(f"{RED}❌ FAIL: {message}{RESET}")

def print_info(message):
    """Print info message."""
    print(f"{BLUE}ℹ️  INFO: {message}{RESET}")

class CoordinatorManager:
    """Manages coordinator process for testing."""
    
    def __init__(self):
        self.process = None
    
    def start(self):
        """Start coordinator."""
        print_info("Starting coordinator...")
        self.process = subprocess.Popen(
            [sys.executable, "-m", "coordinator.main"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        # Give it time to start
        time.sleep(3)
        
        if self.process.poll() is not None:
            print_fail("Coordinator failed to start")
            return False
        
        print_pass("Coordinator started")
        return True
    
    def stop(self):
        """Stop coordinator."""
        if self.process:
            print_info("Stopping coordinator...")
            self.process.send_signal(signal.SIGTERM)
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            print_pass("Coordinator stopped")

class WorkerTest:
    """Test wrapper for worker processes."""
    
    @staticmethod
    def run_worker(user, password, timeout=10):
        """
        Run a worker and return (success, output).
        
        Returns:
            (bool, str): (True if connected successfully, stderr output)
        """
        process = subprocess.Popen(
            [sys.executable, "-m", "worker.main", 
             "--user", user, 
             "--password", password, 
             "--no-cli"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for connection or failure
        start_time = time.time()
        while time.time() - start_time < timeout:
            if process.poll() is not None:
                # Process exited
                _, stderr = process.communicate()
                # Check if it was auth failure
                if "AUTHENTICATION FAILED" in stderr:
                    return False, stderr
                else:
                    # Unexpected exit
                    return False, f"Unexpected exit: {stderr}"
            
            time.sleep(0.5)
        
        # Still running - likely connected successfully
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
        
        return True, "Connected successfully"
    
    @staticmethod
    def check_worker_identity_file(user):
        """Check if worker identity file exists."""
        config_file = Path.home() / ".gridx" / f"worker_{user}.json"
        return config_file.exists()
    
    @staticmethod
    def get_worker_id(user):
        """Get worker ID from identity file."""
        config_file = Path.home() / ".gridx" / f"worker_{user}.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                data = json.load(f)
                return data.get('worker_id')
        return None
    
    @staticmethod
    def cleanup_worker_identity(user):
        """Remove worker identity file."""
        config_file = Path.home() / ".gridx" / f"worker_{user}.json"
        if config_file.exists():
            config_file.unlink()

def test_new_user_registration():
    """Test that new users can register successfully."""
    print_test("New user registration")
    
    # Clean up any existing identity
    WorkerTest.cleanup_worker_identity("testuser1")
    
    # Try to connect
    success, output = WorkerTest.run_worker("testuser1", "password123", timeout=8)
    
    if success:
        print_pass("New user registered and connected")
        
        # Verify identity file was created
        if WorkerTest.check_worker_identity_file("testuser1"):
            print_pass("Worker identity file created")
        else:
            print_fail("Worker identity file NOT created")
            return False
        
        return True
    else:
        print_fail(f"New user failed to register: {output}")
        return False

def test_correct_password_reconnection():
    """Test that existing users can reconnect with correct password."""
    print_test("Reconnection with correct password")
    
    # Get original worker ID
    original_worker_id = WorkerTest.get_worker_id("testuser1")
    if not original_worker_id:
        print_fail("No worker identity found from previous test")
        return False
    
    # Try to reconnect with same password
    success, output = WorkerTest.run_worker("testuser1", "password123", timeout=8)
    
    if success:
        # Verify same worker ID
        new_worker_id = WorkerTest.get_worker_id("testuser1")
        if new_worker_id == original_worker_id:
            print_pass(f"Reconnected with same worker ID: {original_worker_id[:16]}...")
            return True
        else:
            print_fail(f"Different worker ID! Original: {original_worker_id[:16]}..., New: {new_worker_id[:16]}...")
            return False
    else:
        print_fail(f"Failed to reconnect: {output}")
        return False

def test_wrong_password_rejection():
    """Test that wrong passwords are REJECTED (key fix!)."""
    print_test("Wrong password rejection (KEY TEST)")
    
    # Try to connect with WRONG password
    success, output = WorkerTest.run_worker("testuser1", "wrongpassword", timeout=8)
    
    if not success:
        # Check that it failed due to authentication
        if "AUTHENTICATION FAILED" in output and "Invalid password" in output:
            print_pass("Wrong password correctly REJECTED ✅")
            print_info("Error message shown to user:")
            # Extract and show the error message
            for line in output.split('\n'):
                if 'AUTHENTICATION' in line or 'password' in line.lower():
                    print(f"  {line.strip()}")
            return True
        else:
            print_fail(f"Failed for wrong reason: {output}")
            return False
    else:
        print_fail("Wrong password was ACCEPTED - BUG STILL EXISTS!")
        return False

def test_multiple_workers_same_user():
    """Test that multiple workers can exist for same user with same password."""
    print_test("Multiple workers for same user (correct password)")
    
    # Clean up test user
    WorkerTest.cleanup_worker_identity("testuser2")
    
    # First worker
    success1, _ = WorkerTest.run_worker("testuser2", "pass456", timeout=8)
    if not success1:
        print_fail("First worker failed to connect")
        return False
    
    worker1_id = WorkerTest.get_worker_id("testuser2")
    
    # Remove identity file to simulate different machine
    WorkerTest.cleanup_worker_identity("testuser2")
    
    # Second worker (same credentials)
    success2, _ = WorkerTest.run_worker("testuser2", "pass456", timeout=8)
    if not success2:
        print_fail("Second worker failed to connect")
        return False
    
    worker2_id = WorkerTest.get_worker_id("testuser2")
    
    if worker1_id != worker2_id:
        print_pass(f"Two different workers created for same user with same password")
        print_info(f"Worker 1: {worker1_id[:16]}...")
        print_info(f"Worker 2: {worker2_id[:16]}...")
        return True
    else:
        print_fail("Same worker ID - identity persistence issue")
        return False

def test_different_users():
    """Test that different users can exist independently."""
    print_test("Different users independence")
    
    # Clean up
    WorkerTest.cleanup_worker_identity("alice")
    WorkerTest.cleanup_worker_identity("bob")
    
    # Alice connects
    success1, _ = WorkerTest.run_worker("alice", "alicepass", timeout=8)
    if not success1:
        print_fail("Alice failed to connect")
        return False
    
    # Bob connects
    success2, _ = WorkerTest.run_worker("bob", "bobpass", timeout=8)
    if not success2:
        print_fail("Bob failed to connect")
        return False
    
    alice_id = WorkerTest.get_worker_id("alice")
    bob_id = WorkerTest.get_worker_id("bob")
    
    if alice_id != bob_id:
        print_pass("Different users have different worker IDs")
        return True
    else:
        print_fail("Different users have same worker ID!")
        return False

def cleanup():
    """Clean up test users."""
    print_info("Cleaning up test users...")
    for user in ["testuser1", "testuser2", "alice", "bob"]:
        WorkerTest.cleanup_worker_identity(user)
    print_pass("Cleanup complete")

def main():
    """Run all authentication tests."""
    print_header("Grid-X Authentication Fix - Test Suite")
    print("This script will verify the authentication fix is working correctly.\n")
    
    # Start coordinator
    coordinator = CoordinatorManager()
    if not coordinator.start():
        print_fail("Cannot start coordinator - aborting tests")
        return 1
    
    try:
        # Run tests
        results = []
        
        results.append(("New user registration", test_new_user_registration()))
        time.sleep(1)
        
        results.append(("Correct password reconnection", test_correct_password_reconnection()))
        time.sleep(1)
        
        results.append(("Wrong password rejection (KEY TEST)", test_wrong_password_rejection()))
        time.sleep(1)
        
        results.append(("Multiple workers same user", test_multiple_workers_same_user()))
        time.sleep(1)
        
        results.append(("Different users independence", test_different_users()))
        
        # Summary
        print_header("Test Results Summary")
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
            print(f"{status}: {test_name}")
        
        print(f"\n{BLUE}Total: {passed}/{total} tests passed{RESET}")
        
        if passed == total:
            print(f"\n{GREEN}{'='*60}")
            print("🎉 ALL TESTS PASSED!")
            print("The authentication fix is working correctly!")
            print(f"{'='*60}{RESET}\n")
            return 0
        else:
            print(f"\n{RED}{'='*60}")
            print("❌ SOME TESTS FAILED")
            print("The authentication fix may not be complete.")
            print(f"{'='*60}{RESET}\n")
            return 1
    
    finally:
        # Stop coordinator and cleanup
        coordinator.stop()
        cleanup()

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Tests interrupted by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Test suite error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
