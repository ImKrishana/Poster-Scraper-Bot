## Deployment Guide 

<details>
  <summary><strong>Heroku (One-Click Deploy)</strong></summary>

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/ImKrishana/Poster-Scraper-Bot/tree/deploy)

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

2. Setup Configuration File
   
   Create "config.py" file:
   
   nano config.py
   
   Add the required variables:
   
   BOT_TOKEN = "your_bot_token"
TELEGRAM_API = 12345678
TELEGRAM_HASH = "your_telegram_api_hash"
DATABASE_URL = "your_mongodb_url"
OWNER_ID = 123456789
UPSTREAM_REPO = "https://github.com/ImKrishana/Poster-Scraper-Bot"
UPSTREAM_BRANCH = "main"
   
   Save and exit ("Ctrl + X", then "Y", then "Enter").

3. Start the Bot
   
   docker-compose up -d
   
   The bot will start in detached mode (background).

4. Verify Bot is Running
   
   docker-compose ps
   
   You should see the bot container with status "Up".

Xtras

View Live Logs:

docker-compose logs -f

Press "Ctrl + C" to exit logs.

Stop the Bot:

docker-compose down

Restart the Bot:

docker-compose restart

Update and Restart:

git pull
docker-compose up -d --build

Stop and Remove Everything:

docker-compose down -v

</details>
```

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
