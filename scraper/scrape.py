import json
import os
import sys
import time
import re
from datetime import datetime, timezone
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
COOKIES_FILE = PROJECT_ROOT / "scraper" / "cookies.json"

SEARCH_QUERIES = [
    "developer grants apply",
    "hackathon registration open",
    "open source bounty",
    "paid open source contributors",
    "startup funding apply",
    "VC funding founders apply",
    "developer bounty program",
    "web3 grants open",
    "tech accelerator applications open",
    "open source sponsorship",
]

MAX_SCROLL_PER_QUERY = 3


def create_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    return driver


def save_cookies(driver):
    cookies = driver.get_cookies()
    with open(COOKIES_FILE, "w") as f:
        json.dump(cookies, f)


def load_cookies(driver):
    if not COOKIES_FILE.exists():
        return False
    with open(COOKIES_FILE) as f:
        cookies = json.load(f)
    driver.get("https://x.com")
    time.sleep(2)
    for cookie in cookies:
        cookie.pop("sameSite", None)
        cookie.pop("expiry", None)
        try:
            driver.add_cookie(cookie)
        except Exception:
            pass
    driver.refresh()
    time.sleep(3)
    return True


def login(driver):
    username = os.environ.get("TWITTER_USERNAME", "")
    email = os.environ.get("TWITTER_EMAIL", "")
    password = os.environ.get("TWITTER_PASSWORD", "")

    if not all([username, email, password]):
        print("Error: Set TWITTER_USERNAME, TWITTER_EMAIL, TWITTER_PASSWORD in .env")
        sys.exit(1)

    # Try loading cookies first
    if COOKIES_FILE.exists():
        load_cookies(driver)
        driver.get("https://x.com/home")
        time.sleep(3)
        if "login" not in driver.current_url.lower():
            print("Logged in via cookies.")
            return

    print("Logging in with credentials...")
    driver.get("https://x.com/i/flow/login")
    time.sleep(5)

    wait = WebDriverWait(driver, 20)
    debug_dir = PROJECT_ROOT / "debug"
    debug_dir.mkdir(exist_ok=True)

    # Enter username
    try:
        username_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[autocomplete="username"]'))
        )
    except Exception:
        driver.save_screenshot(str(debug_dir / "login_step1.png"))
        print(f"Could not find username field. Screenshot saved. URL: {driver.current_url}")
        sys.exit(1)

    username_input.send_keys(username)
    username_input.send_keys(Keys.RETURN)
    time.sleep(3)

    driver.save_screenshot(str(debug_dir / "after_username.png"))

    # Check if email/phone verification is needed
    try:
        email_input = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[data-testid="ocfEnterTextTextInput"]'))
        )
        print("Email verification step detected.")
        email_input.send_keys(email)
        email_input.send_keys(Keys.RETURN)
        time.sleep(3)
    except Exception:
        pass

    # Enter password — try multiple selectors
    password_input = None
    for selector in ['input[name="password"]', 'input[type="password"]', 'input[autocomplete="current-password"]']:
        try:
            password_input = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            break
        except Exception:
            continue

    if not password_input:
        driver.save_screenshot(str(debug_dir / "no_password_field.png"))
        print(f"Could not find password field. Screenshot saved. URL: {driver.current_url}")
        print(f"Page source snippet: {driver.page_source[:500]}")
        sys.exit(1)

    password_input.send_keys(password)
    password_input.send_keys(Keys.RETURN)
    time.sleep(5)

    driver.save_screenshot(str(debug_dir / "after_login.png"))

    if "home" in driver.current_url.lower():
        print("Login successful.")
        save_cookies(driver)
    else:
        print(f"Login may have failed. Current URL: {driver.current_url}")
        save_cookies(driver)


def extract_tweets_from_page(driver) -> list[dict]:
    tweets = []
    try:
        articles = driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')
        for article in articles:
            try:
                tweet = {}

                # Get user info
                user_links = article.find_elements(By.CSS_SELECTOR, 'a[role="link"]')
                for link in user_links:
                    href = link.get_attribute("href") or ""
                    if href.startswith("https://x.com/") and "/status/" not in href:
                        tweet["user_url"] = href
                        tweet["screen_name"] = href.split("/")[-1]
                        break

                # Get display name
                try:
                    name_el = article.find_element(
                        By.CSS_SELECTOR, 'div[data-testid="User-Name"] a span'
                    )
                    tweet["name"] = name_el.text
                except Exception:
                    tweet["name"] = tweet.get("screen_name", "Unknown")

                # Get tweet text
                try:
                    text_el = article.find_element(
                        By.CSS_SELECTOR, 'div[data-testid="tweetText"]'
                    )
                    tweet["text"] = text_el.text
                except Exception:
                    tweet["text"] = ""

                # Get tweet link (for ID and URL)
                try:
                    time_el = article.find_element(By.CSS_SELECTOR, "time")
                    parent_a = time_el.find_element(By.XPATH, "./..")
                    tweet_url = parent_a.get_attribute("href") or ""
                    tweet["url"] = tweet_url
                    tweet["id"] = tweet_url.split("/")[-1] if "/status/" in tweet_url else ""
                    tweet["created_at"] = time_el.get_attribute("datetime") or ""
                except Exception:
                    tweet["url"] = ""
                    tweet["id"] = ""
                    tweet["created_at"] = ""

                # Get metrics
                tweet["favorite_count"] = 0
                tweet["retweet_count"] = 0
                try:
                    like_btn = article.find_element(
                        By.CSS_SELECTOR, 'button[data-testid="like"]'
                    )
                    like_text = like_btn.get_attribute("aria-label") or ""
                    nums = re.findall(r"[\d,]+", like_text)
                    if nums:
                        tweet["favorite_count"] = int(nums[0].replace(",", ""))
                except Exception:
                    pass
                try:
                    rt_btn = article.find_element(
                        By.CSS_SELECTOR, 'button[data-testid="retweet"]'
                    )
                    rt_text = rt_btn.get_attribute("aria-label") or ""
                    nums = re.findall(r"[\d,]+", rt_text)
                    if nums:
                        tweet["retweet_count"] = int(nums[0].replace(",", ""))
                except Exception:
                    pass

                # Get profile image
                try:
                    img = article.find_element(
                        By.CSS_SELECTOR, 'div[data-testid="Tweet-User-Avatar"] img'
                    )
                    tweet["profile_image"] = img.get_attribute("src") or ""
                except Exception:
                    tweet["profile_image"] = ""

                if tweet.get("text") and tweet.get("id"):
                    tweets.append(tweet)
            except Exception:
                continue
    except Exception:
        pass
    return tweets


def search_query(driver, query: str) -> list[dict]:
    encoded = query.replace(" ", "%20")
    url = f"https://x.com/search?q={encoded}&src=typed_query&f=live"
    driver.get(url)
    time.sleep(4)

    all_tweets = []
    seen_ids = set()

    for _ in range(MAX_SCROLL_PER_QUERY):
        tweets = extract_tweets_from_page(driver)
        for t in tweets:
            if t["id"] not in seen_ids:
                seen_ids.add(t["id"])
                all_tweets.append(t)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    print(f"  Found {len(all_tweets)} tweets for: {query}")
    return all_tweets


def format_tweet(tweet: dict, query: str) -> dict:
    return {
        "id": tweet.get("id", ""),
        "text": tweet.get("text", ""),
        "user": {
            "name": tweet.get("name", "Unknown"),
            "screen_name": tweet.get("screen_name", "unknown"),
            "followers": 0,
            "profile_image": tweet.get("profile_image", ""),
        },
        "created_at": tweet.get("created_at", ""),
        "favorite_count": tweet.get("favorite_count", 0),
        "retweet_count": tweet.get("retweet_count", 0),
        "url": tweet.get("url", ""),
        "query": query,
    }


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"Scraping tweets for {today}...")

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    driver = create_driver()
    try:
        login(driver)

        all_tweets = []
        for query in SEARCH_QUERIES:
            tweets = search_query(driver, query)
            for t in tweets:
                all_tweets.append(format_tweet(t, query))
            time.sleep(1)

        # Load IDs from previous days to avoid duplicates across runs
        past_ids = set()
        for old_file in DATA_DIR.glob("*.json"):
            if old_file.stem == today:
                continue
            try:
                with open(old_file) as f:
                    old_data = json.load(f)
                for t in old_data.get("tweets", []):
                    past_ids.add(t.get("id", ""))
            except Exception:
                pass

        # Deduplicate within today + across past days
        seen = set()
        unique = []
        for t in all_tweets:
            if t["id"] not in seen and t["id"] not in past_ids:
                seen.add(t["id"])
                unique.append(t)
        unique.sort(key=lambda t: t.get("favorite_count", 0), reverse=True)

        output_file = DATA_DIR / f"{today}.json"
        with open(output_file, "w") as f:
            json.dump(
                {"date": today, "tweet_count": len(unique), "tweets": unique},
                f,
                indent=2,
                default=str,
            )

        print(f"Saved {len(unique)} unique tweets to {output_file}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
