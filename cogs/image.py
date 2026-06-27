import io
from inspect import Parameter, Signature
from typing import Callable, Any
from dataclasses import dataclass, field

from discord import app_commands, Interaction, Attachment, File
from discord.app_commands import Range, Group, Command
from discord.ext.commands import GroupCog
from PIL import Image, ImageOps, ImageFilter, ImageEnhance, UnidentifiedImageError, ImageDraw, ImageFont, ImageSequence

import utils
from utils import CustomBot


def image_to_file(image: Image.Image, extension) -> File:
    img_bytes = io.BytesIO()
    image.save(img_bytes, extension, optimize=True)

    img_bytes.seek(0)

    return File(img_bytes, f'image.{extension}')


def hande_gif_images(b: bytes, func: Callable, *args, **kwargs) -> File:
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

    return File(new, 'image.gif')


def invert_image(image: Image.Image):
    r, g, b, a = image.split()
    rgb_image = Image.merge('RGB', (r, g, b))
    inverted_image = ImageOps.invert(rgb_image)
    r2, g2, b2 = inverted_image.split()

    image = Image.merge('RGBA', (r2, g2, b2, a))

    return image


def greyscale_image(image: Image.Image):
    image = image.convert('LA')

    return image


def deepfry_image(image: Image.Image):
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


def noise_image(image: Image.Image, alpha: float):
    noise = Image.effect_noise(image.size, 20).convert('RGBA')

    image = Image.blend(image, noise, alpha/100)

    return image


def blur_image(image: Image.Image, radius: int):
    image = image.filter(ImageFilter.GaussianBlur(radius))

    return image


def brighten_image(image: Image.Image, intensity: float):
    b = ImageEnhance.Brightness(image)
    image = b.enhance(intensity)

    return image


def contrast_image(image: Image.Image, intensity: float):
    c = ImageEnhance.Contrast(image)
    image = c.enhance(intensity)

    return image


def rotate_image(image: Image.Image, angle: int):
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


def make_flag(image: Image.Image, alpha: float, colors: list[int]) -> Image.Image:
    alpha /= 100
    mask = make_mask(colors, *image.size)
    blended_image = Image.blend(image, mask, alpha)

    return blended_image


def add_impact(image: Image.Image, top_text: str, bottom_text: str | None):
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


@dataclass
class ImageCommand:
    name: str
    description: str
    parameters: list[tuple[str, Any, Any]]
    func: Callable
    arguments: tuple[Any] = field(default_factory=tuple)
    descripts: dict[str, str] = field(default_factory=dict)

    def add_param_description(self, callback: Callable):
        self.descripts['image'] = 'The image you want to modify. If not specified, will use the last selected image, or your avatar'
        deco = app_commands.describe(**self.descripts)
        return deco(callback)

    def get_callback(self) -> Callable:
        params = [
            Parameter(
                "interaction",
                Parameter.POSITIONAL_OR_KEYWORD,
                annotation=Interaction,
            ),
            Parameter(
                "image",
                Parameter.POSITIONAL_OR_KEYWORD,
                annotation=Attachment | None,
                default=None
            ),
        ]

        for name, typ, default in self.parameters:
            params.append(
                Parameter(
                    name,
                    Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=typ,
                    default=default,
                )
            )

        async def callback(*args, **kwargs):
            bound = callback.__signature__.bind(*args, **kwargs)  # type: ignore

            interaction: Interaction[CustomBot] = bound.arguments["interaction"]
            image: Attachment | None = bound.arguments["image"]

            if image:
                if not image.content_type or not image.content_type.startswith('image'):
                    raise utils.DoggieBotException('Attachment is not an image!', f'The specifed attachment is an `{image.content_type}`, which is not an image type.')
                image_bytes = await image.read()
            else:
                image_bytes = await interaction.user.display_avatar.read()

            command_args = [
                bound.arguments[name]
                for name, _, _ in self.parameters
            ]

            await interaction.response.defer(thinking=True)

            file = await interaction.client.loop.run_in_executor(
                None,
                lambda: hande_gif_images(
                    image_bytes,
                    self.func,
                    *command_args,
                    *self.arguments
                )
            )

            embed = utils.create_embed(
                interaction.user,
                title="Here's your image:",
                image=f"attachment://{file.filename}",
            )

            await interaction.edit_original_response(
                embed=embed,
                attachments=[file],
            )

        callback.__name__ = str(self.name)
        callback.__signature__ = Signature(params)  # type: ignore
        callback = self.add_param_description(callback)

        return callback

@dataclass
class PrideFlagCommand(ImageCommand):
    func: Callable = field(init=False, default=make_flag)

    def __post_init__(self):
        self.descripts = {'transparency': 'How transparent the flag overlay will be (0-100)'}

# pylint: disable=line-too-long
IMAGE_COMMANDS = [
    ImageCommand('invert', 'Invert an image\'s colors!', [], invert_image),
    ImageCommand('grayscale', 'Grayscale an image!', [], greyscale_image),
    ImageCommand('deepfry', 'Deepfry an image!', [], deepfry_image),
    ImageCommand('blur', 'Blur an image!', [('strength', Range[int, 0, 100], 5)], blur_image, tuple(), {'strength': 'How strong to make the blur (0-100, default 5)'}),
    ImageCommand('noise', 'Add a noise filter to an image!', [('strength', Range[int, 0, 100], 50)], noise_image, tuple(), {'strength': 'How strong to make the noise (0-100, default 50)'}),
    ImageCommand('brighten', 'Brighten an image!', [('brightness', Range[float, 0, 10], 1.25)], brighten_image, tuple(), {'brightness': 'How bright to make the image, values under 1 darken it. (0-10, default 1.25)'}),
    ImageCommand('contrast', 'Add contrast to an image!', [('contrast', Range[float, 0, 10], 1.25)], contrast_image, tuple(), {'contrast': 'How strong to make the contrast, values under 1 lower contrast (0-10, default 1.25)'}),
    ImageCommand('impact', 'Add impact-font text to an image!', [('top_text', str, 'TOP TEXT'), ('bottom_text', str, '')], add_impact, tuple(), {'top_text': 'The text to add at the top', 'bottom_text': 'The text to add at the bottom'}),
    ImageCommand('rotate', 'Rotate an image!', [('angle', float, 90.0)], rotate_image, tuple(), {'angle': 'How many degrees to rotate the image clockwise (default 90.0)'})
]

FLAG_COMMANDS = [
    PrideFlagCommand('pride', 'Overlay the regular pride colors unto an image', [('transparency', Range[int, 0, 100], 50)], ([(255, 0, 24), (255, 165, 44), (255, 255, 65), (0, 128, 24), (0, 0, 249), (134, 0, 125)],)),
    PrideFlagCommand('gay', 'Overlay the toothpaste gay colors unto an image', [('transparency', Range[int, 0, 100], 50)], ([(7, 141, 112), (38, 206, 170), (153, 232, 194), (255, 255, 255), (123, 173, 227), (80, 73, 203), (62, 26, 120)],)),
    PrideFlagCommand('transgender', 'Overlay the transgender colors unto an image', [('transparency', Range[int, 0, 100], 50)], ([(91, 206, 250), (245, 169, 184), (255, 255, 255), (245, 169, 184), (91, 206, 250)],)),
    PrideFlagCommand('bisexual', 'Overlay the bisexual colors unto an image', [('transparency', Range[int, 0, 100], 50)], ([(216, 9, 126), (216, 9, 126), (140, 87, 156), (36, 70, 142), (36, 70, 142)],)),
    PrideFlagCommand('lesbian', 'Overlay the lesbian colors unto an image', [('transparency', Range[int, 0, 100], 50)], ([(213, 45, 0), (239, 118, 39), (255, 154, 86), (255, 255, 255), (209, 98, 164), (181, 86, 144), (163, 2, 98)],)),
    PrideFlagCommand('acesexual', 'Overlay the acesexual colors unto an image', [('transparency', Range[int, 0, 100], 50)], ([(0, 0, 0), (164, 164, 164), (255, 255, 255), (129, 0, 129)],)),
    PrideFlagCommand('pansexual', 'Overlay the pansexual colors unto an image', [('transparency', Range[int, 0, 100], 50)], ([(255, 28, 141), (255, 215, 0), (26, 179, 255)],)),
    PrideFlagCommand('nonbinary', 'Overlay the nonbinary colors unto an image', [('transparency', Range[int, 0, 100], 50)], ([(255, 244, 48), (255, 255, 255), (156, 89, 209), (0, 0, 0)],)),
    PrideFlagCommand('gnc', 'Overlay the gender-nonconforming colors unto an image', [('transparency', Range[int, 0, 100], 50)], ([(80, 40, 76), (150, 71, 122), (93, 150, 247), (255, 255, 255), (93, 150, 247), (150, 71, 122), (80, 40, 76)],)),
    PrideFlagCommand('aromantic', 'Overlay the aromantic colors unto an image', [('transparency', Range[int, 0, 100], 50)], ([(58, 166, 63), (168, 212, 122), (255, 255, 255), (170, 170, 170), (0, 0, 0)],)),
    PrideFlagCommand('genderqueer', 'Overlay the genderqueer colors unto an image', [('transparency', Range[int, 0, 100], 50)], ([(181, 126, 220), (255, 255, 255), (73, 128, 34)],)),
]

class Images(GroupCog, group_name='image'):
    """Commands for image manipulation!"""

    def __init__(self, bot):
        self.bot: CustomBot = bot

    async def cog_load(self):
        if self.app_command:
            for image_command in IMAGE_COMMANDS:
                self.app_command.add_command(
                    Command(
                        name=image_command.name.lower(),
                        description=image_command.description,
                        callback=image_command.get_callback()
                    )
                )

        pride_group = Group(name='pride', description='Image commands for pride', parent=self.app_command)

        for image_command in FLAG_COMMANDS:
            pride_group.add_command(
                Command(
                    name=image_command.name.lower(),
                    description=image_command.description,
                    callback=image_command.get_callback()
                )
            )

    async def cog_app_command_error(self, interaction: Interaction, error: Exception):
        if isinstance(error, UnidentifiedImageError):
            raise utils.DoggieBotException('Error while making image!', 'The bot wasn\'t able to identify the image\'s format\n **Note:** Links from sites like Tenor and GIPHY don\'t work, use the direct image url') from error

        raise error

async def setup(bot):
    await bot.add_cog(Images(bot))
