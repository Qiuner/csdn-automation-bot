"""Verify the container's headed browser without logging in or visiting articles."""
import json
import tempfile
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

with tempfile.TemporaryDirectory() as profile:
    options = webdriver.ChromeOptions()
    options.binary_location = '/usr/bin/chromium'
    options.add_argument('--no-sandbox')
    options.add_argument('--user-data-dir=' + profile)
    options.page_load_strategy = 'eager'
    driver = webdriver.Chrome(service=Service('/usr/bin/chromedriver'), options=options)
    try:
        driver.set_page_load_timeout(30)
        driver.get('data:text/html,<title>csdn-server-smoke</title><h1>Ready</h1>')
        assert driver.title == 'csdn-server-smoke'
        print(json.dumps({'browser': driver.capabilities['browserVersion'],
                          'driver': driver.capabilities['chrome']['chromedriverVersion'].split(' ')[0],
                          'headed_browser': 'passed'}), flush=True)
    finally:
        driver.quit()
