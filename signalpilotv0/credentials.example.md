# SignalPilot Credentials Template

Keep your real credentials in `signalpilotv0/credentials.md`. That file is ignored by Git.

```text
NEWS_API_KEY=your_newsapi_key
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini

ROBINHOOD_USERNAME=your_robinhood_email_or_username
ROBINHOOD_PASSWORD=your_robinhood_password
ROBINHOOD_MFA_CODE=replace_with_current_mfa_code
ROBINHOOD_TOTP_SECRET=replace_with_authenticator_secret
ROBINHOOD_SESSION_DIR=.robinhood_tokens

MANUAL_HOLDINGS=MU:10:88.50,NVDA:2:650.00
```

Only `ROBINHOOD_USERNAME` and `ROBINHOOD_PASSWORD` are required for Robinhood import. `MANUAL_HOLDINGS` can be used instead for local testing without broker login.

Do not commit real API keys, brokerage credentials, MFA codes, TOTP secrets, or token cache files.
