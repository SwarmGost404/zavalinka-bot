### IF YOU CAN USE DOCKER 
```bash
docker build -t zavalinka-bot .
docker run -d -p 5000:5000 --restart unless-stopped --name  zavalinka-bot zavalinka-bot 
```