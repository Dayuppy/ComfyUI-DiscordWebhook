"""
@author: Dayuppy
@title: Discord Webhook
@nickname: DiscordWebhook
@description: A very simple Discord webhook integration node for ComfyUI that lets you post images and text with optional metadata.
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
    image = Image.new("RGB", (128, 128), "black")
    colors = ["white", "yellow", "cyan", "green", "magenta", "red", "blue", "black"]
    bar_width = 128 // len(colors)
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
            raise ValueError("Invalid URL format. URL should start with 'https://discord.com/api/webhooks/' Please reference https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks")
        
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
        """Process the image and return it in a format suitable for Discord."""       
        if image is None:
            image = create_default_image()
            
        if isinstance(image, np.ndarray):
            image = Image.fromarray(np.clip(image.squeeze() * 255, 0, 255).astype(np.uint8))
        elif hasattr(image, "cpu"):
            array = image.cpu().numpy()

            # Convert array to PIL image
            if 'array' in locals():
                if len(array.shape) == 4 and array.shape[-1] == 3:
                    array = np.squeeze(array, axis=0)

            array = np.clip(array * 255, 0, 255).astype(np.uint8)
            image = Image.fromarray(array)
    
        # Save the image to a temporary file
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "image.png")
        image.save(file_path, format="PNG", compress_level=1)

         # If the file size exceeds 20MB, resize and save again
        if os.path.getsize(file_path) > 20 * 1024 * 1024:
            image = image.resize((image.width // 2, image.height // 2))
            image.save(file_path, format="PNG", compress_level=9)

        with open(file_path, "rb") as f:
            files = [{"data": f.read(), "name": "image.png"}]

        # Clean up the temporary directory
        shutil.rmtree(temp_dir)
        
        return files
    
    def execute(self, image, send_Message=True, send_Image=True, message="", prepend_message=""):
        with open("discord_webhook_url.txt", "r") as f:
            webhook_url = f.read().strip()
        
        if not webhook_url:
            raise ValueError("Webhook URL is empty.")
        
        if send_Message:
            message = f"{prepend_message}\n{message}"
        
        files = self.process_image(image) if send_Image else None
        asyncio.run(self.send_webhook(webhook_url, message, files))

        return (image,)

NODE_CLASS_MAPPINGS = {
    "DiscordSetWebhook": DiscordSetWebhook,
    "DiscordPostViaWebhook": DiscordPostViaWebhook
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DiscordSetWebhook": "Set Discord Webhook",
    "DiscordPostViaWebhook": "Use Discord Webhook"
}