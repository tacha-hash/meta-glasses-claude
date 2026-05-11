# Meta Ray-Ban (Display) Glasses + Claude Integration Project

This project integrates the Meta Ray-Ban / Ray-Ban Display glasses with a WhatsApp bot, leveraging Anthropic Claude
(via the official Anthropic SDK with tool_use), Redis for data management, Notion for note-taking, and Google Calendar
for event and reminder management.

**Why WhatsApp?** Meta's Wearables Device Access Toolkit (DAT) does NOT expose the Display HUD. The only way to push
text onto the HUD today is through Meta-owned notification channels (WhatsApp, Messenger, iMessage, Calendar). By
binding Claude to a WhatsApp number, every message sent from the glasses ("Hey Meta, send a message to Claude ...")
becomes a Claude prompt, and Claude's reply appears on the HUD as an incoming WhatsApp notification.

Forked from [josancamon19/meta-glasses-gemini](https://github.com/josancamon19/meta-glasses-gemini) — Gemini swapped
for Claude. Default model: `claude-opus-4-7`.

**Auth**: Uses the local `claude` CLI (Claude Code) via subprocess — no API key needed. Just `claude login` once
with your Claude Max account and the bot inherits your subscription.

## Getting Started

### Prerequisites

- Python 3.x
- pip for Python package installation

### Installation

1. Clone this repository to your local machine.
2. Navigate to the project directory.
3. Install the required Python packages:

    ```sh
    pip install -r requirements.txt
    ```
4. Run the project:

    ```sh
    uvicorn main:app --reload
    ```

### Environment Variables

You need to set the following environment variables in a `.env` file within the project directory:

```dotenv
WHATSAPP_AUTH_TOKEN=
WHATSAPP_PHONE_NUMBER=
WHATSAPP_WEBHOOK_VERIFICATION_TOKEN=
REDIS_DB_HOST=
REDIS_DB_PORT=
REDIS_DB_PASSWORD=
CLAUDE_MODEL=claude-opus-4-7
CLAUDE_CLI=claude
CLAUDE_CWD=/tmp
CLOUD_STORAGE_BUCKET_NAME=
NOTION_INTEGRATION_SECRET=
NOTION_DATABASE_ID=
SERPER_DEV_API_KEY=
CRAWLBASE_API_KEY=
OAUTH_CREDENTIALS_ENCODED=
```

- `WHATSAPP_AUTH_TOKEN`: Create an app at [Meta for Developers](https://developers.facebook.com/) and retrieve the
  WhatsApp authentication token.
- `WHATSAPP_PHONE_NUMBER`: The phone number associated with your WhatsApp API.
- `WHATSAPP_WEBHOOK_VERIFICATION_TOKEN`: Set a verification token of your choice and use it in the Meta for Developers
  dashboard to verify the webhook.
- `REDIS_DB_HOST`, `REDIS_DB_PORT`, `REDIS_DB_PASSWORD`: Credentials for your Redis database. This project uses Redis
  for managing data, including storing images for analysis.
- `CLAUDE_MODEL`: (Optional) Override the default Claude model. Defaults to `claude-opus-4-7`.
- `CLAUDE_CLI`: (Optional) Path to the `claude` binary. Defaults to `claude` (assumed on PATH).
- `CLAUDE_CWD`: (Optional) Working directory for the `claude` subprocess. Defaults to `/tmp` so the bot does NOT inherit any project `CLAUDE.md` / MCP config.

Make sure you've run `claude login` once with your Claude Max account on the machine running this bot.
- `CLOUD_STORAGE_BUCKET_NAME`: The name of your Google Cloud Storage bucket for storing images and data.
- `NOTION_INTEGRATION_SECRET`, `NOTION_DATABASE_ID`: Create a Notion integration and a database with fields (Title,
  Category, Content, Created At, Completed). Share the database with the integration.
- `SERPER_DEV_API_KEY`, `CRAWLBASE_API_KEY`: Obtain these API keys from the respective websites to enable advanced
  search and data retrieval functionalities.
- OAUTH_CREDENTIALS_ENCODED: Base64 encode your Google OAuth credentials and set them here.

### Additional Configuration

- **Google Cloud Platform Credentials**: Place your `google-credentials.json` file in the project root. This file should
  contain credentials for your GCP project.
- **Google OAuth Token**: Ensure you have a `credentials.json` file for OAuth to enable Google Calendar integrations.
  Follow the Google Calendar API documentation to obtain this token.
- **Create a Meta App**: Create an app at [Meta for Developers](https://developers.facebook.com/) to obtain the WhatsApp
  API credentials, and setup the webhook to your URL.