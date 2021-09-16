import io

import discord
from PIL import Image, ImageOps, ImageFilter, ImageEnhance, UnidentifiedImageError
from discord.ext import commands
from typing import Optional

import utils


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


def brighten_image(b: bytes, intensity: float) -> discord.File:
    image = Image.open(io.BytesIO(b)).convert('RGBA')

    b = ImageEnhance.Brightness(image)
    image = b.enhance(intensity)

    img_bytes = io.BytesIO()
    image.save(img_bytes, 'png', optimize=True)

    img_bytes.seek(0)
    return discord.File(img_bytes, 'brighten.png')


def contrast_image(b: bytes, intensity: float) -> discord.File:
    image = Image.open(io.BytesIO(b)).convert('RGBA')

    c = ImageEnhance.Contrast(image)
    image = c.enhance(intensity)

    img_bytes = io.BytesIO()
    image.save(img_bytes, 'png', optimize=True)

    img_bytes.seek(0)
    return discord.File(img_bytes, 'contrast.png')


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


class Images(commands.Cog):
    """Commands for image manipulation!"""

    def __init__(self, bot):
        self.bot: utils.CustomBot = bot

    @commands.command()
    async def invert(self, ctx: utils.CustomContext, *, image: Optional[str]):
        """Inverts the colors of a specified image!

        **Steps for getting image:**
        1. Replied message -> Message steps
        2. Specified message -> Message steps
        3. Command's message -> Message steps
        4. Invoker's avatar

        **Message steps:**
        1. Attachment
        2. Sticker
        3. Embed image/thumbnail
        3. Specified user
        4. Specified emote
        5. Specified link
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

        **Steps for getting image:**
        1. Replied message -> Message steps
        2. Specified message -> Message steps
        3. Command's message -> Message steps
        4. Invoker's avatar

        **Message steps:**
        1. Attachment
        2. Sticker
        3. Embed image/thumbnail
        3. Specified user
        4. Specified emote
        5. Specified link
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
        """Deepfry the specified image!

        **Steps for getting image:**
        1. Replied message -> Message steps
        2. Specified message -> Message steps
        3. Command's message -> Message steps
        4. Invoker's avatar

        **Message steps:**
        1. Attachment
        2. Sticker
        3. Embed image/thumbnail
        3. Specified user
        4. Specified emote
        5. Specified link
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

        **Steps for getting image:**
        1. Replied message -> Message steps
        2. Specified message -> Message steps
        3. Command's message -> Message steps
        4. Invoker's avatar

        **Message steps:**
        1. Attachment
        2. Sticker
        3. Embed image/thumbnail
        3. Specified user
        4. Specified emote
        5. Specified link
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
        """Adds noise to specified image! Strength should be in between 0 and 100

        **Steps for getting image:**
        1. Replied message -> Message steps
        2. Specified message -> Message steps
        3. Command's message -> Message steps
        4. Invoker's avatar

        **Message steps:**
        1. Attachment
        2. Sticker
        3. Embed image/thumbnail
        3. Specified user
        4. Specified emote
        5. Specified link
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

    @commands.command(aliases=['bright', 'brightness', 'dark', 'darken'])
    async def brighten(self, ctx: utils.CustomContext, image: Optional[utils.ImageConverter], strength=1.25):
        """Brightens specified image! Passing in an strength less than 1 will darken it instead

        **Steps for getting image:**
        1. Replied message -> Message steps
        2. Specified message -> Message steps
        3. Command's message -> Message steps
        4. Invoker's avatar

        **Message steps:**
        1. Attachment
        2. Sticker
        3. Embed image/thumbnail
        3. Specified user
        4. Specified emote
        5. Specified link
        """

        if not 0 < strength:
            raise commands.BadArgument('Strength should be more than zero!')

        if not image:
            image_bytes = await utils.ImageConverter().convert(ctx, image)
        else:
            image_bytes = image

        file = await self.bot.loop.run_in_executor(None, brighten_image, image_bytes, strength)

        embed = utils.create_embed(
            ctx.author,
            title=f'Here\'s your brightened image:',
            image='attachment://brighten.png'
        )

        await ctx.send(embed=embed, file=file)

    @commands.command()
    async def contrast(self, ctx: utils.CustomContext, image: Optional[utils.ImageConverter], strength=1.25):
        """Adds contrast to specified image! Passing in an strength less than 1 will lower it instead

        **Steps for getting image:**
        1. Replied message -> Message steps
        2. Specified message -> Message steps
        3. Command's message -> Message steps
        4. Invoker's avatar

        **Message steps:**
        1. Attachment
        2. Sticker
        3. Embed image/thumbnail
        3. Specified user
        4. Specified emote
        5. Specified link
        """

        if not 0 < strength:
            raise commands.BadArgument('Strength should be more than zero!')

        if not image:
            image_bytes = await utils.ImageConverter().convert(ctx, image)
        else:
            image_bytes = image

        file = await self.bot.loop.run_in_executor(None, contrast_image, image_bytes, strength)

        embed = utils.create_embed(
            ctx.author,
            title=f'Here\'s your modified image:',
            image='attachment://contrast.png'
        )

        await ctx.send(embed=embed, file=file)

    async def cog_command_error(self, ctx: utils.CustomContext, error: Exception) -> None:
        embed = None

        if isinstance(error, commands.CommandInvokeError):
            error = error.original

        if isinstance(error, UnidentifiedImageError):
            embed = utils.create_embed(
                ctx.author,
                title='Error while making image!',
                description='The bot wasn\'t able to identify the image\'s format\n'
                            '**Note:** Links from sites like Tenor and GIPHY don\'t work, use the direct image url',
                color=discord.Color.red()
            )

        if embed:
            return await ctx.send(embed=embed)

        ctx.uncaught_error = True


def setup(bot):
    bot.add_cog(Images(bot))
