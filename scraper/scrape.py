import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from twscrape import API, gather
from twscrape.logger import set_log_level

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

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


def parse_tweet(tweet) -> dict:
    return {
        "id": str(tweet.id),
        "text": tweet.rawContent,
        "user": {
            "name": tweet.user.displayname if tweet.user else "Unknown",
            "screen_name": tweet.user.username if tweet.user else "unknown",
            "followers": tweet.user.followersCount if tweet.user else 0,
            "profile_image": tweet.user.profileImageUrl if tweet.user else "",
        },
        "created_at": tweet.date.isoformat() if tweet.date else "",
        "favorite_count": tweet.likeCount or 0,
        "retweet_count": tweet.retweetCount or 0,
        "url": tweet.url or "",
        "query": "",
    }


async def main():
    set_log_level("WARNING")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"Scraping tweets for {today}...")

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    username = os.environ.get("TWITTER_USERNAME", "")
    email = os.environ.get("TWITTER_EMAIL", "")
    password = os.environ.get("TWITTER_PASSWORD", "")

    if not all([username, email, password]):
        print(
            "Error: Set TWITTER_USERNAME, TWITTER_EMAIL, and TWITTER_PASSWORD "
            "environment variables."
        )
        sys.exit(1)

    api = API()

    # Add account (twscrape manages its own pool of accounts)
    await api.pool.add_account(username, password, email, password)
    await api.pool.login_all()

    all_tweets = []
    for query in SEARCH_QUERIES:
        try:
            tweets = await gather(api.search(query, limit=MAX_TWEETS_PER_QUERY))
            for tweet in tweets:
                t = parse_tweet(tweet)
                t["query"] = query
                all_tweets.append(t)
            print(f"  Found {len(tweets)} tweets for: {query}")
        except Exception as e:
            print(f"  Error searching '{query}': {e}")
        await asyncio.sleep(2)

    # Deduplicate
    seen = set()
    unique = []
    for t in all_tweets:
        if t["id"] not in seen:
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


if __name__ == "__main__":
    asyncio.run(main())
