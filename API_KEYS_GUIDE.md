# API Keys Setup Guide
# Step-by-step instructions for getting social media API keys

## Quick Answer: You Don't Need API Keys Right Now!

Your QuantumTrade Engine is already working with **simulated social signals** that look and feel real. The system shows trading signals for BTC/USD, EUR/USD, AAPL, and OIL/USD without needing any API keys.

## If You Want Real Social Media Data (Optional)

### Twitter/X API Keys (Free Tier Available)

**Steps to get Twitter Bearer Token:**

1. **Create Twitter Account**
   - Go to https://twitter.com and create a free account
   - Verify your email address

2. **Apply for Developer Access**
   - Go to https://developer.twitter.com
   - Click "Sign up for Free Account"
   - Fill out the application (describe your project as "Educational trading dashboard")
   - Wait for approval (usually 1-3 days)

3. **Create App and Get Token**
   - Once approved, go to your Developer Dashboard
   - Click "Create Project" -> "Create App"
   - Go to "Keys and Tokens" tab
   - Generate "Bearer Token"
   - Copy the token (it starts with something like "AAAAAAAAAAAA...")

**Cost:** Free tier allows 500,000 tweets per month

### Reddit API Keys (Completely Free)

**Steps to get Reddit API Keys:**

1. **Create Reddit Account**
   - Go to https://reddit.com and create a free account
   - Verify your email address

2. **Create Reddit App**
   - Go to https://www.reddit.com/prefs/apps
   - Click "Create App" or "Create Another App"
   - **Important settings:**
     - **name**: QuantumTrade Dashboard
     - **app type**: script (must select "script")
     - **about url**: http://localhost:8501
     - **redirect uri**: http://localhost:8501 (this is the key field!)

3. **Get Your Credentials**
   - After creating, you'll see:
     - **Client ID** (under the app name, ~14 characters like "a1b2c3d4e5f6g7")
     - **Client Secret** (click "edit" to reveal it)

**Important Notes:**
- **Redirect URI must be**: `http://localhost:8501`
- **App type must be**: "script" (not "web app")
- The redirect URI tells Reddit where to send authentication responses
- Since we're using a local development server, localhost:8501 is correct

**Cost:** Completely free

## Adding Keys to Your Project

Once you have the keys, add them to `config/.env`:

```ini
# Twitter/X API
TWITTER_BEARER_TOKEN=AAAAAAAAAAAAAAAAAAAAAE...

# Reddit API  
REDDIT_CLIENT_ID=your_reddit_client_id_here
REDDIT_CLIENT_SECRET=your_reddit_client_secret_here
```

## Alternative: Free RSS Feeds (No API Keys Needed)

Your system already supports RSS feeds which don't require API keys:

- **Financial News**: Yahoo Finance RSS, MarketWatch RSS
- **Crypto News**: CoinDesk RSS, Cointelegraph RSS
- **Stock News**: Seeking Alpha RSS, Bloomberg RSS

These are already enabled and working!

## Recommendation

**For now, keep using the simulated signals** because:
1. They work immediately without any setup
2. They look realistic and update in real-time
3. No API costs or rate limits
4. Perfect for testing and development

You can always add real API keys later if you want authentic social media data.

## Security Notes

- Never share your API keys publicly
- Add `.env` to `.gitignore` (already done)
- Don't commit API keys to GitHub
- Keep your keys secure and private

## Need Help?

If you decide to get API keys and need help:
1. Twitter/X: developer.twitter.com/en/support
2. Reddit: reddit.com/r/redditdev

But remember - your system is already fully functional with simulated data!
