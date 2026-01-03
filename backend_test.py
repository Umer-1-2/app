import requests
import sys
import json
from datetime import datetime, timedelta
import time

class AttendanceAPITester:
    def __init__(self, base_url="https://workshift-27.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.employee_token = None
        self.employer_token = None
        self.employee_user = None
        self.employer_user = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
            self.failed_tests.append({"test": name, "error": details})

    def make_request(self, method, endpoint, data=None, token=None, expected_status=200):
        """Make HTTP request with error handling"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)

            success = response.status_code == expected_status
            return success, response.status_code, response.json() if response.content else {}

        except requests.exceptions.RequestException as e:
            return False, 0, {"error": str(e)}
        except json.JSONDecodeError:
            return False, response.status_code, {"error": "Invalid JSON response"}

    def test_user_registration(self):
        """Test user registration for both employee and employer"""
        timestamp = int(time.time())
        
        # Test employee registration
        employee_data = {
            "email": f"employee_{timestamp}@test.com",
            "password": "TestPass123!",
            "name": f"Test Employee {timestamp}",
            "role": "employee"
        }
        
        success, status, response = self.make_request('POST', 'auth/register', employee_data, expected_status=200)
        
        if success and 'token' in response and 'user' in response:
            self.employee_token = response['token']
            self.employee_user = response['user']
            self.log_test("Employee Registration", True)
        else:
            self.log_test("Employee Registration", False, f"Status: {status}, Response: {response}")
            return False

        # Test employer registration
        employer_data = {
            "email": f"employer_{timestamp}@test.com",
            "password": "TestPass123!",
            "name": f"Test Employer {timestamp}",
            "role": "employer"
        }
        
        success, status, response = self.make_request('POST', 'auth/register', employer_data, expected_status=200)
        
        if success and 'token' in response and 'user' in response:
            self.employer_token = response['token']
            self.employer_user = response['user']
            self.log_test("Employer Registration", True)
            return True
        else:
            self.log_test("Employer Registration", False, f"Status: {status}, Response: {response}")
            return False

    def test_user_login(self):
        """Test user login functionality"""
        if not self.employee_user:
            self.log_test("Employee Login", False, "No employee user to test login")
            return False

        login_data = {
            "email": self.employee_user['email'],
            "password": "TestPass123!"
        }
        
        success, status, response = self.make_request('POST', 'auth/login', login_data, expected_status=200)
        
        if success and 'token' in response:
            self.log_test("Employee Login", True)
            return True
        else:
            self.log_test("Employee Login", False, f"Status: {status}, Response: {response}")
            return False

    def test_punch_in(self):
        """Test employee punch in functionality"""
        if not self.employee_token:
            self.log_test("Punch In", False, "No employee token available")
            return False

        success, status, response = self.make_request('POST', 'attendance/punch-in', {}, self.employee_token, expected_status=200)
        
        if success and 'message' in response and 'punch_in_time' in response:
            self.log_test("Punch In", True)
            return True
        else:
            self.log_test("Punch In", False, f"Status: {status}, Response: {response}")
            return False

    def test_today_status(self):
        """Test getting today's attendance status"""
        if not self.employee_token:
            self.log_test("Today Status", False, "No employee token available")
            return False

        success, status, response = self.make_request('GET', 'attendance/today-status', token=self.employee_token, expected_status=200)
        
        if success and 'has_attendance' in response:
            self.log_test("Today Status", True)
            return True
        else:
            self.log_test("Today Status", False, f"Status: {status}, Response: {response}")
            return False

    def test_start_break(self):
        """Test starting a break"""
        if not self.employee_token:
            self.log_test("Start Break", False, "No employee token available")
            return False

        success, status, response = self.make_request('POST', 'attendance/start-break', {}, self.employee_token, expected_status=200)
        
        if success and 'message' in response and 'break_start_time' in response:
            self.log_test("Start Break", True)
            return True
        else:
            self.log_test("Start Break", False, f"Status: {status}, Response: {response}")
            return False

    def test_end_break(self):
        """Test ending a break"""
        if not self.employee_token:
            self.log_test("End Break", False, "No employee token available")
            return False

        success, status, response = self.make_request('POST', 'attendance/end-break', {}, self.employee_token, expected_status=200)
        
        if success and 'message' in response and 'break_end_time' in response:
            self.log_test("End Break", True)
            return True
        else:
            self.log_test("End Break", False, f"Status: {status}, Response: {response}")
            return False

    def test_punch_out(self):
        """Test employee punch out functionality"""
        if not self.employee_token:
            self.log_test("Punch Out", False, "No employee token available")
            return False

        success, status, response = self.make_request('POST', 'attendance/punch-out', {}, self.employee_token, expected_status=200)
        
        if success and 'message' in response and 'total_hours' in response:
            self.log_test("Punch Out", True)
            return True
        else:
            self.log_test("Punch Out", False, f"Status: {status}, Response: {response}")
            return False

    def test_attendance_history(self):
        """Test getting attendance history"""
        if not self.employee_token:
            self.log_test("Attendance History", False, "No employee token available")
            return False

        success, status, response = self.make_request('GET', 'attendance/my-history', token=self.employee_token, expected_status=200)
        
        if success and isinstance(response, list):
            self.log_test("Attendance History", True)
            return True
        else:
            self.log_test("Attendance History", False, f"Status: {status}, Response: {response}")
            return False

    def test_monthly_report(self):
        """Test employer monthly report functionality"""
        if not self.employer_token:
            self.log_test("Monthly Report", False, "No employer token available")
            return False

        current_date = datetime.now()
        report_data = {
            "year": current_date.year,
            "month": current_date.month
        }

        success, status, response = self.make_request('POST', 'attendance/monthly-report', report_data, self.employer_token, expected_status=200)
        
        if success and isinstance(response, list):
            self.log_test("Monthly Report", True)
            return True
        else:
            self.log_test("Monthly Report", False, f"Status: {status}, Response: {response}")
            return False

    def test_role_permissions(self):
        """Test that employees can't access employer endpoints"""
        if not self.employee_token:
            self.log_test("Role Permissions", False, "No employee token available")
            return False

        # Employee should not be able to access monthly report
        report_data = {"year": 2025, "month": 1}
        success, status, response = self.make_request('POST', 'attendance/monthly-report', report_data, self.employee_token, expected_status=403)
        
        if success:
            self.log_test("Role Permissions (Employee blocked from employer endpoint)", True)
            return True
        else:
            self.log_test("Role Permissions", False, f"Employee was able to access employer endpoint. Status: {status}")
            return False

    def test_duplicate_registration(self):
        """Test that duplicate email registration is prevented"""
        if not self.employee_user:
            self.log_test("Duplicate Registration Prevention", False, "No employee user to test duplicate")
            return False

        duplicate_data = {
            "email": self.employee_user['email'],
            "password": "AnotherPass123!",
            "name": "Duplicate User",
            "role": "employee"
        }
        
        success, status, response = self.make_request('POST', 'auth/register', duplicate_data, expected_status=400)
        
        if success:
            self.log_test("Duplicate Registration Prevention", True)
            return True
        else:
            self.log_test("Duplicate Registration Prevention", False, f"Duplicate registration was allowed. Status: {status}")
            return False

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting Attendance API Tests...")
        print(f"Testing against: {self.base_url}")
        print("=" * 60)

        # Test user registration and authentication
        if not self.test_user_registration():
            print("❌ Registration failed - stopping tests")
            return self.get_results()

        self.test_user_login()
        self.test_duplicate_registration()

        # Test attendance workflow
        self.test_punch_in()
        self.test_today_status()
        self.test_start_break()
        
        # Wait a moment for break to register
        time.sleep(1)
        
        self.test_end_break()
        self.test_punch_out()
        self.test_attendance_history()

        # Test employer functionality
        self.test_monthly_report()
        self.test_role_permissions()

        return self.get_results()

    def get_results(self):
        """Get test results summary"""
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.failed_tests:
            print("\n❌ Failed Tests:")
            for test in self.failed_tests:
                print(f"  - {test['test']}: {test['error']}")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"\n✨ Success Rate: {success_rate:.1f}%")
        
        return {
            "total_tests": self.tests_run,
            "passed_tests": self.tests_passed,
            "failed_tests": self.failed_tests,
            "success_rate": success_rate
        }

def main():
    tester = AttendanceAPITester()
    results = tester.run_all_tests()
    
    # Return appropriate exit code
    return 0 if results["success_rate"] >= 80 else 1

if __name__ == "__main__":
    sys.exit(main())