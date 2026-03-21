# XRSS - Daily Opportunity Digest

Automated daily digest of grants, hackathons, bounties, paid open source projects, and VC funding opportunities scraped from Twitter/X.

## How It Works

1. **GitHub Actions** runs a cron job at 11 PM daily
2. **Python scraper** uses [twikit](https://github.com/d60/twikit) to search Twitter for opportunity-related tweets
3. **HTML generator** builds a static page with daily tabs
4. **GitHub Pages** serves the page for free

## Setup

### 1. Create a GitHub repo

```bash
cd xrss
git init
git add .
git commit -m "Initial commit"
gh repo create xrss --public --source=. --push
```

### 2. Add Twitter credentials as GitHub Secrets

Go to your repo → Settings → Secrets and variables → Actions → New repository secret

Add these three secrets:
- `TWITTER_USERNAME` — your Twitter/X username
- `TWITTER_EMAIL` — the email on your Twitter/X account
- `TWITTER_PASSWORD` — your Twitter/X password

> Use a secondary/burner account if you prefer.

### 3. Enable GitHub Pages

Go to your repo → Settings → Pages:
- Source: **Deploy from a branch**
- Branch: **main**, folder: **/docs**
- Save

### 4. Adjust the cron schedule (optional)

Edit `.github/workflows/scrape.yml` and change the cron time to match your timezone:

```yaml
# 11 PM IST  → "30 17 * * *"
# 11 PM EST  → "0  4  * * *"
# 11 PM UTC  → "0  23 * * *"
```

### 5. Test it manually

Go to Actions → "Daily Opportunity Scrape" → Run workflow

Your page will be live at: `https://<your-username>.github.io/xrss/`

## Local Development

```bash
pip install -r requirements.txt
export TWITTER_USERNAME=your_username
export TWITTER_EMAIL=your_email
export TWITTER_PASSWORD=your_password
python scraper/scrape.py
python scraper/generate_html.py
# open docs/index.html in your browser
```

## Search Queries

Edit the `SEARCH_QUERIES` list in `scraper/scrape.py` to customize what gets scraped.
