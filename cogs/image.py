import discord
import io
import utils

from discord.ext import commands
from PIL import Image, ImageOps, ImageFilter, ImageEnhance, UnidentifiedImageError, ImageDraw, ImageFont, ImageSequence
from typing import Optional, List


def image_to_file(image: Image, extension) -> discord.File:
    img_bytes = io.BytesIO()
    image.save(img_bytes, extension, optimize=True)

    img_bytes.seek(0)

    return discord.File(img_bytes, f'image.{extension}')


def hande_gif_images(func, b: bytes, *args, **kwargs):
    im = Image.open(io.BytesIO(b))
    frames = []
    new = io.BytesIO()

    for frame in ImageSequence.Iterator(im):
        frame = frame.convert('RGBA')
        frame = func(frame, *args, **kwargs)
        frames.append(frame)

    if len(frames) == 1:
        return image_to_file(frames[0], 'png')

    frames[0].save(new, 'gif', append_images=frames[1:], save_all=True)
    new.seek(0)

    return discord.File(new, 'image.gif')


def invert_image(image: Image):
    r, g, b, a = image.split()
    rgb_image = Image.merge('RGB', (r, g, b))
    inverted_image = ImageOps.invert(rgb_image)
    r2, g2, b2 = inverted_image.split()

    image = Image.merge('RGBA', (r2, g2, b2, a))

    return image


def greyscale_image(image: Image):
    image = image.convert('LA')

    return image


def deepfry_image(image: Image):
    original = image.convert('P').convert('RGB')
    noise = Image.effect_noise(original.size, 20).convert('RGB')

    b = ImageEnhance.Brightness(original)
    image = b.enhance(1.1)
    c = ImageEnhance.Contrast(image)
    image = c.enhance(10)

    image = Image.blend(image, noise, 0.25).convert('P').convert('RGB')

    img_bytes = io.BytesIO()
    image.save(img_bytes, 'png', quality=10, optimize=True)

    img_bytes.seek(0)
    return image


def noise_image(image: Image, alpha: float):
    noise = Image.effect_noise(image.size, 20).convert('RGBA')

    image = Image.blend(image, noise, alpha)

    return image


def blur_image(image: Image, radius: int):
    image = image.filter(ImageFilter.GaussianBlur(radius))

    return image


def brighten_image(image: Image, intensity: float):
    b = ImageEnhance.Brightness(image)
    image = b.enhance(intensity)

    return image


def contrast_image(image: Image, intensity: float):
    c = ImageEnhance.Contrast(image)
    image = c.enhance(intensity)

    return image


def rotate_image(image: Image, angle: int):
    image = image.rotate(-angle, expand=True)

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


def make_flag(image: Image, alpha: float, colors: List):
    mask = make_mask(colors, *image.size)
    blended_image = Image.blend(image, mask, alpha)

    return blended_image


async def pride_flag(ctx: utils.CustomContext, image: Optional[bytes], transparency: int, colors: List):
    if not 0 < transparency <= 100:
        raise commands.BadArgument('Transparency should be in between 0 and 100')

    transparency /= 100

    if not image:
        image_bytes = await utils.ImageConverter().convert(ctx, image)
    else:
        image_bytes = image

    file = await ctx.bot.loop.run_in_executor(None, hande_gif_images, make_flag, image_bytes, transparency, colors)

    embed = utils.create_embed(
        ctx.author,
        title=f'Here\'s your {ctx.command.name} image:',
        image=f'attachment://{file.filename}'
    )

    await ctx.send(embed=embed, file=file)


def add_impact(image: Image, top_text: str, bottom_text: str):
    top_text = top_text.upper()
    bottom_text = bottom_text.upper() if bottom_text else None

    if image.width < 256:
        height = int(256 * (image.height / image.width))
        image = image.resize((256, height))

    impact = ImageFont.truetype('assets/impact.ttf', image.width // 10)
    canvas = ImageDraw.Draw(image)

    xpos = image.width / 2

    font_kwargs = {
        'fill': (255, 255, 255),
        'font': impact,
        'align': 'center',
        'stroke_width': image.width / 10 / 10,
        'stroke_fill': (0, 0, 0)
    }

    canvas.multiline_text(
        xy=(xpos, 0),
        text=top_text,
        anchor='ma',
        **font_kwargs
    )

    if bottom_text:
        canvas.multiline_text(
            xy=(xpos, image.height),
            text=bottom_text,
            anchor='md',
            **font_kwargs
        )

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

        file = await self.bot.loop.run_in_executor(None, hande_gif_images, invert_image, image_bytes)

        embed = utils.create_embed(
            ctx.author,
            title='Here\'s your inverted image:',
            image=f'attachment://{file.filename}'
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

        file = await self.bot.loop.run_in_executor(None, hande_gif_images, greyscale_image, image_bytes)

        embed = utils.create_embed(
            ctx.author,
            title=f'Here\'s your {alias[:4]}scale image:',
            image=f'attachment://{file.filename}'
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

        file = await self.bot.loop.run_in_executor(None, hande_gif_images, deepfry_image, image_bytes)

        embed = utils.create_embed(
            ctx.author,
            title=f'Here\'s your deepfried image:',
            image=f'attachment://{file.filename}'
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

        file = await self.bot.loop.run_in_executor(None, hande_gif_images, blur_image, image_bytes, abs(strength))

        embed = utils.create_embed(
            ctx.author,
            title=f'Here\'s your blurred image:',
            image=f'attachment://{file.filename}'
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

        file = await self.bot.loop.run_in_executor(None, hande_gif_images, noise_image, image_bytes, strength)

        embed = utils.create_embed(
            ctx.author,
            title=f'Here\'s your noisy image:',
            image=f'attachment://{file.filename}'
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

        file = await self.bot.loop.run_in_executor(None, hande_gif_images, brighten_image, image_bytes, strength)

        embed = utils.create_embed(
            ctx.author,
            title=f'Here\'s your brightened image:',
            image=f'attachment://{file.filename}'
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

        file = await self.bot.loop.run_in_executor(None, hande_gif_images, contrast_image, image_bytes, strength)

        embed = utils.create_embed(
            ctx.author,
            title=f'Here\'s your modified image:',
            image=f'attachment://{file.filename}'
        )

        await ctx.send(embed=embed, file=file)

    @commands.command(aliases=['meme', 'text'])
    async def impact(
            self,
            ctx: utils.CustomContext,
            image: Optional[utils.ImageConverter],
            top_text: str,
            bottom_text: Optional[str]
    ):
        """Adds text with impact font to specified image!

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

        file = await self.bot.loop.run_in_executor(
            None,
            hande_gif_images,
            add_impact,
            image_bytes,
            top_text,
            bottom_text
        )

        embed = utils.create_embed(
            ctx.author,
            title=f'Here\'s your modified image:',
            image=f'attachment://{file.filename}'
        )

        await ctx.send(embed=embed, file=file)

    @commands.command()
    async def rotate(self, ctx: utils.CustomContext, image: Optional[utils.ImageConverter], angle=90):
        """Rotates an image! Positive number for clockwise, negative for counter-clockwise

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

        file = await self.bot.loop.run_in_executor(None, hande_gif_images, rotate_image, image_bytes, angle)

        embed = utils.create_embed(
            ctx.author,
            title=f'Here\'s your modified image:',
            image=f'attachment://{file.filename}'
        )

        await ctx.send(embed=embed, file=file)

    @commands.command(aliases=['rainbow', 'lgbt'])
    async def pride(self, ctx: utils.CustomContext, image: Optional[utils.ImageConverter], transparency=50):
        """Adds the pride rainbow to image!

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

        pride_colors = [(255, 0, 24), (255, 165, 44), (255, 255, 65), (0, 128, 24), (0, 0, 249), (134, 0, 125)]

        await pride_flag(ctx, image, transparency, pride_colors)

    @commands.command(aliases=['homo', 'homosexual'])
    async def gay(self, ctx: utils.CustomContext, image: Optional[utils.ImageConverter], transparency=50):
        """Adds the gay flag to image!

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

        gay_colors = [
            (7, 141, 112),
            (38, 206, 170),
            (153, 232, 194),
            (255, 255, 255),
            (123, 173, 227),
            (80, 73, 203),
            (62, 26, 120)
        ]

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

    async def cog_command_error(self, ctx: utils.CustomContext, error: Exception):
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


async def setup(bot):
    await bot.add_cog(Images(bot))
