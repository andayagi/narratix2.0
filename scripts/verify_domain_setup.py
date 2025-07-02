#!/usr/bin/env python3
"""
Script to verify custom domain setup for Railway deployment.
Tests connectivity, SSL certificates, and API endpoints.
"""

import asyncio
import aiohttp
import ssl
import socket
import subprocess
import sys
from typing import Dict, Any, List, Tuple
from datetime import datetime
import json

# Domain configuration
DOMAIN = "midsummerr.com"
API_DOMAIN = "api.midsummerr.com"
DOMAINS_TO_TEST = [
    f"https://{API_DOMAIN}"
]

# API endpoints to test
ENDPOINTS_TO_TEST = [
    "/",
    "/health", 
    "/health/detailed",
    "/health/ready"
]

async def test_domain_connectivity(domain_url: str) -> Dict[str, Any]:
    """Test basic connectivity to the domain."""
    print(f"Testing connectivity to {domain_url}...")
    
    result = {
        "domain": domain_url,
        "connectivity": False,
        "ssl_valid": False,
        "response_time": None,
        "status_code": None,
        "error": None
    }
    
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            start_time = datetime.now()
            async with session.get(domain_url) as response:
                end_time = datetime.now()
                
                result["connectivity"] = True
                result["status_code"] = response.status
                result["response_time"] = (end_time - start_time).total_seconds()
                result["ssl_valid"] = domain_url.startswith("https://")
                
                print(f"✅ {domain_url}: Status {response.status}, Response time: {result['response_time']:.3f}s")
                
    except Exception as e:
        result["error"] = str(e)
        print(f"❌ {domain_url}: Connection failed - {e}")
    
    return result

async def test_api_endpoints(base_url: str) -> List[Dict[str, Any]]:
    """Test API endpoints on the domain."""
    print(f"\nTesting API endpoints on {base_url}...")
    
    results = []
    timeout = aiohttp.ClientTimeout(total=10)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for endpoint in ENDPOINTS_TO_TEST:
            url = f"{base_url}{endpoint}"
            result = {
                "endpoint": endpoint,
                "url": url,
                "success": False,
                "status_code": None,
                "response_data": None,
                "error": None
            }
            
            try:
                async with session.get(url) as response:
                    result["status_code"] = response.status
                    result["success"] = 200 <= response.status < 400
                    
                    # Try to get JSON response
                    try:
                        result["response_data"] = await response.json()
                    except:
                        result["response_data"] = await response.text()
                    
                    if result["success"]:
                        print(f"✅ {endpoint}: Status {response.status}")
                    else:
                        print(f"❌ {endpoint}: Status {response.status}")
                        
            except Exception as e:
                result["error"] = str(e)
                print(f"❌ {endpoint}: Error - {e}")
            
            results.append(result)
    
    return results

def check_dns_records() -> Dict[str, Any]:
    """Check DNS records for the API domain."""
    print(f"\nChecking DNS records for {API_DOMAIN}...")
    
    result = {
        "domain": API_DOMAIN,
        "a_record": None,
        "cname_records": {},
        "error": None
    }
    
    try:
        # Check A record for API subdomain
        try:
            a_records = socket.gethostbyname_ex(API_DOMAIN)[2]
            result["a_record"] = a_records[0] if a_records else None
            print(f"✅ A record for {API_DOMAIN}: {result['a_record']}")
        except Exception as e:
            print(f"❌ A record lookup failed for {API_DOMAIN}: {e}")
        
        # Check main domain for reference
        try:
            main_ip = socket.gethostbyname(DOMAIN)
            result["cname_records"]["main"] = main_ip
            print(f"✅ {DOMAIN} resolves to: {main_ip} (frontend)")
        except Exception as e:
            print(f"❌ Main domain lookup failed: {e}")
            
    except Exception as e:
        result["error"] = str(e)
        print(f"❌ DNS lookup error: {e}")
    
    return result

def check_ssl_certificate(domain: str) -> Dict[str, Any]:
    """Check SSL certificate for the domain."""
    print(f"\nChecking SSL certificate for {domain}...")
    
    result = {
        "domain": domain,
        "ssl_valid": False,
        "issuer": None,
        "expires": None,
        "error": None
    }
    
    try:
        # Remove https:// prefix if present
        clean_domain = domain.replace("https://", "").replace("http://", "")
        
        context = ssl.create_default_context()
        with socket.create_connection((clean_domain, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=clean_domain) as ssock:
                cert = ssock.getpeercert()
                
                result["ssl_valid"] = True
                result["issuer"] = dict(x[0] for x in cert['issuer'])
                result["expires"] = cert['notAfter']
                
                print(f"✅ SSL certificate valid for {clean_domain}")
                print(f"   Issuer: {result['issuer'].get('organizationName', 'Unknown')}")
                print(f"   Expires: {result['expires']}")
                
    except Exception as e:
        result["error"] = str(e)
        print(f"❌ SSL certificate check failed: {e}")
    
    return result

async def main():
    """Main verification function."""
    print(f"🔍 Verifying API domain setup for {API_DOMAIN}")
    print("=" * 60)
    
    verification_results = {
        "timestamp": datetime.now().isoformat(),
        "domain": API_DOMAIN,
        "dns_check": None,
        "ssl_checks": [],
        "connectivity_tests": [],
        "api_tests": []
    }
    
    # 1. Check DNS records
    verification_results["dns_check"] = check_dns_records()
    
    # 2. Check SSL certificates
    for domain_url in DOMAINS_TO_TEST:
        ssl_result = check_ssl_certificate(domain_url)
        verification_results["ssl_checks"].append(ssl_result)
    
    # 3. Test domain connectivity
    connectivity_tasks = [test_domain_connectivity(url) for url in DOMAINS_TO_TEST]
    connectivity_results = await asyncio.gather(*connectivity_tasks)
    verification_results["connectivity_tests"] = connectivity_results
    
    # 4. Test API endpoints (only on successful connections)
    for conn_result in connectivity_results:
        if conn_result["connectivity"]:
            api_results = await test_api_endpoints(conn_result["domain"])
            verification_results["api_tests"].extend(api_results)
    
    # Summary
    print("\n" + "=" * 60)
    print("🏁 VERIFICATION SUMMARY")
    print("=" * 60)
    
    # DNS Summary
    dns_ok = verification_results["dns_check"]["a_record"] is not None
    print(f"DNS Configuration: {'✅ PASS' if dns_ok else '❌ FAIL'}")
    
    # SSL Summary  
    ssl_ok = any(check["ssl_valid"] for check in verification_results["ssl_checks"])
    print(f"SSL Certificates: {'✅ PASS' if ssl_ok else '❌ FAIL'}")
    
    # Connectivity Summary
    connectivity_ok = any(test["connectivity"] for test in verification_results["connectivity_tests"])
    print(f"Domain Connectivity: {'✅ PASS' if connectivity_ok else '❌ FAIL'}")
    
    # API Summary
    api_ok = any(test["success"] for test in verification_results["api_tests"])
    print(f"API Endpoints: {'✅ PASS' if api_ok else '❌ FAIL'}")
    
    # Overall status
    overall_success = dns_ok and ssl_ok and connectivity_ok and api_ok
    print(f"\nOverall Status: {'✅ ALL SYSTEMS GO' if overall_success else '❌ ISSUES DETECTED'}")
    
    # Save results to file
    output_file = f"api_domain_verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(verification_results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {output_file}")
    
    return overall_success

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Verification cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Verification failed with error: {e}")
        sys.exit(1) 