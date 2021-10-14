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

## How to use this bot:
Use `doggie.command` to use a command.

Most commands also need you to put an argument after the command, such as `doggie.user @Doggie`
You will know which arguments to put in a command by looking at its command signature!

```properties
<user> - User is a required argument
[user] - User is an optional argument
<users...> - You can specify more than one user
[amount=100] - Amount is optional, and 100 is the default
̶c̶o̶m̶m̶a̶n̶d - You can't run this command
```

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

**osu - \<subcommand>**: Gets info for osu! accounts and beatmaps!

## Utility commands:

**recentjoins**: Shows the most recent joins in the current server

**selfbot - [users]...**: Creates a fake Nitro giveaway to catch a selfbot (Automated user accounts which auto-react to giveaways)

**hoisters - \<subcommand>**: Shows a list of members who have names made to 'hoist' themselves to the top of the member list!

**steal - [emotes]...**: Adds the specified emotes to your server!

**newacc**: Shows the newest accounts in this server!

**poll - [timeout=600] \<question> [options...]**: Makes a poll that anyone can vote on! Use quotes to separate multi-word question and options

## Images commands:

**invert - [image]**: Inverts the colors of a specified image!

**greyscale - [image]**: Greyscale the specified image!

**deepfry - [image]**: Deepfry the specified image!

**blur - [image] [strength=5]**: Blurs the specified image!

**noise - [image] [strength=50]**: Adds noise to specified image! Strength should be in between 0 and 100

**brighten - [image] [strength=1.25]**: Brightens specified image! Passing in an strength less than 1 will darken it instead

**contrast - [image] [strength=1.25]**: Adds contrast to specified image! Passing in an strength less than 1 will lower it instead

**rotate - [image] [angle=90]**: Rotates an image! Positive number for clockwise, negative for counter-clockwise

**pride - [image] [transparency=50]**: Adds the pride rainbow to image!

**gay - [image] [transparency=50]**: Adds the gay rainbow to image!

**transgender - [image] [transparency=50]**: Adds the transgender flag to image!

**bisexual - [image] [transparency=50]**: Adds the bisexual flag to image!

**lesbian - [image] [transparency=50]**: Adds the lesbian flag to image!

**asexual - [image] [transparency=50]**: Adds the asexual flag to image!

**pansexual - [image] [transparency=50]**: Adds the pansexual flag to image!

**nonbinary - [image] [transparency=50]**: Adds the non-binary flag to image!

**gnc - [image] [transparency=50]**: Adds the gender nonconforming flag to image!

**aromantic - [image] [transparency=50]**: Adds the aromantic flag to image!

**genderqueer - [image] [transparency=50]**: Adds the genderqueer flag to image!

## Configuration commands:

**config - \<subcommand>**: Shows the current configuration for this server!

**logging - \<flags>...**: Sets the log channels for this server! `help logging` for help with flags format

## Random commands:

**random - \<subcommand>**: Commands that choose something random!

**unsplash - \<subcommand>**: Commands that have to do with the Unsplash API!

**fox**: Gets a random fox from randomfox.ca

**duck**: Gets a random duck from random-d.uk

**dog**: Gets a random dog from random.dog

**hug - [user]**: Get picture of furries hugging, because why not?

**boop - [user]**: Get picture of furries booping eachother, because why not?

**hold - [user]**: Get picture of furries holding eachother, because why not?

**kiss - [user]**: Get picture of furries kissing, because why not?

**lick - [user]**: Get picture of furries licking eachother, because why not?