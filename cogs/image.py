import io

import discord
from PIL import Image, ImageOps, ImageFilter, ImageEnhance, UnidentifiedImageError, ImageDraw
from discord.ext import commands
from typing import Optional, List

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


def make_mask(colors, width, height):
    color_height = height / len(colors)

    color_image = Image.new('RGBA', (width, height))
    canvas = ImageDraw.Draw(color_image)

    for i, color in enumerate(colors):
        x1 = 0
        x2 = width

        y1 = i * color_height
        y2 = y1 + color_height

        cords = [(x1, y1), (x2, y2)]

        canvas.rectangle(cords, fill=color)

    return color_image


def make_flag(b: bytes, alpha: float, max_size: int, colors: List):
    image = Image.open(io.BytesIO(b)).convert('RGBA')

    mask = make_mask(colors, *image.size)
    blended_image = Image.blend(image, mask, alpha)
    resized_image = maybe_resize_image(blended_image, max_size)

    img_bytes = io.BytesIO()
    resized_image.save(img_bytes, 'png', optimize=True)
    img_bytes.seek(0)

    return discord.File(img_bytes, 'pride.png')


async def pride_flag(ctx: utils.CustomContext, image: Optional[bytes], transparency: int, colors: List):
    if not 0 < transparency <= 100:
        raise commands.BadArgument('Transparency should be in between 0 and 100')

    transparency /= 100

    if not image:
        image_bytes = await utils.ImageConverter().convert(ctx, image)
    else:
        image_bytes = image

    limit = ctx.guild.filesize_limit if ctx.guild else 8 * 1000 * 1000

    file = await ctx.bot.loop.run_in_executor(None, make_flag, image_bytes, transparency, limit, colors)

    embed = utils.create_embed(
        ctx.author,
        title=f'Here\'s your {ctx.command.name} image:',
        image='attachment://pride.png'
    )

    await ctx.send(embed=embed, file=file)


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

    @commands.command(aliases=['blurry'])
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

    @commands.command(aliases=['noisy'])
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

    @commands.command(aliases=['bright', 'brightness'])
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

    @commands.command(aliases=['rainbow'])
    async def gay(self, ctx: utils.CustomContext, image: Optional[utils.ImageConverter], transparency=50):
        """Adds the gay rainbow to image!

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

        gay_colors = [(255, 0, 24), (255, 165, 44), (255, 255, 65), (0, 128, 24), (0, 0, 249), (134, 0, 125)]

        await pride_flag(ctx, image, transparency, gay_colors)

    @commands.command(aliases=['trans'])
    async def transgender(self, ctx: utils.CustomContext, image: Optional[utils.ImageConverter], transparency=50):
        """Adds the transgender flag to image!

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

        trans_colors = [(91, 206, 250), (245, 169, 184), (255, 255, 255), (245, 169, 184), (91, 206, 250)]

        await pride_flag(ctx, image, transparency, trans_colors)

    @commands.command(aliases=['bi'])
    async def bisexual(self, ctx: utils.CustomContext, image: Optional[utils.ImageConverter], transparency=50):
        """Adds the bisexual flag to image!

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

        bi_colors = [(216, 9, 126), (216, 9, 126), (140, 87, 156), (36, 70, 142), (36, 70, 142)]

        await pride_flag(ctx, image, transparency, bi_colors)

    @commands.command(aliases=['lesb'])
    async def lesbian(self, ctx: utils.CustomContext, image: Optional[utils.ImageConverter], transparency=50):
        """Adds the lesbian flag to image!

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

        lesbian_colors = [
            (213, 45, 0), (239, 118, 39), (255, 154, 86), (255, 255, 255), (209, 98, 164), (181, 86, 144), (163, 2, 98)
        ]

        await pride_flag(ctx, image, transparency, lesbian_colors)

    @commands.command(aliases=['ace'])
    async def asexual(self, ctx: utils.CustomContext, image: Optional[utils.ImageConverter], transparency=50):
        """Adds the asexual flag to image!

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

        ace_colors = [(0, 0, 0), (164, 164, 164), (255, 255, 255), (129, 0, 129)]

        await pride_flag(ctx, image, transparency, ace_colors)

    @commands.command(aliases=['pan'])
    async def pansexual(self, ctx: utils.CustomContext, image: Optional[utils.ImageConverter], transparency=50):
        """Adds the pansexual flag to image!

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

        pan_colors = [(255, 28, 141), (255, 215, 0), (26, 179, 255)]

        await pride_flag(ctx, image, transparency, pan_colors)

    @commands.command(aliases=['nb', 'non-binary', 'non_binary'])
    async def nonbinary(self, ctx: utils.CustomContext, image: Optional[utils.ImageConverter], transparency=50):
        """Adds the non-binary flag to image!

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

        nb_colors = [(255, 244, 48), (255, 255, 255), (156, 89, 209), (0, 0, 0)]

        await pride_flag(ctx, image, transparency, nb_colors)

    @commands.command(aliases=['nonconforming'])
    async def gnc(self, ctx: utils.CustomContext, image: Optional[utils.ImageConverter], transparency=50):
        """Adds the gender nonconforming flag to image!

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

        gnc_colors = [
            (80, 40, 76), (150, 71, 122), (93, 150, 247), (255, 255, 255), (93, 150, 247), (150, 71, 122), (80, 40, 76)
        ]

        await pride_flag(ctx, image, transparency, gnc_colors)

    @commands.command(aliases=['aro'])
    async def aromantic(self, ctx: utils.CustomContext, image: Optional[utils.ImageConverter], transparency=50):
        """Adds the aromantic flag to image!

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

        aromantic_colors = [(58, 166, 63), (168, 212, 122), (255, 255, 255), (170, 170, 170), (0, 0, 0)]

        await pride_flag(ctx, image, transparency, aromantic_colors)

    @commands.command(aliases=['gq'])
    async def genderqueer(self, ctx: utils.CustomContext, image: Optional[utils.ImageConverter], transparency=50):
        """Adds the genderqueer flag to image!

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

        genderqueer_colors = [(181, 126, 220), (255, 255, 255), (73, 128, 34)]

        await pride_flag(ctx, image, transparency, genderqueer_colors)

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
