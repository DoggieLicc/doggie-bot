[![Discord](https://discord.com/api/guilds/1298552274896949339/widget.png?style=shield)](https://discord.gg/d7dgReCnRR)

# doggie-bot
A multipurpose bot with moderation, utility, reminder, image commands, and more.

This bot runs on [discord.py](https://github.com/Rapptz/discord.py)

## Invite this bot:
[Invite Link](https://discord.com/oauth2/authorize?client_id=930596365426360421), it's recommended to not remove any permissions, as some or all commands may stop working

## Hosting guide (docker compose, recomended):

1. Create a bot account in the Discord Dev portal and invite it to your server. - [Guide](https://discordpy.readthedocs.io/en/latest/discord.html)

2. Make sure to enable member intents too. - [Example](https://discordpy.readthedocs.io/en/latest/intents.html#privileged-intents)

3. Install Docker Engine + docker compose if you don't have it already - [Docs](https://docs.docker.com/engine/install/)

4. Use the `docker-compose.yml` file as a template, and fill in the `BOT_TOKEN` variable with your bot token (or in a `.env` file)
    - You must also set `OSU_CLIENT_ID`, `OSU_CLIENT_SECRET`, `UNSPLASH_API_KEY`, and `SAUCENAO_API_KEY` if you want those commands to work

5. Use `docker compose up -d --build` to start the bot, and have fun!

## Hosting guide:

1. Create a bot account in the Discord Dev portal and invite it to your server. - [Guide](https://discordpy.readthedocs.io/en/latest/discord.html)

2. Make sure to enable member intents too. - [Example](https://discordpy.readthedocs.io/en/latest/intents.html#privileged-intents)

3. Install python 3.14 or higher if you don't have it already. - [Download](https://www.python.org/downloads/)

4. Install dependencies in `requirements.txt`
    - You should probably make a venv first
    - `pip install -r requirements.txt`

5. Paste your bot token in `config.yaml`, right after `bot_token: `

    - You must also fill in `osu_client_id`, `osu_client_secret`, `unsplash_api_key`, and `saucenao_api_key` if you want those commands to work
    
6. Run bot and have fun!

# Bot commands!

## How to use this bot:
Use `doggie.command` to use a command.
You can also use slash commands.

Most commands also need you to put an argument after the command, such as `doggie.user @Doggie`
You will know which arguments to put in a command by looking at its command signature!

```properties
<user> - User is a required argument
[user] - User is an optional argument
<users...> - You can specify more than one user
[amount=100] - Amount is optional, and 100 is the default
̶c̶o̶m̶m̶a̶n̶d - You can't run this command
```
