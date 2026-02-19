import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time

class TestCyberpunkUI:
    @pytest.fixture(scope="class")
    def driver(self):
        """Setup Chrome driver with headless options"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        driver = webdriver.Chrome(options=chrome_options)
        yield driver
        driver.quit()

    def test_dashboard_loads(self, driver):
        """Test that the cyberpunk dashboard loads successfully"""
        driver.get("http://localhost:3000/dashboard")
        
        # Wait for page to load
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "cyberpunk-dashboard")))
        
        assert "Dashboard" in driver.title

    def test_neon_elements_display(self, driver):
        """Test that neon UI elements are properly displayed"""
        driver.get("http://localhost:3000/dashboard")
        wait = WebDriverWait(driver, 10)
        
        # Check for neon headers
        neon_headers = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "neon-text")))
        assert len(neon_headers) > 0
        
        # Verify glow effects are applied
        for header in neon_headers:
            box_shadow = header.value_of_css_property("box-shadow")
            assert box_shadow is not None and box_shadow != "none"

    def test_grid_layout_responsive(self, driver):
        """Test that the dashboard grid layout is responsive"""
        driver.get("http://localhost:3000/dashboard")
        wait = WebDriverWait(driver, 10)
        
        # Check grid container exists
        grid_container = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "dashboard-grid")))
        
        # Test desktop view
        driver.set_window_size(1920, 1080)
        time.sleep(0.5)
        desktop_width = grid_container.size['width']
        
        # Test mobile view
        driver.set_window_size(390, 844)
        time.sleep(0.5)
        mobile_width = grid_container.size['width']
        
        assert mobile_width < desktop_width

    def test_cyberpunk_widgets_present(self, driver):
        """Test that all cyberpunk-themed widgets are present"""
        driver.get("http://localhost:3000/dashboard")
        wait = WebDriverWait(driver, 10)
        
        # Check for system status widget
        system_widget = wait.until(EC.presence_of_element_located((By.ID, "system-status")))
        assert system_widget.is_displayed()
        
        # Check for data streams widget
        data_widget = wait.until(EC.presence_of_element_located((By.ID, "data-streams")))
        assert data_widget.is_displayed()
        
        # Check for neural network visualization
        neural_widget = wait.until(EC.presence_of_element_located((By.ID, "neural-viz")))
        assert neural_widget.is_displayed()

    def test_animations_functional(self, driver):
        """Test that cyberpunk animations are working"""
        driver.get("http://localhost:3000/dashboard")
        wait = WebDriverWait(driver, 10)
        
        # Check for animated elements
        animated_elements = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "cyberpunk-pulse")))
        
        for element in animated_elements:
            # Verify animation is applied
            animation = element.value_of_css_property("animation-name")
            assert animation and animation != "none"

    def test_theme_colors_applied(self, driver):
        """Test that cyberpunk color scheme is properly applied"""
        driver.get("http://localhost:3000/dashboard")
        wait = WebDriverWait(driver, 10)
        
        # Check background color
        body = wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        bg_color = body.value_of_css_property("background-color")
        
        # Should be dark cyberpunk background
        assert "rgb(0, 0, 0)" in bg_color or "rgb(15, 15, 35)" in bg_color
        
        # Check accent colors
        accent_elements = driver.find_elements(By.CLASS_NAME, "cyberpunk-accent")
        for element in accent_elements:
            color = element.value_of_css_property("color")
            # Should be cyan/neon colors
            assert any(neon in color for neon in ["rgb(0, 255, 255)", "rgb(57, 255, 20)", "rgb(255, 20, 147)"])