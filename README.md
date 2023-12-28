# ibc-client-bot
## Note: This bot is not ready for production
This bot is used to check IBC client expiration time and alert when a client has time left smaller than 2days. It uses Cosmos REST endpoint to get information.
Since there are many IBC clients created by mistake, instead of scan all of the network clients, the bot only checks specific clients defined by env.

# Install
- setup required lib
```
pip3 install -r requirements.txt 
```
- create a bot using [BotFather](https://t.me/BotFather)
- setup env
```
export BOT_TOKEN=xxx 
export CLIENT_LIST=xxx # A list contain tuples (clientId, REST endpoint). Example: CLIENT_LIST=[('07-tendermint-13', 'https://rest.cosmos.directory/aura'),('07-tendermint-17', 'https://rest.cosmos.directory/aura')]
export CHANNEL_ID=xxx # Telegram channel id for sending alerts
export POLL_INTERVAL=xxx # for check new message in telegram
```
- run bot
```
python3 bot.py
```
# How to use

Command to interact with bot:
```
/client_status - Check the status of clients.
/help - Get help with available commands.
```
