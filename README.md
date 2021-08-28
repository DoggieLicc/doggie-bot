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

# Bot commands!

**help - [command]**: Shows this bot's commands, if a command is specified then info for that command is shown! 

## Information commands:

**server**: Lists info for the current guild

**user - [user]**: Shows information about the user specified, if no user specified then it returns info for invoker

**avatar - [user]**: Shows user's avatar using their ID or name

**invite - \<invite>**: Shows info for an invite using a invite URL or its code

**channel - \<channel>**: Shows info for the channel specified using channel mention or ID

**role - \<role>**: Shows info for the role specified using role mention or ID

**emote - \<emoji>**: Shows info of emote using the emote ID or emote itself

**token - \<token>**: Shows info of an account/bot token! (Don't use valid tokens in public servers!)

**message - \<message>**: Gets information for a Discord Message!

**color - \<color>**: Gets info for a color! You can specify a member, role, or color.

**whois - \<domain>**: Does a WHOIS lookup on a domain!

**wikipedia - \<search>**: Looks up Wikipedia articles by their title!

## Moderation commands:

**ban - \<users>... [reason]**: Ban members who broke the rules! You can specify multiple members in one command.

**unban - \<users>... [reason]**: Unban banned users with their User ID, you can specify multiple people to be unbanned.

**softban - \<members>... [reason]**: Bans then unbans the specified users, which deletes their recent messages and 'kicks' them.

**kick - \<members>... [reason]**: Kick members who broke the rules! You can specify multiple members in one command.

**rename - [members]... \<nickname>**: Renames users to a specified name

**mute - [members]... [reason=No reason specified]**: Gives the configured mute role to members!

**unmute - [members]... [reason=No reason specified]**: Removes the configured mute role from members!

**purge - [users]... [amount=20]**: Deletes multiple messages from the current channel, you can specify users that it will delete messages from.

**asciify - [members]...**: Replace weird unicode letters in nicknames with normal ASCII text!

**snipe - [channel] [user]**: Shows recent deleted messages! You can specify an user to get deleted messages from.

## Reminder commands:

**remind - \<duration> [channel] \<reminder>**: Add a reminder to be sent to you or a channel after a specified duration!

**reminders**: Shows your active reminders that you made!

**cancel - \<reminder_id>**: Cancels and deletes a reminder using its ID!

## Misc commands:

**info**: Shows information for the bot!

**suggest - \<suggestion>**: Send a suggestion or bug report to the bot owner!

**source - [command]**: Look at the code of this bot!

## Game commands:

**minecraft - \<account>**: Gets info of minecraft accounts using current username or their UUID

**osu - \<subcommand>**: 

## Utility commands:

**recentjoins**: Shows the most recent joins in the current server

**selfbot - [users]...**: Creates a fake Nitro giveaway to catch a selfbot (Automated user accounts which auto-react to giveaways)

**hoisters - \<subcommand>**: Shows a list of members who have names made to 'hoist' themselves to the top of the member list!

**steal - [emotes]...**: Adds the specified emotes to your server!

**newacc**: Shows the newest accounts in this server!

## Image commands:

**unsplash - \<subcommand>**: Get an image from the Unsplash API

**fox**: Gets a random fox from randomfox.ca

**duck**: Gets a random duck from random-d.uk

**dog**: Gets a random dog from random.dog

## Configuration commands:

**config - \[subcommand]**: Shows the current configuration for this server!

**logging - \<flags>...**: Sets the log channels for this server! `help logging` for help with flags format