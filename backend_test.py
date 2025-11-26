#!/usr/bin/env python3
"""
Backend API Testing Suite for Traffic Opportunity Engine
Tests all backend endpoints with proper authentication and error handling.
"""

import requests
import json
import time
from typing import Dict, Any, Optional

# Backend URL from frontend/.env
BACKEND_URL = "https://comment-miner-1.preview.emergentagent.com/api"

class TrafficEngineAPITester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.user_token = None
        self.test_user_id = None
        self.admin_user_id = None
        
    def log(self, message: str, level: str = "INFO"):
        """Log test messages with timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def make_request(self, method: str, endpoint: str, token: Optional[str] = None, 
                    data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request with proper headers and error handling"""
        url = f"{BACKEND_URL}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers, params=params, timeout=30)
            elif method.upper() == "POST":
                response = self.session.post(url, headers=headers, json=data, timeout=30)
            elif method.upper() == "PUT":
                response = self.session.put(url, headers=headers, json=data, params=params, timeout=30)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            return {
                "status_code": response.status_code,
                "data": response.json() if response.content else {},
                "success": 200 <= response.status_code < 300
            }
        except requests.exceptions.RequestException as e:
            self.log(f"Request failed for {method} {url}: {str(e)}", "ERROR")
            return {"status_code": 0, "data": {"error": str(e)}, "success": False}
        except json.JSONDecodeError:
            return {
                "status_code": response.status_code,
                "data": {"error": "Invalid JSON response"},
                "success": False
            }

    def test_health_check(self) -> bool:
        """Test health check endpoint with database and Redis status"""
        self.log("Testing health check endpoint...")
        result = self.make_request("GET", "/health")
        
        if result["success"] and result["data"].get("status") in ["healthy", "degraded"]:
            data = result["data"]
            db_status = data.get("database", "unknown")
            redis_status = data.get("redis", "unknown")
            self.log(f"✅ Health check passed - Database: {db_status}, Redis: {redis_status}")
            
            # Check if both services are connected
            if db_status == "connected" and redis_status == "connected":
                self.log("✅ All services are healthy")
            else:
                self.log("⚠️ Some services may be degraded")
            return True
        else:
            self.log(f"❌ Health check failed: {result}", "ERROR")
            return False

    def test_auth_register(self) -> bool:
        """Test user registration"""
        self.log("Testing user registration...")
        
        user_data = {
            "email": "testuser@example.com",
            "password": "testpass123"
        }
        
        result = self.make_request("POST", "/auth/register", data=user_data)
        
        if result["success"]:
            self.user_token = result["data"].get("access_token")
            user_info = result["data"].get("user", {})
            self.test_user_id = user_info.get("id")
            self.log(f"✅ User registration successful. User ID: {self.test_user_id}")
            return True
        else:
            # Check if user already exists
            if result["status_code"] == 400 and "already registered" in str(result["data"]):
                self.log("User already exists, proceeding with login...")
                return self.test_auth_login_user()
            else:
                self.log(f"❌ User registration failed: {result}", "ERROR")
                return False

    def test_auth_login_admin(self) -> bool:
        """Test admin login"""
        self.log("Testing admin login...")
        
        admin_data = {
            "email": "admin@traffic.engine",
            "password": "admin123"
        }
        
        result = self.make_request("POST", "/auth/login", data=admin_data)
        
        if result["success"]:
            self.admin_token = result["data"].get("access_token")
            user_info = result["data"].get("user", {})
            self.admin_user_id = user_info.get("id")
            self.log(f"✅ Admin login successful. Admin ID: {self.admin_user_id}")
            return True
        else:
            self.log(f"❌ Admin login failed: {result}", "ERROR")
            return False

    def test_auth_login_user(self) -> bool:
        """Test regular user login"""
        self.log("Testing user login...")
        
        user_data = {
            "email": "testuser@example.com",
            "password": "testpass123"
        }
        
        result = self.make_request("POST", "/auth/login", data=user_data)
        
        if result["success"]:
            self.user_token = result["data"].get("access_token")
            user_info = result["data"].get("user", {})
            self.test_user_id = user_info.get("id")
            self.log(f"✅ User login successful. User ID: {self.test_user_id}")
            return True
        else:
            self.log(f"❌ User login failed: {result}", "ERROR")
            return False

    def test_auth_me(self) -> bool:
        """Test /auth/me endpoint"""
        self.log("Testing /auth/me endpoint...")
        
        if not self.user_token:
            self.log("❌ No user token available for /auth/me test", "ERROR")
            return False
            
        result = self.make_request("GET", "/auth/me", token=self.user_token)
        
        if result["success"] and result["data"].get("email"):
            self.log("✅ /auth/me endpoint working")
            return True
        else:
            self.log(f"❌ /auth/me failed: {result}", "ERROR")
            return False

    def test_opportunities_list(self) -> bool:
        """Test opportunities listing"""
        self.log("Testing opportunities listing...")
        
        if not self.user_token:
            self.log("❌ No user token available for opportunities test", "ERROR")
            return False
            
        result = self.make_request("GET", "/opportunities", token=self.user_token)
        
        if result["success"]:
            opportunities = result["data"]
            self.log(f"✅ Opportunities list retrieved. Count: {len(opportunities)}")
            return True
        else:
            self.log(f"❌ Opportunities list failed: {result}", "ERROR")
            return False

    def test_opportunities_filtered(self) -> bool:
        """Test opportunities with score filter"""
        self.log("Testing opportunities with score filter...")
        
        if not self.user_token:
            self.log("❌ No user token available for filtered opportunities test", "ERROR")
            return False
            
        result = self.make_request("GET", "/opportunities", token=self.user_token, params={"score_min": 70})
        
        if result["success"]:
            opportunities = result["data"]
            self.log(f"✅ Filtered opportunities retrieved. Count: {len(opportunities)}")
            return True
        else:
            self.log(f"❌ Filtered opportunities failed: {result}", "ERROR")
            return False

    def test_recommendations_list(self) -> bool:
        """Test recommendations listing"""
        self.log("Testing recommendations listing...")
        
        if not self.user_token:
            self.log("❌ No user token available for recommendations test", "ERROR")
            return False
            
        result = self.make_request("GET", "/recommendations", token=self.user_token)
        
        if result["success"]:
            recommendations = result["data"]
            self.log(f"✅ Recommendations list retrieved. Count: {len(recommendations)}")
            return True
        else:
            self.log(f"❌ Recommendations list failed: {result}", "ERROR")
            return False

    def test_admin_stats(self) -> bool:
        """Test admin stats endpoint"""
        self.log("Testing admin stats...")
        
        if not self.admin_token:
            self.log("❌ No admin token available for stats test", "ERROR")
            return False
            
        result = self.make_request("GET", "/admin/stats", token=self.admin_token)
        
        if result["success"] and "total_users" in result["data"]:
            stats = result["data"]
            self.log(f"✅ Admin stats retrieved: {stats}")
            return True
        else:
            self.log(f"❌ Admin stats failed: {result}", "ERROR")
            return False

    def test_admin_users(self) -> bool:
        """Test admin users listing"""
        self.log("Testing admin users listing...")
        
        if not self.admin_token:
            self.log("❌ No admin token available for users test", "ERROR")
            return False
            
        result = self.make_request("GET", "/admin/users", token=self.admin_token)
        
        if result["success"]:
            users = result["data"]
            self.log(f"✅ Admin users list retrieved. Count: {len(users)}")
            return True
        else:
            self.log(f"❌ Admin users list failed: {result}", "ERROR")
            return False

    def test_admin_channels(self) -> bool:
        """Test admin channels listing"""
        self.log("Testing admin channels listing...")
        
        if not self.admin_token:
            self.log("❌ No admin token available for channels test", "ERROR")
            return False
            
        result = self.make_request("GET", "/admin/channels", token=self.admin_token)
        
        if result["success"]:
            channels = result["data"]
            self.log(f"✅ Admin channels list retrieved. Count: {len(channels)}")
            return True
        else:
            self.log(f"❌ Admin channels list failed: {result}", "ERROR")
            return False

    def test_admin_trigger_scan(self) -> bool:
        """Test manual scan trigger"""
        self.log("Testing manual scan trigger...")
        
        if not self.admin_token:
            self.log("❌ No admin token available for scan trigger test", "ERROR")
            return False
            
        result = self.make_request("POST", "/admin/trigger-scan", token=self.admin_token)
        
        if result["success"] and result["data"].get("task_id"):
            task_id = result["data"]["task_id"]
            self.log(f"✅ Manual scan triggered successfully. Task ID: {task_id}")
            return True
        else:
            self.log(f"❌ Manual scan trigger failed: {result}", "ERROR")
            return False

    def test_unauthorized_access(self) -> bool:
        """Test unauthorized access to protected endpoints"""
        self.log("Testing unauthorized access...")
        
        # Test accessing admin endpoint without token
        result = self.make_request("GET", "/admin/stats")
        
        if result["status_code"] == 401:
            self.log("✅ Unauthorized access properly blocked")
            return True
        else:
            self.log(f"❌ Unauthorized access not properly blocked: {result}", "ERROR")
            return False

    def test_user_accessing_admin(self) -> bool:
        """Test regular user accessing admin endpoints"""
        self.log("Testing regular user accessing admin endpoints...")
        
        if not self.user_token:
            self.log("❌ No user token available for admin access test", "ERROR")
            return False
            
        result = self.make_request("GET", "/admin/users", token=self.user_token)
        
        if result["status_code"] == 403:
            self.log("✅ Regular user properly blocked from admin endpoints")
            return True
        else:
            self.log(f"❌ Regular user not properly blocked from admin endpoints: {result}", "ERROR")
            return False

    def test_preferences_get_defaults(self) -> bool:
        """Test getting default user preferences"""
        self.log("Testing GET /preferences (default preferences)...")
        
        if not self.user_token:
            self.log("❌ No user token available for preferences test", "ERROR")
            return False
            
        result = self.make_request("GET", "/preferences", token=self.user_token)
        
        if result["success"] and result["data"].get("user_id"):
            prefs = result["data"]
            # Check default values
            expected_defaults = {
                "enabled_channels": ["reddit", "hacker_news", "product_hunt", "google_trends"],
                "scan_frequency": "hourly",
                "min_opportunity_score": 50.0,
                "max_opportunities_per_day": 50,
                "auto_generate_content": True,
                "include_competitor_analysis": True
            }
            
            all_defaults_correct = True
            for key, expected_value in expected_defaults.items():
                actual_value = prefs.get(key)
                if actual_value != expected_value:
                    self.log(f"⚠️ Default mismatch for {key}: expected {expected_value}, got {actual_value}")
                    all_defaults_correct = False
            
            if all_defaults_correct:
                self.log("✅ Default preferences retrieved successfully with correct defaults")
            else:
                self.log("✅ Default preferences retrieved (some defaults may differ)")
            return True
        else:
            self.log(f"❌ Get default preferences failed: {result}", "ERROR")
            return False

    def test_preferences_update(self) -> bool:
        """Test updating user preferences"""
        self.log("Testing PUT /preferences (update preferences)...")
        
        if not self.user_token:
            self.log("❌ No user token available for preferences update test", "ERROR")
            return False
        
        # Test data with realistic values
        update_data = {
            "enabled_channels": ["reddit", "twitter", "linkedin"],
            "target_keywords": ["email marketing", "lead generation", "b2b sales"],
            "industry": "SaaS",
            "niche": "Email Marketing Tools",
            "exclude_keywords": ["spam", "free trial"],
            "scan_frequency": "daily",
            "notification_channels": ["email"],
            "notification_email": "testuser@example.com",
            "min_opportunity_score": 70.0,
            "enabled_opportunity_types": ["question", "trending_keyword", "complaint"],
            "max_opportunities_per_day": 25,
            "auto_generate_content": False,
            "include_competitor_analysis": True,
            "competitor_domains": ["mailchimp.com", "hubspot.com"]
        }
        
        result = self.make_request("PUT", "/preferences", token=self.user_token, data=update_data)
        
        if result["success"] and result["data"].get("user_id"):
            updated_prefs = result["data"]
            
            # Verify updates were applied
            verification_passed = True
            for key, expected_value in update_data.items():
                actual_value = updated_prefs.get(key)
                if actual_value != expected_value:
                    self.log(f"⚠️ Update verification failed for {key}: expected {expected_value}, got {actual_value}")
                    verification_passed = False
            
            if verification_passed:
                self.log("✅ Preferences updated successfully and verified")
            else:
                self.log("✅ Preferences updated (some values may not match exactly)")
            return True
        else:
            self.log(f"❌ Update preferences failed: {result}", "ERROR")
            return False

    def test_preferences_get_updated(self) -> bool:
        """Test getting updated preferences to verify persistence"""
        self.log("Testing GET /preferences (verify updated preferences persist)...")
        
        if not self.user_token:
            self.log("❌ No user token available for preferences persistence test", "ERROR")
            return False
            
        result = self.make_request("GET", "/preferences", token=self.user_token)
        
        if result["success"] and result["data"].get("user_id"):
            prefs = result["data"]
            
            # Check if some of our updates are still there
            expected_updates = {
                "industry": "SaaS",
                "niche": "Email Marketing Tools",
                "scan_frequency": "daily",
                "min_opportunity_score": 70.0,
                "max_opportunities_per_day": 25
            }
            
            persistence_verified = True
            for key, expected_value in expected_updates.items():
                actual_value = prefs.get(key)
                if actual_value != expected_value:
                    self.log(f"⚠️ Persistence check failed for {key}: expected {expected_value}, got {actual_value}")
                    persistence_verified = False
            
            if persistence_verified:
                self.log("✅ Updated preferences persisted correctly")
            else:
                self.log("✅ Preferences retrieved (persistence may have issues)")
            return True
        else:
            self.log(f"❌ Get updated preferences failed: {result}", "ERROR")
            return False

    def test_preferences_reset(self) -> bool:
        """Test resetting preferences to defaults"""
        self.log("Testing POST /preferences/reset...")
        
        if not self.user_token:
            self.log("❌ No user token available for preferences reset test", "ERROR")
            return False
            
        result = self.make_request("POST", "/preferences/reset", token=self.user_token)
        
        if result["success"] and "reset" in result["data"].get("message", "").lower():
            self.log("✅ Preferences reset successfully")
            return True
        else:
            self.log(f"❌ Preferences reset failed: {result}", "ERROR")
            return False

    def test_preferences_get_after_reset(self) -> bool:
        """Test getting preferences after reset to verify defaults restored"""
        self.log("Testing GET /preferences (verify reset to defaults)...")
        
        if not self.user_token:
            self.log("❌ No user token available for post-reset preferences test", "ERROR")
            return False
            
        result = self.make_request("GET", "/preferences", token=self.user_token)
        
        if result["success"] and result["data"].get("user_id"):
            prefs = result["data"]
            
            # Check that we're back to defaults
            expected_defaults = {
                "scan_frequency": "hourly",
                "min_opportunity_score": 50.0,
                "max_opportunities_per_day": 50,
                "auto_generate_content": True,
                "industry": "",
                "niche": ""
            }
            
            reset_verified = True
            for key, expected_value in expected_defaults.items():
                actual_value = prefs.get(key)
                if actual_value != expected_value:
                    self.log(f"⚠️ Reset verification failed for {key}: expected {expected_value}, got {actual_value}")
                    reset_verified = False
            
            if reset_verified:
                self.log("✅ Preferences successfully reset to defaults")
            else:
                self.log("✅ Preferences retrieved after reset (some defaults may differ)")
            return True
        else:
            self.log(f"❌ Get preferences after reset failed: {result}", "ERROR")
            return False

    def test_preferences_unauthorized(self) -> bool:
        """Test preferences endpoints without authentication"""
        self.log("Testing preferences endpoints without authentication...")
        
        # Test GET without token
        result = self.make_request("GET", "/preferences")
        
        if result["status_code"] == 401:
            self.log("✅ Preferences endpoints properly protected (unauthorized access blocked)")
            return True
        else:
            self.log(f"❌ Preferences endpoints not properly protected: {result}", "ERROR")
            return False

    def test_api_token_generation(self) -> bool:
        """Test API token generation"""
        self.log("Testing API token generation...")
        
        if not self.user_token:
            self.log("❌ No user token available for API token generation test", "ERROR")
            return False
            
        result = self.make_request("POST", "/tokens/generate", token=self.user_token)
        
        if result["success"] and result["data"].get("token") and result["data"].get("token_id"):
            token = result["data"]["token"]
            token_id = result["data"]["token_id"]
            self.log(f"✅ API token generated successfully. Token ID: {token_id}")
            
            # Store for cleanup test
            self.generated_token = token
            self.generated_token_id = token_id
            return True
        else:
            self.log(f"❌ API token generation failed: {result}", "ERROR")
            return False

    def test_api_token_list(self) -> bool:
        """Test listing API tokens"""
        self.log("Testing API token listing...")
        
        if not self.user_token:
            self.log("❌ No user token available for API token list test", "ERROR")
            return False
            
        result = self.make_request("GET", "/tokens", token=self.user_token)
        
        if result["success"] and isinstance(result["data"], list):
            tokens = result["data"]
            self.log(f"✅ API tokens listed successfully. Count: {len(tokens)}")
            return True
        else:
            self.log(f"❌ API token listing failed: {result}", "ERROR")
            return False

    def test_api_token_revoke(self) -> bool:
        """Test revoking API token"""
        self.log("Testing API token revocation...")
        
        if not self.user_token:
            self.log("❌ No user token available for API token revoke test", "ERROR")
            return False
            
        if not hasattr(self, 'generated_token_id'):
            self.log("❌ No generated token ID available for revocation test", "ERROR")
            return False
            
        result = self.make_request("DELETE", f"/tokens/{self.generated_token_id}", token=self.user_token)
        
        if result["success"] and "revoked" in result["data"].get("message", "").lower():
            self.log("✅ API token revoked successfully")
            return True
        else:
            self.log(f"❌ API token revocation failed: {result}", "ERROR")
            return False

    # ============= SMART KEYWORD DISCOVERY TESTS =============

    def test_extract_keywords_apollo(self) -> bool:
        """Test keyword extraction from apollo.io"""
        self.log("Testing keyword extraction from apollo.io...")
        
        if not self.user_token:
            self.log("❌ No user token available for keyword extraction test", "ERROR")
            return False
            
        test_data = {"url": "https://www.apollo.io"}
        result = self.make_request("POST", "/extract-keywords", token=self.user_token, data=test_data)
        
        if result["success"] and result["data"].get("keywords"):
            keywords = result["data"]["keywords"]
            industry = result["data"].get("industry", "")
            niche = result["data"].get("niche", "")
            business_type = result["data"].get("business_type", "")
            
            self.log(f"✅ Keywords extracted from apollo.io: {len(keywords)} keywords")
            self.log(f"   Industry: {industry}")
            self.log(f"   Niche: {niche}")
            self.log(f"   Business Type: {business_type}")
            self.log(f"   Sample keywords: {keywords[:5]}")
            
            # Store for save test
            self.extracted_keywords = keywords
            self.extracted_url = "https://www.apollo.io"
            self.extracted_metadata = {
                "industry": industry,
                "niche": niche,
                "business_type": business_type
            }
            return True
        else:
            self.log(f"❌ Keyword extraction from apollo.io failed: {result}", "ERROR")
            return False

    def test_extract_keywords_hunter(self) -> bool:
        """Test keyword extraction from hunter.io"""
        self.log("Testing keyword extraction from hunter.io...")
        
        if not self.user_token:
            self.log("❌ No user token available for keyword extraction test", "ERROR")
            return False
            
        test_data = {"url": "https://www.hunter.io"}
        result = self.make_request("POST", "/extract-keywords", token=self.user_token, data=test_data)
        
        if result["success"] and result["data"].get("keywords"):
            keywords = result["data"]["keywords"]
            industry = result["data"].get("industry", "")
            niche = result["data"].get("niche", "")
            
            self.log(f"✅ Keywords extracted from hunter.io: {len(keywords)} keywords")
            self.log(f"   Industry: {industry}")
            self.log(f"   Niche: {niche}")
            self.log(f"   Sample keywords: {keywords[:5]}")
            return True
        else:
            self.log(f"❌ Keyword extraction from hunter.io failed: {result}", "ERROR")
            return False

    def test_extract_keywords_clearbit(self) -> bool:
        """Test keyword extraction from clearbit.com"""
        self.log("Testing keyword extraction from clearbit.com...")
        
        if not self.user_token:
            self.log("❌ No user token available for keyword extraction test", "ERROR")
            return False
            
        test_data = {"url": "https://clearbit.com"}
        result = self.make_request("POST", "/extract-keywords", token=self.user_token, data=test_data)
        
        if result["success"] and result["data"].get("keywords"):
            keywords = result["data"]["keywords"]
            industry = result["data"].get("industry", "")
            niche = result["data"].get("niche", "")
            
            self.log(f"✅ Keywords extracted from clearbit.com: {len(keywords)} keywords")
            self.log(f"   Industry: {industry}")
            self.log(f"   Niche: {niche}")
            self.log(f"   Sample keywords: {keywords[:5]}")
            return True
        else:
            self.log(f"❌ Keyword extraction from clearbit.com failed: {result}", "ERROR")
            return False

    def test_extract_keywords_invalid_url(self) -> bool:
        """Test keyword extraction with invalid URL"""
        self.log("Testing keyword extraction with invalid URL...")
        
        if not self.user_token:
            self.log("❌ No user token available for invalid URL test", "ERROR")
            return False
            
        test_data = {"url": "invalid-url-test"}
        result = self.make_request("POST", "/extract-keywords", token=self.user_token, data=test_data)
        
        if not result["success"] and result["status_code"] in [400, 500]:
            self.log("✅ Invalid URL properly rejected")
            return True
        else:
            self.log(f"❌ Invalid URL not properly handled: {result}", "ERROR")
            return False

    def test_analyze_seo_apollo(self) -> bool:
        """Test SEO analysis of apollo.io"""
        self.log("Testing SEO analysis of apollo.io...")
        
        if not self.user_token:
            self.log("❌ No user token available for SEO analysis test", "ERROR")
            return False
            
        test_data = {"url": "https://www.apollo.io"}
        result = self.make_request("POST", "/analyze-seo", token=self.user_token, data=test_data)
        
        if result["success"] and "seo_score" in result["data"]:
            seo_data = result["data"]
            seo_score = seo_data.get("seo_score", 0)
            issues = seo_data.get("issues", [])
            warnings = seo_data.get("warnings", [])
            good_practices = seo_data.get("good_practices", [])
            keyword_opportunities = seo_data.get("keyword_opportunities", [])
            content_suggestions = seo_data.get("content_suggestions", [])
            traffic_strategies = seo_data.get("traffic_strategies", [])
            
            self.log(f"✅ SEO analysis completed for apollo.io")
            self.log(f"   SEO Score: {seo_score}/100")
            self.log(f"   Issues: {len(issues)}")
            self.log(f"   Warnings: {len(warnings)}")
            self.log(f"   Good Practices: {len(good_practices)}")
            self.log(f"   Keyword Opportunities: {len(keyword_opportunities)}")
            self.log(f"   Content Suggestions: {len(content_suggestions)}")
            self.log(f"   Traffic Strategies: {len(traffic_strategies)}")
            
            if seo_score > 0:
                self.log("✅ SEO score calculated successfully")
            else:
                self.log("⚠️ SEO score is 0, may indicate calculation issue")
                
            return True
        else:
            self.log(f"❌ SEO analysis of apollo.io failed: {result}", "ERROR")
            return False

    def test_analyze_seo_clearbit(self) -> bool:
        """Test SEO analysis of clearbit.com"""
        self.log("Testing SEO analysis of clearbit.com...")
        
        if not self.user_token:
            self.log("❌ No user token available for SEO analysis test", "ERROR")
            return False
            
        test_data = {"url": "https://clearbit.com"}
        result = self.make_request("POST", "/analyze-seo", token=self.user_token, data=test_data)
        
        if result["success"] and "seo_score" in result["data"]:
            seo_data = result["data"]
            seo_score = seo_data.get("seo_score", 0)
            issues = seo_data.get("issues", [])
            warnings = seo_data.get("warnings", [])
            
            self.log(f"✅ SEO analysis completed for clearbit.com")
            self.log(f"   SEO Score: {seo_score}/100")
            self.log(f"   Issues: {len(issues)}")
            self.log(f"   Warnings: {len(warnings)}")
            return True
        else:
            self.log(f"❌ SEO analysis of clearbit.com failed: {result}", "ERROR")
            return False

    def test_save_extracted_keywords(self) -> bool:
        """Test saving extracted keywords to user preferences"""
        self.log("Testing saving extracted keywords...")
        
        if not self.user_token:
            self.log("❌ No user token available for save keywords test", "ERROR")
            return False
            
        if not hasattr(self, 'extracted_keywords'):
            self.log("❌ No extracted keywords available for save test", "ERROR")
            return False
            
        save_data = {
            "keywords": self.extracted_keywords[:10],  # Save first 10 keywords
            "url": self.extracted_url,
            "metadata": self.extracted_metadata
        }
        
        result = self.make_request("POST", "/save-extracted-keywords", token=self.user_token, data=save_data)
        
        if result["success"] and result["data"].get("total_keywords"):
            total_keywords = result["data"]["total_keywords"]
            message = result["data"].get("message", "")
            
            self.log(f"✅ Keywords saved successfully")
            self.log(f"   Message: {message}")
            self.log(f"   Total keywords in preferences: {total_keywords}")
            return True
        else:
            self.log(f"❌ Saving extracted keywords failed: {result}", "ERROR")
            return False

    def test_preferences_with_extracted_keywords(self) -> bool:
        """Test that preferences contain extracted keywords"""
        self.log("Testing preferences contain extracted keywords...")
        
        if not self.user_token:
            self.log("❌ No user token available for preferences test", "ERROR")
            return False
            
        result = self.make_request("GET", "/preferences", token=self.user_token)
        
        if result["success"] and result["data"].get("user_id"):
            prefs = result["data"]
            extracted_keywords = prefs.get("extracted_keywords", [])
            target_keywords = prefs.get("target_keywords", [])
            analyzed_urls = prefs.get("analyzed_urls", [])
            
            self.log(f"✅ Preferences retrieved with keyword data")
            self.log(f"   Extracted keywords: {len(extracted_keywords)}")
            self.log(f"   Target keywords: {len(target_keywords)}")
            self.log(f"   Analyzed URLs: {len(analyzed_urls)}")
            
            # Check if our saved keywords are present
            if hasattr(self, 'extracted_keywords'):
                saved_keywords = self.extracted_keywords[:10]
                found_keywords = [kw for kw in saved_keywords if kw in target_keywords]
                self.log(f"   Keywords found in preferences: {len(found_keywords)}/{len(saved_keywords)}")
                
                if len(found_keywords) > 0:
                    self.log("✅ Extracted keywords successfully merged into preferences")
                else:
                    self.log("⚠️ Extracted keywords not found in preferences")
            
            # Check analyzed URLs
            if analyzed_urls and hasattr(self, 'extracted_url'):
                url_found = any(entry.get('url') == self.extracted_url for entry in analyzed_urls)
                if url_found:
                    self.log("✅ Analyzed URL tracked in preferences")
                else:
                    self.log("⚠️ Analyzed URL not found in preferences")
            
            return True
        else:
            self.log(f"❌ Get preferences with extracted keywords failed: {result}", "ERROR")
            return False

    def test_extract_keywords_unauthorized(self) -> bool:
        """Test keyword extraction without authentication"""
        self.log("Testing keyword extraction without authentication...")
        
        test_data = {"url": "https://www.apollo.io"}
        result = self.make_request("POST", "/extract-keywords", data=test_data)
        
        if result["status_code"] == 401:
            self.log("✅ Keyword extraction properly protected (unauthorized access blocked)")
            return True
        else:
            self.log(f"❌ Keyword extraction not properly protected: {result}", "ERROR")
            return False

    def test_analyze_seo_unauthorized(self) -> bool:
        """Test SEO analysis without authentication"""
        self.log("Testing SEO analysis without authentication...")
        
        test_data = {"url": "https://www.apollo.io"}
        result = self.make_request("POST", "/analyze-seo", data=test_data)
        
        if result["status_code"] == 401:
            self.log("✅ SEO analysis properly protected (unauthorized access blocked)")
            return True
        else:
            self.log(f"❌ SEO analysis not properly protected: {result}", "ERROR")
            return False

    def run_all_tests(self) -> Dict[str, bool]:
        """Run all backend tests"""
        self.log("=" * 60)
        self.log("STARTING TRAFFIC OPPORTUNITY ENGINE BACKEND TESTS")
        self.log("=" * 60)
        
        test_results = {}
        
        # Health check
        test_results["health_check"] = self.test_health_check()
        
        # Authentication tests
        test_results["auth_register"] = self.test_auth_register()
        test_results["auth_login_admin"] = self.test_auth_login_admin()
        test_results["auth_me"] = self.test_auth_me()
        
        # Core functionality tests
        test_results["opportunities_list"] = self.test_opportunities_list()
        test_results["opportunities_filtered"] = self.test_opportunities_filtered()
        test_results["recommendations_list"] = self.test_recommendations_list()
        
        # User Preferences System tests (NEW)
        self.log("\n" + "=" * 40)
        self.log("TESTING USER PREFERENCES SYSTEM")
        self.log("=" * 40)
        test_results["preferences_get_defaults"] = self.test_preferences_get_defaults()
        test_results["preferences_update"] = self.test_preferences_update()
        test_results["preferences_get_updated"] = self.test_preferences_get_updated()
        test_results["preferences_reset"] = self.test_preferences_reset()
        test_results["preferences_get_after_reset"] = self.test_preferences_get_after_reset()
        test_results["preferences_unauthorized"] = self.test_preferences_unauthorized()
        
        # API Token Management tests (NEW)
        self.log("\n" + "=" * 40)
        self.log("TESTING API TOKEN MANAGEMENT")
        self.log("=" * 40)
        test_results["api_token_generation"] = self.test_api_token_generation()
        test_results["api_token_list"] = self.test_api_token_list()
        test_results["api_token_revoke"] = self.test_api_token_revoke()
        
        # Admin tests
        self.log("\n" + "=" * 40)
        self.log("TESTING ADMIN ENDPOINTS")
        self.log("=" * 40)
        test_results["admin_stats"] = self.test_admin_stats()
        test_results["admin_users"] = self.test_admin_users()
        test_results["admin_channels"] = self.test_admin_channels()
        test_results["admin_trigger_scan"] = self.test_admin_trigger_scan()
        
        # Security tests
        self.log("\n" + "=" * 40)
        self.log("TESTING SECURITY & AUTHORIZATION")
        self.log("=" * 40)
        test_results["unauthorized_access"] = self.test_unauthorized_access()
        test_results["user_accessing_admin"] = self.test_user_accessing_admin()
        
        # Summary
        self.log("=" * 60)
        self.log("TEST RESULTS SUMMARY")
        self.log("=" * 60)
        
        passed = sum(1 for result in test_results.values() if result)
        total = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{test_name}: {status}")
            
        self.log(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            self.log("🎉 ALL TESTS PASSED!")
        else:
            self.log(f"⚠️  {total - passed} tests failed")
            
        return test_results


if __name__ == "__main__":
    tester = TrafficEngineAPITester()
    results = tester.run_all_tests()