#!/usr/bin/env python3
"""
Backend API Testing for Tracking App
Tests all backend endpoints with realistic data and comprehensive error handling.
"""

import requests
import json
from datetime import datetime, timedelta
import time

# Backend URL from frontend environment
BASE_URL = "https://phone-trace-6.preview.emergentagent.com/api"

class TrackingAppTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.user1_token = None
        self.user2_token = None
        self.user1_id = None
        self.user2_id = None
        self.connection_id = None
        self.alarm_id = None
        self.test_results = []
        # Generate unique timestamp for this test run
        import time
        self.timestamp = str(int(time.time()))
        
    def log_test(self, test_name, success, details=""):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append({
            "test": test_name,
            "status": status,
            "details": details
        })
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
    
    def make_request(self, method, endpoint, data=None, headers=None, expected_status=200):
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            if response.status_code != expected_status:
                return False, f"Expected {expected_status}, got {response.status_code}. Response: {response.text}"
            
            try:
                return True, response.json()
            except:
                return True, response.text
                
        except requests.exceptions.RequestException as e:
            return False, f"Request failed: {str(e)}"
    
    def test_user_registration(self):
        """Test user registration endpoint"""
        print("\n=== Testing User Registration ===")
        
        # Test User 1 Registration
        user1_data = {
            "phone_number": f"+123456{self.timestamp[-4:]}",
            "password": "securepass123",
            "name": "Alice Johnson"
        }
        
        success, response = self.make_request("POST", "/auth/register", user1_data, expected_status=200)
        if success and isinstance(response, dict) and "access_token" in response:
            self.user1_token = response["access_token"]
            self.user1_id = response["user"]["id"]
            self.log_test("User 1 Registration", True, f"User ID: {self.user1_id}")
        else:
            self.log_test("User 1 Registration", False, str(response))
            return False
        
        # Test User 2 Registration
        user2_data = {
            "phone_number": f"+198765{self.timestamp[-4:]}",
            "password": "mypassword456",
            "name": "Bob Smith"
        }
        
        success, response = self.make_request("POST", "/auth/register", user2_data, expected_status=200)
        if success and isinstance(response, dict) and "access_token" in response:
            self.user2_token = response["access_token"]
            self.user2_id = response["user"]["id"]
            self.log_test("User 2 Registration", True, f"User ID: {self.user2_id}")
        else:
            self.log_test("User 2 Registration", False, str(response))
            return False
        
        # Test duplicate registration (should fail)
        success, response = self.make_request("POST", "/auth/register", user1_data, expected_status=400)
        if success:
            self.log_test("Duplicate Registration Prevention", True, "Correctly rejected duplicate phone number")
        else:
            self.log_test("Duplicate Registration Prevention", False, str(response))
        
        return True
    
    def test_user_login(self):
        """Test user login endpoint"""
        print("\n=== Testing User Login ===")
        
        # Test valid login
        login_data = {
            "phone_number": f"+123456{self.timestamp[-4:]}",
            "password": "securepass123"
        }
        
        success, response = self.make_request("POST", "/auth/login", login_data, expected_status=200)
        if success and isinstance(response, dict) and "access_token" in response:
            self.log_test("Valid Login", True, "Login successful")
        else:
            self.log_test("Valid Login", False, str(response))
            return False
        
        # Test invalid password
        invalid_login = {
            "phone_number": f"+123456{self.timestamp[-4:]}",
            "password": "wrongpassword"
        }
        
        success, response = self.make_request("POST", "/auth/login", invalid_login, expected_status=401)
        if success:
            self.log_test("Invalid Password Rejection", True, "Correctly rejected invalid password")
        else:
            self.log_test("Invalid Password Rejection", False, str(response))
        
        # Test non-existent user
        nonexistent_login = {
            "phone_number": "+9999999999",
            "password": "anypassword"
        }
        
        success, response = self.make_request("POST", "/auth/login", nonexistent_login, expected_status=401)
        if success:
            self.log_test("Non-existent User Rejection", True, "Correctly rejected non-existent user")
        else:
            self.log_test("Non-existent User Rejection", False, str(response))
        
        return True
    
    def test_get_current_user(self):
        """Test get current user endpoint"""
        print("\n=== Testing Get Current User ===")
        
        # Test with valid token
        headers = {"Authorization": f"Bearer {self.user1_token}"}
        success, response = self.make_request("GET", "/auth/me", headers=headers, expected_status=200)
        if success and isinstance(response, dict) and response.get("id") == self.user1_id:
            self.log_test("Get Current User (Valid Token)", True, f"Retrieved user: {response.get('name')}")
        else:
            self.log_test("Get Current User (Valid Token)", False, str(response))
            return False
        
        # Test with invalid token
        headers = {"Authorization": "Bearer invalid_token"}
        success, response = self.make_request("GET", "/auth/me", headers=headers, expected_status=401)
        if success:
            self.log_test("Get Current User (Invalid Token)", True, "Correctly rejected invalid token")
        else:
            self.log_test("Get Current User (Invalid Token)", False, str(response))
        
        # Test without token
        success, response = self.make_request("GET", "/auth/me", expected_status=403)
        if success:
            self.log_test("Get Current User (No Token)", True, "Correctly rejected missing token")
        else:
            self.log_test("Get Current User (No Token)", False, str(response))
        
        return True
    
    def test_location_updates(self):
        """Test location update and retrieval endpoints"""
        print("\n=== Testing Location Updates ===")
        
        # Update User 1 location
        headers = {"Authorization": f"Bearer {self.user1_token}"}
        location_data = {
            "latitude": 37.7749,
            "longitude": -122.4194
        }
        
        success, response = self.make_request("POST", "/locations", location_data, headers, expected_status=200)
        if success and isinstance(response, dict) and "id" in response:
            self.log_test("User 1 Location Update", True, "Location updated successfully")
        else:
            self.log_test("User 1 Location Update", False, str(response))
            return False
        
        # Update User 2 location
        headers = {"Authorization": f"Bearer {self.user2_token}"}
        location_data = {
            "latitude": 40.7128,
            "longitude": -74.0060
        }
        
        success, response = self.make_request("POST", "/locations", location_data, headers, expected_status=200)
        if success and isinstance(response, dict) and "id" in response:
            self.log_test("User 2 Location Update", True, "Location updated successfully")
        else:
            self.log_test("User 2 Location Update", False, str(response))
            return False
        
        # Test unauthorized location update
        success, response = self.make_request("POST", "/locations", location_data, expected_status=403)
        if success:
            self.log_test("Unauthorized Location Update", True, "Correctly rejected unauthorized request")
        else:
            self.log_test("Unauthorized Location Update", False, str(response))
        
        return True
    
    def test_connection_management(self):
        """Test connection request, accept, and listing"""
        print("\n=== Testing Connection Management ===")
        
        # User 1 sends connection request to User 2
        headers = {"Authorization": f"Bearer {self.user1_token}"}
        request_data = {
            "target_phone": f"+198765{self.timestamp[-4:]}"
        }
        
        success, response = self.make_request("POST", "/connections/request", request_data, headers, expected_status=200)
        if success and isinstance(response, dict) and "id" in response:
            self.connection_id = response["id"]
            self.log_test("Send Connection Request", True, f"Request ID: {self.connection_id}")
        else:
            self.log_test("Send Connection Request", False, str(response))
            return False
        
        # Test duplicate connection request (should fail)
        success, response = self.make_request("POST", "/connections/request", request_data, headers, expected_status=400)
        if success:
            self.log_test("Duplicate Connection Request Prevention", True, "Correctly rejected duplicate request")
        else:
            self.log_test("Duplicate Connection Request Prevention", False, str(response))
        
        # User 2 checks pending requests
        headers = {"Authorization": f"Bearer {self.user2_token}"}
        success, response = self.make_request("GET", "/connections/pending", headers=headers, expected_status=200)
        if success and isinstance(response, list) and len(response) > 0:
            self.log_test("Get Pending Requests", True, f"Found {len(response)} pending request(s)")
        else:
            self.log_test("Get Pending Requests", False, str(response))
            return False
        
        # User 2 accepts the connection
        success, response = self.make_request("POST", f"/connections/{self.connection_id}/accept", headers=headers, expected_status=200)
        if success:
            self.log_test("Accept Connection", True, "Connection accepted successfully")
        else:
            self.log_test("Accept Connection", False, str(response))
            return False
        
        # Test unauthorized connection acceptance
        headers = {"Authorization": f"Bearer {self.user1_token}"}
        success, response = self.make_request("POST", f"/connections/{self.connection_id}/accept", headers=headers, expected_status=404)
        if success:
            self.log_test("Unauthorized Connection Accept", True, "Correctly rejected unauthorized accept")
        else:
            self.log_test("Unauthorized Connection Accept", False, str(response))
        
        return True
    
    def test_location_access(self):
        """Test location access between connected users"""
        print("\n=== Testing Location Access ===")
        
        # User 1 should be able to access User 2's location (they are connected)
        headers = {"Authorization": f"Bearer {self.user1_token}"}
        success, response = self.make_request("GET", f"/locations/{self.user2_id}", headers=headers, expected_status=200)
        if success and isinstance(response, dict) and "latitude" in response:
            self.log_test("Connected User Location Access", True, f"Retrieved location: {response['latitude']}, {response['longitude']}")
        else:
            self.log_test("Connected User Location Access", False, str(response))
            return False
        
        # Test location history access
        success, response = self.make_request("GET", f"/locations/history/{self.user2_id}", headers=headers, expected_status=200)
        if success and isinstance(response, list):
            self.log_test("Location History Access", True, f"Retrieved {len(response)} location records")
        else:
            self.log_test("Location History Access", False, str(response))
            return False
        
        # Test own location access
        success, response = self.make_request("GET", f"/locations/{self.user1_id}", headers=headers, expected_status=200)
        if success and isinstance(response, dict) and "latitude" in response:
            self.log_test("Own Location Access", True, "Successfully retrieved own location")
        else:
            self.log_test("Own Location Access", False, str(response))
        
        return True
    
    def test_connection_listing(self):
        """Test listing all connections"""
        print("\n=== Testing Connection Listing ===")
        
        # User 1 lists connections
        headers = {"Authorization": f"Bearer {self.user1_token}"}
        success, response = self.make_request("GET", "/connections", headers=headers, expected_status=200)
        if success and isinstance(response, list) and len(response) > 0:
            connection = response[0]
            if "user" in connection and "location" in connection:
                self.log_test("List Connections", True, f"Found {len(response)} connection(s) with location data")
            else:
                self.log_test("List Connections", False, "Connection data missing user or location info")
        else:
            self.log_test("List Connections", False, str(response))
            return False
        
        return True
    
    def test_alarm_management(self):
        """Test alarm creation, listing, and deletion"""
        print("\n=== Testing Alarm Management ===")
        
        # Create alarm
        headers = {"Authorization": f"Bearer {self.user1_token}"}
        future_time = datetime.utcnow() + timedelta(hours=1)
        alarm_data = {
            "title": "Important Meeting",
            "message": "Don't forget the quarterly review meeting",
            "trigger_time": future_time.isoformat()
        }
        
        success, response = self.make_request("POST", "/alarms", alarm_data, headers, expected_status=200)
        if success and isinstance(response, dict) and "id" in response:
            self.alarm_id = response["id"]
            self.log_test("Create Alarm", True, f"Alarm ID: {self.alarm_id}")
        else:
            self.log_test("Create Alarm", False, str(response))
            return False
        
        # List alarms
        success, response = self.make_request("GET", "/alarms", headers=headers, expected_status=200)
        if success and isinstance(response, list) and len(response) > 0:
            alarm = response[0]
            if alarm.get("title") == "Important Meeting":
                self.log_test("List Alarms", True, f"Found {len(response)} alarm(s)")
            else:
                self.log_test("List Alarms", False, "Alarm data doesn't match created alarm")
        else:
            self.log_test("List Alarms", False, str(response))
            return False
        
        # Delete alarm
        success, response = self.make_request("DELETE", f"/alarms/{self.alarm_id}", headers=headers, expected_status=200)
        if success:
            self.log_test("Delete Alarm", True, "Alarm deleted successfully")
        else:
            self.log_test("Delete Alarm", False, str(response))
            return False
        
        # Verify alarm is deleted
        success, response = self.make_request("GET", "/alarms", headers=headers, expected_status=200)
        if success and isinstance(response, list) and len(response) == 0:
            self.log_test("Verify Alarm Deletion", True, "Alarm list is empty after deletion")
        else:
            self.log_test("Verify Alarm Deletion", False, f"Expected empty list, got: {response}")
        
        # Test unauthorized alarm deletion
        success, response = self.make_request("DELETE", f"/alarms/nonexistent_id", headers=headers, expected_status=404)
        if success:
            self.log_test("Unauthorized Alarm Deletion", True, "Correctly rejected non-existent alarm deletion")
        else:
            self.log_test("Unauthorized Alarm Deletion", False, str(response))
        
        return True
    
    def run_all_tests(self):
        """Run all backend tests in sequence"""
        print("🚀 Starting Backend API Tests for Tracking App")
        print(f"Testing against: {self.base_url}")
        print("=" * 60)
        
        # Run tests in order
        tests = [
            self.test_user_registration,
            self.test_user_login,
            self.test_get_current_user,
            self.test_location_updates,
            self.test_connection_management,
            self.test_location_access,
            self.test_connection_listing,
            self.test_alarm_management
        ]
        
        all_passed = True
        for test in tests:
            try:
                result = test()
                if not result:
                    all_passed = False
            except Exception as e:
                self.log_test(test.__name__, False, f"Test crashed: {str(e)}")
                all_passed = False
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if "✅" in result["status"])
        failed = sum(1 for result in self.test_results if "❌" in result["status"])
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        
        if failed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if "❌" in result["status"]:
                    print(f"  - {result['test']}: {result['details']}")
        
        if all_passed:
            print("\n🎉 ALL TESTS PASSED! Backend API is working correctly.")
        else:
            print(f"\n⚠️  {failed} test(s) failed. Please check the issues above.")
        
        return all_passed

if __name__ == "__main__":
    tester = TrackingAppTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)