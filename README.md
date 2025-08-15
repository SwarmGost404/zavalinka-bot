### IF YOU CAN USE DOCKER 
```bash
docker build -t zavalinka-bot .
docker run -d -e BOT_TOKEN="your_token" --restart unless-stopped --name  zavalinka-bot zavalinka-bot
```