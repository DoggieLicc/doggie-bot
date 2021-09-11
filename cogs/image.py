import io

import discord
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
from discord.ext import commands

from typing import List, Optional
from unsplash import Unsplash, Photo

import utils

utm_params = '?utm_source=discord_bot_doggie_bot&utm_medium=referral'


def invert_image(b: bytes, max_size) -> discord.File:
    image = Image.open(io.BytesIO(b)).convert('RGBA')

    r, g, b, a = image.split()
    rgb_image = Image.merge('RGB', (r, g, b))
    inverted_image = ImageOps.invert(rgb_image)
    r2, g2, b2 = inverted_image.split()

    image = Image.merge('RGBA', (r2, g2, b2, a))

    img_bytes = io.BytesIO()
    image = maybe_resize_image(image, max_size)
    image.save(img_bytes, 'png', optimize=True)

    img_bytes.seek(0)

    return discord.File(img_bytes, 'inverted.png')


def greyscale_image(b: bytes) -> discord.File:
    # Double convert for transparent gifs
    image = Image.open(io.BytesIO(b)).convert('RGBA').convert('LA')

    img_bytes = io.BytesIO()
    image.save(img_bytes, 'png')

    img_bytes.seek(0)

    return discord.File(img_bytes, 'greyscale.png')


def deepfry_image(b: bytes) -> discord.File:
    original = Image.open(io.BytesIO(b)).convert('P').convert('RGB')
    noise = Image.effect_noise(original.size, 20).convert('RGB')

    b = ImageEnhance.Brightness(original)
    image = b.enhance(1.1)
    c = ImageEnhance.Contrast(image)
    image = c.enhance(10)

    image = Image.blend(image, noise, 0.25).convert('P').convert('RGB')

    img_bytes = io.BytesIO()
    image.save(img_bytes, 'jpeg', quality=10, optimize=True)

    img_bytes.seek(0)
    return discord.File(img_bytes, 'deepfry.jpg')


def noise_image(b: bytes, alpha: float) -> discord.File:
    original = Image.open(io.BytesIO(b)).convert('RGBA')
    noise = Image.effect_noise(original.size, 20).convert('RGBA')

    image = Image.blend(original, noise, alpha)

    img_bytes = io.BytesIO()
    image.save(img_bytes, 'png', optimize=True)

    img_bytes.seek(0)
    return discord.File(img_bytes, 'noise.png')


def blur_image(b: bytes, radius: int) -> discord.File:
    image = Image.open(io.BytesIO(b)).convert('RGBA')
    image = image.filter(ImageFilter.GaussianBlur(radius))

    img_bytes = io.BytesIO()
    image.save(img_bytes, 'png', optimize=True)

    img_bytes.seek(0)
    return discord.File(img_bytes, 'blur.png')


def maybe_resize_image(image: Image, max_size: int) -> Image:
    b = io.BytesIO()
    image.save(b, 'png')

    while b.tell() > max_size:
        b.close()
        new_size = image.size[0] // 2, image.size[1] // 2
        image = image.resize(new_size, resample=Image.BILINEAR)
        b = io.BytesIO()
        image.save(b, 'png')

    return image


async def get_pic(url: str, ctx: utils.CustomContext, key: str) -> str:
    async with ctx.bot.session.get(url) as resp:
        data = await resp.json()

    return data[key]


async def furry_image(ctx, user: Optional[discord.User], endpoint: str, action: str, a2: str = None):
    if not user or user == ctx.author:
        msg = f'{ctx.author.mention} has no one to {action} :('
    elif user.bot:
        msg = f'{ctx.author.mention} tries to {action} a bot... sad :('
    else:
        msg = f'{ctx.author.mention} {action + "s" if not a2 else a2} {user.mention}!'

    url = await get_pic(f'https://v2.yiff.rest/furry/{endpoint}', ctx, key='images')
    return utils.create_embed(ctx.author, title=f'Furry {action}!', description=msg, image=url[0]['url'])


def check_unsplash():
    def predicate(ctx):
        if ctx.bot.config['unsplash_api_key']:
            return True

        raise utils.MissingAPIKey(
            'The Unsplash API key is missing!'
            'The owner of this bot can add an API key in `config.yaml`'
        )

    return commands.check(predicate)


class Images(commands.Cog):
    """Commands that have to do with images!"""

    def __init__(self, bot):
        self.bot: utils.CustomBot = bot

        if bot.config['unsplash_api_key']:
            self.unsplash = Unsplash(bot.config['unsplash_api_key'])
        else:
            self.unsplash = None

        self.cached_random_photos: List[Photo] = []

    @commands.group(invoke_without_command=True)
    async def unsplash(self, ctx: utils.CustomContext):
        await ctx.send_help(ctx.command)

    @check_unsplash()
    @unsplash.command(aliases=['rdm'])
    @commands.cooldown(10, 60, commands.BucketType.user)
    async def random(self, ctx: utils.CustomContext):
        """Gets a random photo from the Unsplash API!"""

        if not self.cached_random_photos:
            self.cached_random_photos = await self.unsplash.random(content_filter='high', count=30)

        image: Photo = self.cached_random_photos.pop(0)

        print(len(self.cached_random_photos))

        description = f'"{image.description or image.alt_description}"\n\n' \
                      f'*Photo by [{image.user.name}](https://unsplash.com/@{image.user.username}{utm_params}) on ' \
                      f'[Unsplash](https://unsplash.com/{utm_params})*'

        embed = utils.create_embed(
            ctx.author,
            title='Unsplash Image',
            description=description,
            image=image.urls.regular,
            color=image.color,
            timestamp=image.created_at
        )

        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(10, 60, commands.BucketType.user)
    async def fox(self, ctx: utils.CustomContext):
        """Gets a random fox from randomfox.ca"""

        url = await get_pic('https://randomfox.ca/floof/', ctx, key='image')
        embed = utils.create_embed(ctx.author, title=f'Random fox picture!:', image=url)

        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(10, 60, commands.BucketType.user)
    async def duck(self, ctx: utils.CustomContext):
        """Gets a random duck from random-d.uk"""

        url = await get_pic('https://random-d.uk/api/v2/quack', ctx, key='url')
        embed = utils.create_embed(ctx.author, title=f'Random duck picture!:', image=url)

        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(10, 60, commands.BucketType.user)
    async def dog(self, ctx: utils.CustomContext):
        """Gets a random dog from random.dog"""

        url = await get_pic('https://random.dog/woof.json?filter=mp4', ctx, key='url')
        embed = utils.create_embed(ctx.author, title=f'Random dog picture!:', image=url)

        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(10, 60, commands.BucketType.user)
    async def hug(self, ctx: utils.CustomContext, *, user: Optional[discord.User]):
        """Get picture of furries hugging, because why not?"""

        embed = await furry_image(ctx, user, 'hug', 'hug')

        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(10, 60, commands.BucketType.user)
    async def boop(self, ctx: utils.CustomContext, *, user: Optional[discord.User]):
        """Get picture of furries booping eachother, because why not?"""

        embed = await furry_image(ctx, user, 'boop', 'boop')

        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(10, 60, commands.BucketType.user)
    async def hold(self, ctx: utils.CustomContext, *, user: Optional[discord.User]):
        """Get picture of furries holding eachother, because why not?"""

        embed = await furry_image(ctx, user, 'hold', 'hold')

        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(10, 60, commands.BucketType.user)
    async def kiss(self, ctx: utils.CustomContext, *, user: Optional[discord.User]):
        """Get picture of furries kissing, because why not?"""

        embed = await furry_image(ctx, user, 'kiss', 'kiss', 'kisses')

        await ctx.send(embed=embed)

    @commands.command(aliases=['licc'])
    @commands.cooldown(10, 60, commands.BucketType.user)
    async def lick(self, ctx: utils.CustomContext, *, user: Optional[discord.User]):
        """Get picture of furries licking eachother, because why not?"""

        embed = await furry_image(ctx, user, 'lick', 'lick')

        await ctx.send(embed=embed)

    @commands.command()
    async def invert(self, ctx: utils.CustomContext, *, image: Optional[str]):
        """Inverts the colors of a specified image!

        The bot checks for images in this order:

        1. Attached image
        2. Attached image in replied message
        3. Emote in replied message (only if emote is by itself)
        4. Specified user's avatar
        5. Specified emote's image
        6. Invoker's avatar
        """

        # Use converter here so that it triggers even without given argument
        image_bytes = await utils.ImageConverter().convert(ctx, image)

        limit = ctx.guild.filesize_limit if ctx.guild else 8 * 1000 * 1000
        file = await self.bot.loop.run_in_executor(None, invert_image, image_bytes, limit)

        embed = utils.create_embed(
            ctx.author,
            title='Here\'s your inverted image:',
            image='attachment://inverted.png'
        )

        await ctx.send(embed=embed, file=file)

    @commands.command(aliases=['grayscale', 'grey', 'gray'])
    async def greyscale(self, ctx: utils.CustomContext, *, image: Optional[str]):
        """Greyscale the specified image!

        The bot checks for images in this order:

        1. Attached image
        2. Attached image in replied message
        3. Emote in replied message (only if emote is by itself)
        4. Specified user's avatar
        5. Specified emote's image
        6. Invoker's avatar
        """

        alias = ctx.invoked_with.lower()

        # Use converter here so that it triggers even without given argument
        image_bytes = await utils.ImageConverter().convert(ctx, image)

        file = await self.bot.loop.run_in_executor(None, greyscale_image, image_bytes)

        embed = utils.create_embed(
            ctx.author,
            title=f'Here\'s your {alias[:4]}scale image:',
            image='attachment://greyscale.png'
        )

        await ctx.send(embed=embed, file=file)

    @commands.command(aliases=['deep', 'fry'])
    async def deepfry(self, ctx: utils.CustomContext, *, image: Optional[str]):
        """Greyscale the specified image!

        The bot checks for images in this order:

        1. Attached image
        2. Attached image in replied message
        3. Emote in replied message (only if emote is by itself)
        4. Specified user's avatar
        5. Specified emote's image
        6. Invoker's avatar
        """

        # Use converter here so that it triggers even without given argument
        image_bytes = await utils.ImageConverter().convert(ctx, image)

        file = await self.bot.loop.run_in_executor(None, deepfry_image, image_bytes)

        embed = utils.create_embed(
            ctx.author,
            title=f'Here\'s your deepfried image:',
            image='attachment://deepfry.jpg'
        )

        await ctx.send(embed=embed, file=file)

    @commands.command()
    async def blur(self, ctx: utils.CustomContext, image: Optional[utils.ImageConverter], strength=5):
        """Blurs the specified image!

        The bot checks for images in this order:

        1. Attached image
        2. Attached image in replied message
        3. Emote in replied message (only if emote is by itself)
        4. Specified user's avatar
        5. Specified emote's image
        6. Invoker's avatar
        """

        if not image:
            image_bytes = await utils.ImageConverter().convert(ctx, image)
        else:
            image_bytes = image

        file = await self.bot.loop.run_in_executor(None, blur_image, image_bytes, abs(strength))

        embed = utils.create_embed(
            ctx.author,
            title=f'Here\'s your blurred image:',
            image='attachment://blur.png'
        )

        await ctx.send(embed=embed, file=file)

    @commands.command()
    async def noise(self, ctx: utils.CustomContext, image: Optional[utils.ImageConverter], strength=50):
        """Blurs the specified image! Strength should be in between 0 and 100

        The bot checks for images in this order:

        1. Attached image
        2. Attached image in replied message
        3. Emote in replied message (only if emote is by itself)
        4. Specified user's avatar
        5. Specified emote's image
        6. Invoker's avatar
        """

        if not 0 < strength <= 100:
            raise commands.BadArgument('Strength should be in between 0 and 100')

        strength /= 100

        if not image:
            image_bytes = await utils.ImageConverter().convert(ctx, image)
        else:
            image_bytes = image

        file = await self.bot.loop.run_in_executor(None, noise_image, image_bytes, strength)

        embed = utils.create_embed(
            ctx.author,
            title=f'Here\'s your noisy image:',
            image='attachment://noise.png'
        )

        await ctx.send(embed=embed, file=file)

    @dog.error
    @duck.error
    @fox.error
    @random.error
    @hug.error
    @unsplash.error
    async def api_error(self, ctx: utils.CustomContext, error):
        if isinstance(error, utils.MissingAPIKey):
            embed = utils.create_embed(
                ctx.author,
                title='Bot missing API key!',
                description=str(error),
                color=discord.Color.red()
            )

            return await ctx.send(embed=embed)

        embed = utils.create_embed(
            ctx.author,
            title='Error while using api!',
            description='For some reason an error happened, maybe the API is down?',
            color=discord.Color.red()
        )

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Images(bot))
