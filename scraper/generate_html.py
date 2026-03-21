import json
import html
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DOCS_DIR = PROJECT_ROOT / "docs"

CATEGORIES = {
    "Grants": ["grant", "grants", "sponsorship"],
    "Hackathons": ["hackathon", "hack", "devpost"],
    "Bounties": ["bounty", "bounties", "bug bounty"],
    "Paid OSS": ["open source", "oss", "contributor", "paid"],
    "VC / Funding": ["funding", "vc", "accelerator", "startup", "founders", "seed"],
}


def categorize_tweet(tweet: dict) -> str:
    text = (tweet.get("text", "") + " " + tweet.get("query", "")).lower()
    for category, keywords in CATEGORIES.items():
        if any(kw in text for kw in keywords):
            return category
    return "Other"


def escape(text: str) -> str:
    return html.escape(text or "")


def render_tweet_card(tweet: dict) -> str:
    user = tweet.get("user", {})
    name = escape(user.get("name", "Unknown"))
    handle = escape(user.get("screen_name", "unknown"))
    followers = user.get("followers", 0)
    text = escape(tweet.get("text", ""))
    url = escape(tweet.get("url", "#"))
    likes = tweet.get("favorite_count", 0)
    retweets = tweet.get("retweet_count", 0)
    profile_img = escape(user.get("profile_image", ""))

    return f"""
    <div class="tweet-card">
      <div class="tweet-header">
        <img src="{profile_img}" alt="" class="avatar" onerror="this.style.display='none'">
        <div class="tweet-user">
          <strong>{name}</strong>
          <span class="handle">@{handle}</span>
          <span class="followers">{followers:,} followers</span>
        </div>
      </div>
      <p class="tweet-text">{text}</p>
      <div class="tweet-meta">
        <span>{likes} likes</span>
        <span>{retweets} RTs</span>
        <a href="{url}" target="_blank" rel="noopener">View on X</a>
      </div>
    </div>"""


def render_day_content(data: dict) -> str:
    tweets = data.get("tweets", [])
    if not tweets:
        return '<p class="empty">No tweets found for this day.</p>'

    categorized: dict[str, list] = {}
    for tweet in tweets:
        cat = categorize_tweet(tweet)
        categorized.setdefault(cat, []).append(tweet)

    sections = []
    for category in list(CATEGORIES.keys()) + ["Other"]:
        cat_tweets = categorized.get(category, [])
        if not cat_tweets:
            continue
        cards = "\n".join(render_tweet_card(t) for t in cat_tweets)
        sections.append(
            f'<div class="category-section">'
            f'<h3 class="category-title">{escape(category)} '
            f'<span class="count">({len(cat_tweets)})</span></h3>'
            f'{cards}</div>'
        )

    return "\n".join(sections)


def generate_html():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    json_files = sorted(DATA_DIR.glob("*.json"), reverse=True)
    if not json_files:
        print("No data files found.")
        return

    days = []
    for jf in json_files[:30]:  # last 30 days max
        with open(jf) as f:
            data = json.load(f)
        days.append(data)

    tab_buttons = []
    tab_contents = []

    for i, day in enumerate(days):
        date_str = day.get("date", "unknown")
        count = day.get("tweet_count", 0)
        active = "active" if i == 0 else ""
        display = "block" if i == 0 else "none"

        try:
            label = datetime.strptime(date_str, "%Y-%m-%d").strftime("%b %d")
        except ValueError:
            label = date_str

        tab_buttons.append(
            f'<button class="tab-btn {active}" onclick="openTab(event, \'day-{date_str}\')">'
            f'{label} <span class="badge">{count}</span></button>'
        )
        tab_contents.append(
            f'<div id="day-{date_str}" class="tab-content" style="display:{display}">'
            f'<h2>{date_str} &mdash; {count} tweets found</h2>'
            f'{render_day_content(day)}</div>'
        )

    tabs_html = "\n".join(tab_buttons)
    content_html = "\n".join(tab_contents)

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>XRSS - Daily Opportunity Digest</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0d1117;
    color: #c9d1d9;
    min-height: 100vh;
  }}
  .header {{
    background: linear-gradient(135deg, #161b22, #1a1f2b);
    border-bottom: 1px solid #30363d;
    padding: 1.5rem 2rem;
    text-align: center;
  }}
  .header h1 {{
    font-size: 1.8rem;
    color: #58a6ff;
    margin-bottom: 0.3rem;
  }}
  .header p {{
    color: #8b949e;
    font-size: 0.9rem;
  }}
  .tabs {{
    display: flex;
    gap: 0.25rem;
    padding: 1rem 2rem 0;
    overflow-x: auto;
    background: #161b22;
    border-bottom: 1px solid #30363d;
  }}
  .tab-btn {{
    background: transparent;
    border: none;
    color: #8b949e;
    padding: 0.6rem 1rem;
    cursor: pointer;
    font-size: 0.85rem;
    border-bottom: 2px solid transparent;
    white-space: nowrap;
    transition: all 0.2s;
  }}
  .tab-btn:hover {{ color: #c9d1d9; }}
  .tab-btn.active {{
    color: #58a6ff;
    border-bottom-color: #58a6ff;
  }}
  .badge {{
    background: #30363d;
    border-radius: 10px;
    padding: 0.1rem 0.5rem;
    font-size: 0.75rem;
    margin-left: 0.3rem;
  }}
  .tab-content {{
    padding: 1.5rem 2rem;
    max-width: 900px;
    margin: 0 auto;
  }}
  .tab-content h2 {{
    color: #c9d1d9;
    margin-bottom: 1.5rem;
    font-size: 1.2rem;
  }}
  .category-section {{
    margin-bottom: 2rem;
  }}
  .category-title {{
    color: #58a6ff;
    font-size: 1.1rem;
    margin-bottom: 0.8rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid #21262d;
  }}
  .count {{
    color: #8b949e;
    font-weight: normal;
    font-size: 0.9rem;
  }}
  .tweet-card {{
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 0.8rem;
    transition: border-color 0.2s;
  }}
  .tweet-card:hover {{
    border-color: #58a6ff;
  }}
  .tweet-header {{
    display: flex;
    align-items: center;
    gap: 0.7rem;
    margin-bottom: 0.6rem;
  }}
  .avatar {{
    width: 36px;
    height: 36px;
    border-radius: 50%;
    flex-shrink: 0;
  }}
  .tweet-user strong {{
    color: #e6edf3;
    font-size: 0.9rem;
  }}
  .handle {{
    color: #8b949e;
    font-size: 0.8rem;
    margin-left: 0.3rem;
  }}
  .followers {{
    color: #8b949e;
    font-size: 0.75rem;
    margin-left: 0.5rem;
  }}
  .tweet-text {{
    font-size: 0.9rem;
    line-height: 1.5;
    color: #c9d1d9;
    margin-bottom: 0.6rem;
    white-space: pre-wrap;
    word-wrap: break-word;
  }}
  .tweet-meta {{
    display: flex;
    gap: 1rem;
    font-size: 0.8rem;
    color: #8b949e;
  }}
  .tweet-meta a {{
    color: #58a6ff;
    text-decoration: none;
  }}
  .tweet-meta a:hover {{
    text-decoration: underline;
  }}
  .empty {{
    text-align: center;
    color: #8b949e;
    padding: 3rem;
    font-size: 1.1rem;
  }}
  @media (max-width: 600px) {{
    .header {{ padding: 1rem; }}
    .tabs {{ padding: 0.5rem 1rem 0; }}
    .tab-content {{ padding: 1rem; }}
  }}
</style>
</head>
<body>
  <div class="header">
    <h1>XRSS</h1>
    <p>Daily digest of grants, hackathons, bounties, paid OSS & funding opportunities from X</p>
  </div>
  <div class="tabs">
    {tabs_html}
  </div>
  {content_html}
  <script>
    function openTab(evt, tabId) {{
      document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
      document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
      document.getElementById(tabId).style.display = 'block';
      evt.currentTarget.classList.add('active');
    }}
  </script>
</body>
</html>"""

    output = DOCS_DIR / "index.html"
    with open(output, "w") as f:
        f.write(page)
    print(f"Generated {output} with {len(days)} day(s) of data.")


if __name__ == "__main__":
    generate_html()
