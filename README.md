[![Discord](https://discord.com/api/guilds/815073622213394473/widget.png?style=shield)](https://discord.gg/Uk6fg39cWn)

# doggie-bot
A multipurpose bot that combines Info Bot, Mini Mod, and Reminder Friend's commands, and more.

This bot runs on the master branch of [discord.py](https://github.com/Rapptz/discord.py)

## Invite this bot:
[Invite Link](https://discord.com/oauth2/authorize?client_id=875185463651078194&scope=bot&permissions=2550164614), it's recommended to not remove any permissions, as some or all commands may stop working

## Hosting guide:

1. Create a bot account in the Discord Dev portal and invite it to your server. - [Guide](https://discordpy.readthedocs.io/en/latest/discord.html)

2. Make sure to enable member intents too. - [Example](https://discordpy.readthedocs.io/en/latest/intents.html#privileged-intents)

3. Install python 3.8 or higher if you don't have it already. - [Download](https://www.python.org/downloads/)

4. Install dependencies in `requirements.txt`
    - You should probably make a venv first
    - `pip install -r requirements.txt`

5. Paste your bot token in `config.yaml`, right after `bot_token: `

    - You must also fill in `osu_client_id`, `osu_client_secret`, and `unsplash_api_key` if you want those commands to work
    
6. Run bot and have fun!