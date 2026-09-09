Powerful telegram bot that scrape Posters from multiple OTT platforms & Bypass direct download links from cloud sites.

## Supported Platforms

<details>
<summary><strong>OTT & Streaming Platforms</strong></summary>

- Crunchyroll
- BookMyShow
- Netflix
- iQIYI
- MX Player
- Amazon Prime Video
- Airtel Xstream
- ZEE5
- Ultra
- YouTube
- Viki
- Youku
- WeTV
- Hulu
- TicketNew
- SonyLIV
- ShemarooMe
- Apple TV+
- Chaupal
- Aha
- VivaMax
- Plex TV
- Atrangii
- Sun NXT
- Playflix
- Lionsgate Play
- Eros Now
- Hungama
- Hoichoi
- Jojo
- Ultra Jhakaas
- MUBI
- Saina Play
- Addatimes
- AaoNXT
- Viu
- Dangal
- Tata Play
- Tubi

</details>

## Variables 
<details>
<summary><strong>Click Here</strong></summary>

### Required Variables

- **`API_ID`** - Get this from [my.telegram.org](https://my.telegram.org)
- **`API_HASH`** - Get this from [my.telegram.org](https://my.telegram.org)
- **`BOT_TOKEN`** - Get this from [@BotFather](https://t.me/BotFather)
- **`DATABASE_URL`** - MongoDB database URL
- **`OWNER_ID`** - Your Telegram user ID
- **`UPSTREAM_REPO`** - Your forked repository URL for auto update
- **`UPSTREAM_BRANCH`** - Repository branch name
  
### Optional Variables

- **`AUTHORIZED_CHATS`** - Comma-separated Telegram chat IDs where the bot is authorized to work
- **`AUTHOR_NAME`** - Name displayed as the author of generated content
- **`AUTHOR_URL`** - Telegram or website URL associated with the author
- **`BASE_URL`** - Base URL used for web access or external services
- **`BASE_URL_PORT`** - Port used by the base URL/web server
- **`CMD_SUFFIX`** - Suffix added to bot commands
- **`DEFAULT_LANG`** - Default language used by the bot
- **`POSTER_API_URL`** - API URL used for generating or fetching posters
- **`POSTER_API_TOKEN`** - Authentication token for the poster API
- **`PROTECTED_API`** - Shortener Bypass API endpoint or URL
- **`PUBLIC_MODE`** - Enables or disables public mode for the bot
- **`SUDO_USERS`** - Telegram user IDs with sudo/admin-level access
- **`SET_COMMANDS`** - Automatically sets bot commands in Telegram
- **`TG_PROXY`** - Telegram proxy configuration
- **`TIMEZONE`** - Timezone used by the bot for date and time operations
- **`UPDATE_PKGS`** - Automatically updates required Python packages
- **`VERIFY_TIMEOUT`** - Timeout duration for user verification


</details>

## Deployment

<details>
  <summary><strong>Heroku (One-Click Deploy)</strong></summary>

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/ImKrishana/Poster-Scraper-Bot)

</details>

<details>
  <summary><strong>Render (One-Click Deploy)</strong></summary>
  
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](
https://render.com/deploy?repo=https://github.com/ImKrishana/Poster-Scraper-Bot&branch=deploy
)

</details>

<details>
  <summary><strong>VPS/Locally</strong></summary>

### Prerequisites
Before starting, ensure you have:
- Docker installed ([Installation Guide](https://docs.docker.com/engine/install/))
- Docker Compose installed ([Installation Guide](https://docs.docker.com/compose/install/))

### Installation Steps

1. **Clone the Repository**
   ```bash
   git clone https://github.com/ImKrishana/Poster-Scraper-Bot psb
   cd psb
   ```

2. **Setup Configuration File**
   
   Create `config.env` file:
   ```bash
   nano config.env
   ```
   
   Add the required variables (replace with your actual values):
   ```env
   API_ID=your_api_id
   API_HASH=your_api_hash
   BOT_TOKEN=your_bot_token
   DATABASE_URL=your_mongodb_url
   OWNER_ID=your_telegram_user_id
   ```
   
   Save and exit (`Ctrl + X`, then `Y`, then `Enter`)

3. **Start the Bot**
   ```bash
   docker-compose up -d
   ```
   
   The bot will start in detached mode (background).

4. **Verify Bot is Running**
   ```bash
   docker-compose ps
   ```
   
   You should see `poster-bot` with status "Up".

### Xtras

**View Live Logs:**
```bash
docker-compose logs -f
```
Press `Ctrl + C` to exit logs

**Stop the Bot:**
```bash
docker-compose down
```

**Restart the Bot:**
```bash
docker-compose restart
```

**Update and Restart:**
```bash
git pull
docker-compose up -d --build
```

**Stop and Remove Everything:**
```bash
docker-compose down -v
```
</details>

<details>
  <summary><strong>Heroku CLI</strong></summary>

1. **Login to Heroku**
   ```bash
   heroku login
   ```

2. **Clone Repository & switch to deploy branch**
   ```bash
   git clone https://github.com/ImKrishana/Poster-Scraper-Bot psb && cd psb && git checkout deploy
   ```

3. **Create config.env file**
   ```bash
   nano config.env
   ```
   Add required variables:
   ```env
   API_ID=your_api_id
   API_HASH=your_api_hash
   BOT_TOKEN=your_bot_token
   DATABASE_URL=your_database_url
   OWNER_ID=your_owner_id
   UPSTREAM_REPO=https://github.com/ImKrishana/Poster-Scraper-Bot
   UPSTREAM_BRANCH=main
   ```

4. **Commit Changes**
   ```bash
   git add . -f
   git commit -m "echo"
   ```

5. **Create Heroku App**
   ```bash
   heroku create YOUR-APP-NAME
   ```

6. **Add Remote**
   ```bash
   heroku git:remote -a YOUR-APP-NAME
   ```

7. **Create Container**
   ```bash
   heroku stack:set container
   ```

8. **Deploy**
   ```bash
   git push heroku deploy:main -f
   ```

9. **Check Logs**
   ```bash
   heroku logs --tail
   ```

</details>

## Admin Side

<details>
<summary><strong>Authorization Management</strong></summary>

### Authorize Users/Chats

Grant access to users or groups to use the bot.

Authorizes the current chat.
```
/authorize
```
**Authorize Specific User/Chat:**
```
/authorize CHAT_ID or USER_ID
```
**Authorize Topic in Group:**
```
/authorize CHAT_ID|TOPIC_ID
```

---

### Unauthorize Users/Chats

Remove access from authorized users or groups.

Unauthorizes the current chat.
```
/unauthorize
```

**Unauthorize Specific User/Chat:**
```
/unauthorize CHAT_ID
```

**Unauthorize Topic:**
```
/unauthorize CHAT_ID|TOPIC_ID
```

</details>

<details>
<summary><strong>Broadcast System</strong></summary>

**Forward with Tag:**
Broadcast with original sender tag.
```
/broadcast -f
```

**Silent Broadcast:**
Broadcast without notification sound.
```
/broadcast -q
```

**Combined Options:**
```
/broadcast -f -q
```

---

### Edit Broadcasts

Edit previously sent broadcast messages.
```
/broadcast BROADCAST_ID -e
```

---

### Delete Broadcasts

Delete broadcast messages from all users.

```
/broadcast BROADCAST_ID -d
```

---

### Broadcast Options

| Flag | Description |
|------|-------------|
| `-f` or `-forward` | Forward message with tag |
| `-q` or `-quiet` | Send without notification |
| `-e` or `-edit` | Edit existing broadcast |
| `-d` or `-delete` | Delete broadcast |

**Important Notes:**
- Broadcast IDs are valid only until bot restart
- After restart, you cannot edit/delete old broadcasts
- Forwarded messages can only be deleted, not edited
- Stats show: Total, Success, Blocked, Deleted, Failed

</details>

## Extras

Live bot can be found here

**Demo Bot:** [@PostersProBot](https://t.me/PostersProBot)

U can test all features and commands to see how it works!

<details>
  <summary><strong>Disclaimer</strong></summary>

This bot is developed strictly for **educational and research purposes only**.

</details>

---

[![License](https://img.shields.io/github/license/ImKrishana/Poster-Scraper-Bot)](https://github.com/ImKrishana/Poster-Scraper-Bot/blob/main/LICENSE)
[![Telegram](https://img.shields.io/badge/Telegram-26A5E4?logo=telegram&logoColor=white)](https://t.me/LeechBots)

If you like this project, don't forget to give it a Star !

**Developer:** [The Zake](https://t.me/TheZake)
