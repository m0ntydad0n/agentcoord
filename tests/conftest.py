import pytest
import subprocess
import time
import requests
from selenium import webdriver

@pytest.fixture(scope="session", autouse=True)
def start_dev_server():
    """Start the development server before running tests"""
    # Start the server process
    server_process = subprocess.Popen(
        ["npm", "start"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to be ready
    max_attempts = 30
    for _ in range(max_attempts):
        try:
            response = requests.get("http://localhost:3000", timeout=1)
            if response.status_code == 200:
                break
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            time.sleep(1)
    else:
        server_process.terminate()
        raise Exception("Development server failed to start")
    
    yield
    
    # Cleanup
    server_process.terminate()
    server_process.wait()

@pytest.fixture(scope="session")
def chrome_options():
    """Chrome options for consistent testing"""
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return options