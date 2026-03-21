import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from twikit import Client

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

MAX_TWEETS_PER_QUERY = 50


async def login(client: Client) -> None:
    """Login to Twitter using env vars or cached cookies."""
    if COOKIES_FILE.exists():
        client.load_cookies(str(COOKIES_FILE))
        print("Loaded cached cookies.")
        return

    username = os.environ.get("TWITTER_USERNAME")
    email = os.environ.get("TWITTER_EMAIL")
    password = os.environ.get("TWITTER_PASSWORD")

    if not all([username, email, password]):
        print(
            "Error: Set TWITTER_USERNAME, TWITTER_EMAIL, and TWITTER_PASSWORD "
            "environment variables, or provide a cookies.json file."
        )
        sys.exit(1)

    await client.login(
        auth_info_1=username,
        auth_info_2=email,
        password=password,
    )
    client.save_cookies(str(COOKIES_FILE))
    print("Logged in and saved cookies.")


def parse_tweet(tweet) -> dict:
    """Extract relevant fields from a tweet object."""
    return {
        "id": tweet.id,
        "text": tweet.text,
        "user": {
            "name": tweet.user.name if tweet.user else "Unknown",
            "screen_name": tweet.user.screen_name if tweet.user else "unknown",
            "followers": tweet.user.followers_count if tweet.user else 0,
            "profile_image": tweet.user.profile_image_url if tweet.user else "",
        },
        "created_at": tweet.created_at,
        "favorite_count": tweet.favorite_count,
        "retweet_count": tweet.retweet_count,
        "url": f"https://x.com/{tweet.user.screen_name}/status/{tweet.id}" if tweet.user else "",
        "query": "",
    }


async def search_tweets(client: Client, query: str) -> list[dict]:
    """Search for tweets matching a query."""
    tweets = []
    try:
        results = await client.search_tweet(query, "Latest", count=MAX_TWEETS_PER_QUERY)
        for tweet in results:
            t = parse_tweet(tweet)
            t["query"] = query
            tweets.append(t)
        print(f"  Found {len(tweets)} tweets for: {query}")
    except Exception as e:
        print(f"  Error searching '{query}': {e}")
    return tweets


def deduplicate(tweets: list[dict]) -> list[dict]:
    """Remove duplicate tweets by ID."""
    seen = set()
    unique = []
    for t in tweets:
        if t["id"] not in seen:
            seen.add(t["id"])
            unique.append(t)
    return unique


async def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"Scraping tweets for {today}...")

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    client = Client(language="en-US")
    await login(client)

    all_tweets = []
    for query in SEARCH_QUERIES:
        tweets = await search_tweets(client, query)
        all_tweets.extend(tweets)
        await asyncio.sleep(2)  # rate limit buffer

    all_tweets = deduplicate(all_tweets)
    all_tweets.sort(key=lambda t: t.get("favorite_count", 0), reverse=True)

    output_file = DATA_DIR / f"{today}.json"
    with open(output_file, "w") as f:
        json.dump(
            {"date": today, "tweet_count": len(all_tweets), "tweets": all_tweets},
            f,
            indent=2,
            default=str,
        )

    print(f"Saved {len(all_tweets)} unique tweets to {output_file}")
    return output_file


if __name__ == "__main__":
    asyncio.run(main())
