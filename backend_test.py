#!/usr/bin/env python3

import requests
import json
import sys
from datetime import datetime

# Backend URL from frontend .env
BACKEND_URL = "https://phone-trace-6.preview.emergentagent.com/api"

def test_location_address_fields():
    """Test the updated location endpoint with street name/address fields"""
    
    print("🧪 Testing Location Address Fields Functionality")
    print("=" * 60)
    
    # Test data with unique phone numbers
    import time
    timestamp = str(int(time.time()))
    test_user1 = {
        "phone_number": f"+123456{timestamp}1",
        "password": "testpass123",
        "name": "Test User 1"
    }
    
    test_user2 = {
        "phone_number": f"+123456{timestamp}2", 
        "password": "testpass123",
        "name": "Test User 2"
    }
    
    test_location = {
        "latitude": 37.7749,
        "longitude": -122.4194,
        "address": "123 Market Street",
        "street": "Market Street", 
        "city": "San Francisco",
        "country": "USA"
    }
    
    try:
        # Step 1: Register first user
        print("\n1️⃣ Registering first user...")
        response = requests.post(f"{BACKEND_URL}/auth/register", json=test_user1)
        if response.status_code != 200:
            print(f"❌ Registration failed: {response.status_code} - {response.text}")
            return False
        
        user1_data = response.json()
        user1_token = user1_data["access_token"]
        user1_id = user1_data["user"]["id"]
        print(f"✅ User 1 registered successfully: {user1_id}")
        
        # Step 2: Register second user for connection testing
        print("\n2️⃣ Registering second user...")
        response = requests.post(f"{BACKEND_URL}/auth/register", json=test_user2)
        if response.status_code != 200:
            print(f"❌ Registration failed: {response.status_code} - {response.text}")
            return False
            
        user2_data = response.json()
        user2_token = user2_data["access_token"]
        user2_id = user2_data["user"]["id"]
        print(f"✅ User 2 registered successfully: {user2_id}")
        
        # Step 3: Test login for user 1
        print("\n3️⃣ Testing login...")
        login_data = {"phone_number": test_user1["phone_number"], "password": test_user1["password"]}
        response = requests.post(f"{BACKEND_URL}/auth/login", json=login_data)
        if response.status_code != 200:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return False
        
        login_response = response.json()
        token = login_response["access_token"]
        print(f"✅ Login successful, token received")
        
        # Step 4: POST location with address fields
        print("\n4️⃣ Posting location with address fields...")
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{BACKEND_URL}/locations", json=test_location, headers=headers)
        if response.status_code != 200:
            print(f"❌ Location update failed: {response.status_code} - {response.text}")
            return False
        
        location_response = response.json()
        location_id = location_response["id"]
        print(f"✅ Location posted successfully: {location_id}")
        print(f"   📍 Coordinates: {test_location['latitude']}, {test_location['longitude']}")
        print(f"   🏠 Address: {test_location['address']}")
        print(f"   🛣️  Street: {test_location['street']}")
        print(f"   🏙️  City: {test_location['city']}")
        print(f"   🌍 Country: {test_location['country']}")
        
        # Step 5: GET location back and verify address fields
        print("\n5️⃣ Getting location back to verify address fields...")
        response = requests.get(f"{BACKEND_URL}/locations/{user1_id}", headers=headers)
        if response.status_code != 200:
            print(f"❌ Get location failed: {response.status_code} - {response.text}")
            return False
        
        retrieved_location = response.json()
        print(f"✅ Location retrieved successfully")
        print(f"   Retrieved data: {json.dumps(retrieved_location, indent=2)}")
        
        # Check if address fields are present
        address_fields = ["address", "street", "city", "country"]
        missing_fields = []
        for field in address_fields:
            if field not in retrieved_location:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ CRITICAL BUG: Address fields missing from GET response: {missing_fields}")
            print(f"   Expected fields: {address_fields}")
            print(f"   Actual fields: {list(retrieved_location.keys())}")
            return False
        
        # Verify address field values
        for field in address_fields:
            expected_value = test_location[field]
            actual_value = retrieved_location.get(field)
            if actual_value != expected_value:
                print(f"❌ Address field mismatch for '{field}': expected '{expected_value}', got '{actual_value}'")
                return False
        
        print(f"✅ All address fields verified correctly")
        
        # Step 6: Test connection between users and verify address data visibility
        print("\n6️⃣ Testing connection and address data visibility...")
        
        # Send connection request from user2 to user1
        connection_request = {"target_phone": test_user1["phone_number"]}
        headers2 = {"Authorization": f"Bearer {user2_token}"}
        response = requests.post(f"{BACKEND_URL}/connections/request", json=connection_request, headers=headers2)
        if response.status_code != 200:
            print(f"❌ Connection request failed: {response.status_code} - {response.text}")
            return False
        
        print(f"✅ Connection request sent from user2 to user1")
        
        # Get pending requests for user1
        response = requests.get(f"{BACKEND_URL}/connections/pending", headers=headers)
        if response.status_code != 200:
            print(f"❌ Get pending requests failed: {response.status_code} - {response.text}")
            return False
        
        pending_requests = response.json()
        if not pending_requests:
            print(f"❌ No pending requests found")
            return False
        
        connection_id = pending_requests[0]["id"]
        print(f"✅ Pending request found: {connection_id}")
        
        # Accept connection request
        response = requests.post(f"{BACKEND_URL}/connections/{connection_id}/accept", headers=headers)
        if response.status_code != 200:
            print(f"❌ Accept connection failed: {response.status_code} - {response.text}")
            return False
        
        print(f"✅ Connection accepted")
        
        # Now user2 should be able to see user1's location with address data
        response = requests.get(f"{BACKEND_URL}/locations/{user1_id}", headers=headers2)
        if response.status_code != 200:
            print(f"❌ User2 cannot access user1's location: {response.status_code} - {response.text}")
            return False
        
        connected_user_location = response.json()
        print(f"✅ User2 can access user1's location")
        print(f"   Retrieved data: {json.dumps(connected_user_location, indent=2)}")
        
        # Check if address fields are present for connected user
        missing_fields_connected = []
        for field in address_fields:
            if field not in connected_user_location:
                missing_fields_connected.append(field)
        
        if missing_fields_connected:
            print(f"❌ CRITICAL BUG: Address fields missing from connected user's location: {missing_fields_connected}")
            return False
        
        print(f"✅ Connected user can see all address fields")
        
        # Step 7: Test location history endpoint
        print("\n7️⃣ Testing location history with address fields...")
        response = requests.get(f"{BACKEND_URL}/locations/history/{user1_id}", headers=headers2)
        if response.status_code != 200:
            print(f"❌ Get location history failed: {response.status_code} - {response.text}")
            return False
        
        location_history = response.json()
        print(f"✅ Location history retrieved: {len(location_history)} entries")
        
        if location_history:
            first_location = location_history[0]
            print(f"   First location: {json.dumps(first_location, indent=2)}")
            
            # Check if address fields are present in history
            missing_fields_history = []
            for field in address_fields:
                if field not in first_location:
                    missing_fields_history.append(field)
            
            if missing_fields_history:
                print(f"❌ CRITICAL BUG: Address fields missing from location history: {missing_fields_history}")
                return False
            
            print(f"✅ Location history includes all address fields")
        
        print("\n🎉 All tests passed successfully!")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_location_without_address_fields():
    """Test that location endpoint still works without optional address fields"""
    
    print("\n🧪 Testing Location Without Address Fields")
    print("=" * 50)
    
    import time
    timestamp = str(int(time.time()))
    test_user = {
        "phone_number": f"+123456{timestamp}3",
        "password": "testpass123", 
        "name": "Test User 3"
    }
    
    basic_location = {
        "latitude": 40.7128,
        "longitude": -74.0060
    }
    
    try:
        # Register user
        print("\n1️⃣ Registering user...")
        response = requests.post(f"{BACKEND_URL}/auth/register", json=test_user)
        if response.status_code != 200:
            print(f"❌ Registration failed: {response.status_code} - {response.text}")
            return False
        
        user_data = response.json()
        token = user_data["access_token"]
        user_id = user_data["user"]["id"]
        print(f"✅ User registered successfully: {user_id}")
        
        # Post location without address fields
        print("\n2️⃣ Posting location without address fields...")
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{BACKEND_URL}/locations", json=basic_location, headers=headers)
        if response.status_code != 200:
            print(f"❌ Location update failed: {response.status_code} - {response.text}")
            return False
        
        print(f"✅ Location posted successfully without address fields")
        
        # Get location back
        response = requests.get(f"{BACKEND_URL}/locations/{user_id}", headers=headers)
        if response.status_code != 200:
            print(f"❌ Get location failed: {response.status_code} - {response.text}")
            return False
        
        retrieved_location = response.json()
        print(f"✅ Location retrieved successfully")
        print(f"   Retrieved data: {json.dumps(retrieved_location, indent=2)}")
        
        # Verify coordinates are correct
        if (retrieved_location.get("latitude") != basic_location["latitude"] or 
            retrieved_location.get("longitude") != basic_location["longitude"]):
            print(f"❌ Coordinate mismatch")
            return False
        
        print(f"✅ Coordinates verified correctly")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Location Address Fields Testing")
    print(f"Backend URL: {BACKEND_URL}")
    
    # Run tests
    test1_passed = test_location_address_fields()
    test2_passed = test_location_without_address_fields()
    
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Location with address fields: {'PASSED' if test1_passed else 'FAILED'}")
    print(f"✅ Location without address fields: {'PASSED' if test2_passed else 'FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED!")
        sys.exit(1)