from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json

options = Options()
options.add_argument("--disable-blink-features=AutomationControlled")
driver = webdriver.Chrome(options=options)
driver.get("https://x.com/i/flow/login")
input("Log in manually in the browser, then press ENTER here...")
cookies = driver.get_cookies()
with open("scraper/cookies.json", "w") as f:
    json.dump(cookies, f)
print(f"Saved {len(cookies)} cookies.")
driver.quit()
