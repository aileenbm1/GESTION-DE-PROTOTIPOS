#!/usr/bin/env python
"""
Comprehensive API testing script
Tests all endpoints for functionality and proper responses
"""

import requests
import json
from pathlib import Path
import time

BASE_URL = "http://127.0.0.1:8000"
API_BASE = f"{BASE_URL}/api"

def log_test(name, status, details=""):
    symbol = "✓" if status else "✗"
    print(f"{symbol} {name}")
    if details:
        print(f"  → {details}")

def test_health():
    print("\n=== HEALTH CHECKS ===")
    try:
        resp = requests.get(f"{BASE_URL}/health")
        log_test("GET /health", resp.status_code == 200, f"Status: {resp.status_code}")
    except Exception as e:
        log_test("GET /health", False, str(e))
    
    try:
        resp = requests.get(f"{API_BASE}/health")
        log_test("GET /api/health", resp.status_code == 200, f"Status: {resp.status_code}")
    except Exception as e:
        log_test("GET /api/health", False, str(e))

def test_project_lifecycle():
    print("\n=== PROJECT LIFECYCLE ===")
    
    # CREATE PROJECT
    project_id = None
    try:
        resp = requests.post(f"{API_BASE}/projects", json={"name": "Test Project"})
        if resp.status_code == 200:
            project = resp.json()
            project_id = project.get("id")
            log_test("POST /api/projects", True, f"Project ID: {project_id}")
        else:
            log_test("POST /api/projects", False, f"Status: {resp.status_code} - {resp.text[:100]}")
    except Exception as e:
        log_test("POST /api/projects", False, str(e))
        return
    
    if not project_id:
        print("  Cannot continue without project_id")
        return
    
    # GET PROJECT
    try:
        resp = requests.get(f"{API_BASE}/projects/{project_id}")
        log_test("GET /api/projects/{id}", resp.status_code == 200, f"Status: {resp.status_code}")
    except Exception as e:
        log_test("GET /api/projects/{id}", False, str(e))
    
    # UPLOAD FILE
    try:
        test_file = Path("/tmp/test_upload.txt")
        test_file.write_text("Test content for upload")
        
        with open(test_file, "rb") as f:
            files = {"file": ("test.txt", f, "text/plain")}
            resp = requests.post(f"{API_BASE}/projects/{project_id}/upload", files=files)
        
        if resp.status_code == 200:
            log_test("POST /api/projects/{id}/upload", True, f"Status: {resp.status_code}")
        else:
            log_test("POST /api/projects/{id}/upload", False, f"Status: {resp.status_code} - {resp.text[:100]}")
    except Exception as e:
        log_test("POST /api/projects/{id}/upload", False, str(e))
    
    # RUN INITIAL ANALYSIS
    try:
        resp = requests.post(f"{API_BASE}/projects/{project_id}/run-initial")
        if resp.status_code == 200:
            log_test("POST /api/projects/{id}/run-initial", True, f"Status: {resp.status_code}")
        else:
            log_test("POST /api/projects/{id}/run-initial", False, f"Status: {resp.status_code} - {resp.text[:100]}")
    except Exception as e:
        log_test("POST /api/projects/{id}/run-initial", False, str(e))
    
    # GET PROGRESS
    try:
        resp = requests.get(f"{API_BASE}/projects/{project_id}/progress")
        if resp.status_code == 200:
            log_test("GET /api/projects/{id}/progress", True, f"Status: {resp.status_code}")
        else:
            log_test("GET /api/projects/{id}/progress", False, f"Status: {resp.status_code}")
    except Exception as e:
        log_test("GET /api/projects/{id}/progress", False, str(e))
    
    # GENERATE SCREENS
    try:
        resp = requests.post(f"{API_BASE}/projects/{project_id}/screens/generate")
        if resp.status_code == 200:
            log_test("POST /api/projects/{id}/screens/generate", True, f"Status: {resp.status_code}")
        else:
            log_test("POST /api/projects/{id}/screens/generate", False, f"Status: {resp.status_code} - {resp.text[:100]}")
    except Exception as e:
        log_test("POST /api/projects/{id}/screens/generate", False, str(e))
    
    # GENERATE ARCHITECTURE
    try:
        resp = requests.post(f"{API_BASE}/projects/{project_id}/architecture")
        if resp.status_code == 200:
            log_test("POST /api/projects/{id}/architecture", True, f"Status: {resp.status_code}")
        else:
            log_test("POST /api/projects/{id}/architecture", False, f"Status: {resp.status_code} - {resp.text[:100]}")
    except Exception as e:
        log_test("POST /api/projects/{id}/architecture", False, str(e))
    
    # GENERATE CODE
    try:
        resp = requests.post(f"{API_BASE}/projects/{project_id}/code")
        if resp.status_code == 200:
            log_test("POST /api/projects/{id}/code", True, f"Status: {resp.status_code}")
        else:
            log_test("POST /api/projects/{id}/code", False, f"Status: {resp.status_code} - {resp.text[:100]}")
    except Exception as e:
        log_test("POST /api/projects/{id}/code", False, str(e))
    
    # PACKAGE PROJECT
    try:
        resp = requests.post(f"{API_BASE}/projects/{project_id}/package")
        if resp.status_code == 200:
            log_test("POST /api/projects/{id}/package", True, f"Status: {resp.status_code}")
        else:
            log_test("POST /api/projects/{id}/package", False, f"Status: {resp.status_code} - {resp.text[:100]}")
    except Exception as e:
        log_test("POST /api/projects/{id}/package", False, str(e))
    
    # DOWNLOAD PROJECT
    try:
        resp = requests.get(f"{API_BASE}/projects/{project_id}/download")
        if resp.status_code == 200:
            log_test("GET /api/projects/{id}/download", True, f"Status: {resp.status_code}")
        else:
            log_test("GET /api/projects/{id}/download", False, f"Status: {resp.status_code}")
    except Exception as e:
        log_test("GET /api/projects/{id}/download", False, str(e))

def test_cors_headers():
    print("\n=== CORS VALIDATION ===")
    try:
        headers = {
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        }
        resp = requests.options(f"{API_BASE}/projects", headers=headers)
        
        has_origin = "access-control-allow-origin" in resp.headers
        has_methods = "access-control-allow-methods" in resp.headers
        has_headers = "access-control-allow-headers" in resp.headers
        
        log_test("CORS Headers Present", has_origin and has_methods and has_headers, 
                f"Origin: {has_origin}, Methods: {has_methods}, Headers: {has_headers}")
    except Exception as e:
        log_test("CORS Headers Present", False, str(e))

if __name__ == "__main__":
    print("=" * 60)
    print("BACKEND API COMPREHENSIVE TEST")
    print("=" * 60)
    
    test_health()
    test_cors_headers()
    test_project_lifecycle()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)
