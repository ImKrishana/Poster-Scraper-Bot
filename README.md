## Deployment

<details>
  <summary><strong>Heroku (One-Click Deploy)</strong></summary>

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/ImKrishana/Poster-Scraper-Bot/tree/deploy)

</details>

<details>
  <summary><strong>Render (One-Click Deploy)</strong></summary>
  
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/ImKrishana/Poster-Scraper-Bot&branch=deploy)

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

</details><details>
  <summary><strong>Heroku CLI</strong></summary>1. Login to Heroku
   
   heroku login

2. Clone Repository & Switch to Deploy Branch
   
   git clone https://github.com/ImKrishana/Poster-Scraper-Bot psb
cd psb
git checkout deploy

3. Create "config.py" File
   
   nano config.py
   
   Add the required variables:
   
   BOT_TOKEN = "your_bot_token"
TELEGRAM_API = 12345678
TELEGRAM_HASH = "your_telegram_api_hash"
DATABASE_URL = "your_mongodb_url"
OWNER_ID = 123456789
UPSTREAM_REPO = "https://github.com/ImKrishana/Poster-Scraper-Bot"
UPSTREAM_BRANCH = "main"

4. Commit Changes
   
   git add . -f
git commit -m "echo"

5. Create Heroku App
   
   heroku create YOUR-APP-NAME

6. Add Remote
   
   heroku git:remote -a YOUR-APP-NAME

7. Set Container Stack
   
   heroku stack:set container

8. Deploy
   
   git push heroku deploy:main -f

9. Check Logs
   
   heroku logs --tail

</details>
```
