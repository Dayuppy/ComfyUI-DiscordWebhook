"""
Copyright (C) 2024  Dayuppy

    This library is free software; you can redistribute it and/or
    modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation; either
    version 2.1 of the License, or (at your option) any later version.

    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this library; if not, write to the Free Software
    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
    USA

@author: Dayuppy
@title: Discord Webhook
@nickname: DiscordWebhook
@description: A very simple Discord webhook integration node for ComfyUI that lets you post images and text.
"""

import os
import tempfile
import shutil
import numpy as np
import asyncio
from PIL import Image, ImageDraw
from discord_webhook import AsyncDiscordWebhook

def create_default_image():
    """Create a simple TV test pattern image."""
    colors = ["white", "yellow", "cyan", "green", "magenta", "red", "blue", "black"]
    bar_width = 128 // len(colors)
    image = Image.new("RGB", (128, 128), "black")
    draw = ImageDraw.Draw(image)

    for i, color in enumerate(colors):
        draw.rectangle([i * bar_width, 0, (i + 1) * bar_width, 128], fill=color)

    return image

class DiscordSetWebhook:
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("DUMMY IMAGE",)
    OUTPUT_NODE = True
    FUNCTION = "execute"
    CATEGORY = "Discord"

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"URL": ("STRING",)}}
    
    def execute(self, URL):
        if not URL.startswith("https://discord.com/api/webhooks/"):
            raise ValueError("Invalid URL format. URL should start with 'https://discord.com/api/webhooks/'. Please reference https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks")

        with open("discord_webhook_url.txt", "w") as f:
            f.write(URL)

        return (create_default_image(),)

class DiscordPostViaWebhook:
    RETURN_TYPES = ("IMAGE",)
    OUTPUT_NODE = True
    FUNCTION = "execute"
    CATEGORY = "Discord"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",)
                },
            "optional": {
                "send_Message": ("BOOLEAN", {"default": True}),
                "send_Image": ("BOOLEAN", {"default": True}),
                "message": ("STRING", {"default": "", "multiline": True}),
                "prepend_message": ("STRING", {"default": "", "multiline": True}),
            },
        }

    async def send_webhook(self, url, message, files=None):
        webhook = AsyncDiscordWebhook(url=url, content=message[:2000], timeout=30.0)
        if files:
            for file in files:
                webhook.add_file(file=file["data"], filename=file["name"])
        await webhook.execute()

    def process_image(self, image):
        """Process the image (or batch of images) and return them in a format suitable for Discord."""
        images_to_send = []

        if image is None:
            images_to_send.append(create_default_image())
        else:
            # Handle both single and batched images
            image_array = image.cpu().numpy() if hasattr(image, "cpu") else image
            image_array = np.clip(image_array * 255, 0, 255).astype(np.uint8)

            if image_array.ndim == 4:  # Batch of images
                images_to_send = [Image.fromarray(image_array[i]) for i in range(image_array.shape[0])]
            elif image_array.ndim == 3:  # Single image
                images_to_send.append(Image.fromarray(image_array))
            else:
                raise ValueError("Input must be a 3D (single image) or 4D (batch) array.")

        # Save images and return the file data
        temp_dir = tempfile.mkdtemp()
        files = []

        for idx, img in enumerate(images_to_send):
            file_path = os.path.join(temp_dir, f"image_{idx}.png")
            img.save(file_path, format="PNG", compress_level=1)

            # If the file size exceeds 20MB, resize and save again
            if os.path.getsize(file_path) > 20 * 1024 * 1024:
                img = img.resize((img.width // 2, img.height // 2))
                img.save(file_path, format="PNG", compress_level=9)

            with open(file_path, "rb") as f:
                files.append({"data": f.read(), "name": f"image_{idx}.png"})

        shutil.rmtree(temp_dir)
        return files

    def execute(self, image, send_Message=True, send_Image=True, message="", prepend_message=""):
        with open("discord_webhook_url.txt", "r") as f:
            webhook_url = f.read().strip()

        if not webhook_url:
            raise ValueError("Webhook URL is empty.")

        full_message = f"{prepend_message}\n{message}" if send_Message else ""
        files = self.process_image(image) if send_Image else None

        if files:
            # Split files into batches of 4 (Discord limit)
            batches = [files[i:i + 4] for i in range(0, len(files), 4)]

            # Send multiple webhooks if necessary
            for batch in batches:
                asyncio.run(self.send_webhook(webhook_url, full_message, batch))
        else:
            asyncio.run(self.send_webhook(webhook_url, full_message))

        return (image,)

NODE_CLASS_MAPPINGS = {
    "DiscordSetWebhook": DiscordSetWebhook,
    "DiscordPostViaWebhook": DiscordPostViaWebhook
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DiscordSetWebhook": "Set Discord Webhook",
    "DiscordPostViaWebhook": "Use Discord Webhook"
}