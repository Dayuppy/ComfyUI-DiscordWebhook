import os
import json
import tempfile
import platform
import shutil
import numpy as np
from discord_webhook import DiscordWebhook
from PIL import Image

class DiscordPostViaWebhook:
    RETURN_TYPES = ("IMAGE",)  # Return the image as pass-through
    RETURN_NAMES = ("IMAGE_PASSTHROUGH",)  # Output name
    OUTPUT_TOOLTIPS = ("Image Output Pass-through",)
    OUTPUT_NODE = True
    FUNCTION = "execute"
    CATEGORY = "Dayuppy Test Nodes"
    DESCRIPTION = "Post image and message to Discord using webhook"
    DEPRECATED = False
    EXPERIMENTAL = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
            },
            "optional": {
                "send_metadata": ("BOOLEAN", {"default": True, "tooltip": "Toggle to include metadata/additional info in the message."}),
                "send_message": ("BOOLEAN", {"default": True, "tooltip": "Toggle to include user message in the post."}),
                "send_image": ("BOOLEAN", {"default": True, "tooltip": "Toggle to include image in the post."}),
                "message": ("STRING", {"default": "", "multiline": True, "tooltip": "Message to accompany the image."}),
                "prepend_message": ("STRING", {"default": "", "multiline": True, "tooltip": "Optional string to prepend to the message."}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            }
        }

    def execute(self, image, send_metadata=True, send_message=True, send_image=True, message="", prepend_message="", prompt=None, extra_pnginfo=None):
        # Retrieve the Discord webhook URL from the environment variable
        webhook_url = os.getenv("DISCORD_HOOK")
        if not webhook_url:
            # Determine the OS and provide specific instructions
            os_type = platform.system()
            instructions = "Please set the 'DISCORD_HOOK' environment variable."

            if os_type == "Linux":
                instructions += " On Linux, you can set it by adding the following line to your terminal or shell startup file (e.g., .bashrc or .zshrc):\n"
                instructions += 'export DISCORD_HOOK="your_webhook_url"'
            elif os_type == "Windows":
                instructions += " On Windows, you can set it by running the following in Command Prompt or PowerShell:\n"
                instructions += '$env:DISCORD_HOOK="your_webhook_url"'
            elif os_type == "Darwin":  # MacOS
                instructions += " On Mac, you can set it by adding the following line to your terminal or shell startup file (e.g., .bash_profile or .zshrc):\n"
                instructions += 'export DISCORD_HOOK="your_webhook_url"'
            else:
                instructions += " For other systems, please consult your operating system's documentation on how to set environment variables."

            raise AssertionError(f"Environment variable 'DISCORD_HOOK' is not set. {instructions}")

        temp_dir = tempfile.mkdtemp()
        full_message = ""

        if send_metadata:
            # Check for metadata in the image and append to the message if found
            metadata = {}
            if prompt is not None:
                metadata["prompt"] = json.dumps(prompt)
            
            if extra_pnginfo is not None:
                for key, value in extra_pnginfo.items():
                    metadata[key] = json.dumps(value)

            # Extract and format the required metadata
            metadata_message = ""
            if metadata:
                prompt_info = metadata.get("prompt", "{}")
                try:
                    prompt_data = json.loads(prompt_info)
                    for key, value in prompt_data.items():
                        if "inputs" in value:
                            inputs = value["inputs"]
                            if "seed" in inputs:
                                metadata_message += f"Seed: {inputs['seed']}\n"
                            if "steps" in inputs:
                                metadata_message += f"Steps: {inputs['steps']}\n"
                            if "cfg" in inputs:
                                metadata_message += f"Config Scale: {inputs['cfg']}\n"
                            if "sampler_name" in inputs:
                                metadata_message += f"Sampler Name: {inputs['sampler_name']}\n"
                            if "scheduler" in inputs:
                                metadata_message += f"Scheduler: {inputs['scheduler']}\n"
                            if "width" in inputs:
                                metadata_message += f"Width: {inputs['width']}\n"
                            if "height" in inputs:
                                metadata_message += f"Height: {inputs['height']}\n"
                except json.JSONDecodeError:
                    metadata_message += "Error reading image metadata.\n"
                full_message += metadata_message

        if send_message:
            # Append the user message
            full_message += f"{prepend_message}\nUser message: {message}"

        if send_image:
            file_path = os.path.join(temp_dir, "image.png")

            # Convert the image tensor to a numpy array and then to a PIL Image
            array = 255.0 * image.cpu().numpy()

            # Squeeze the unnecessary dimensions (batch and channel)
            array = np.squeeze(array)

            # Ensure array has a proper shape for an image (e.g., (512, 512, 3) for RGB)
            if len(array.shape) == 3 and array.shape[0] == 1:
                array = np.squeeze(array, axis=0)

            # Now convert to a PIL image
            img = Image.fromarray(np.clip(array, 0, 255).astype(np.uint8))

            # Resize or compress the image to ensure it's under 20MB
            img.save(file_path, format="PNG", compress_level=9)
            if os.path.getsize(file_path) > 20 * 1024 * 1024:
                img = img.resize((img.width // 2, img.height // 2))
                img.save(file_path, format="PNG", compress_level=9)

            # Send the image and message to Discord
            wh = DiscordWebhook(url=webhook_url, content=full_message[:2000])  # Truncate message to fit within Discord limits
            with open(file_path, "rb") as f:
                wh.add_file(file=f.read(), filename="image.png")
            wh.execute()

            shutil.rmtree(temp_dir)

        # Return the image as a pass-through
        return (image,)


# Map class to node
NODE_CLASS_MAPPINGS = {
    "DiscordPostViaWebhook": DiscordPostViaWebhook
}

# Display name mapping for node
NODE_DISPLAY_NAME_MAPPINGS = {
    "DiscordPostViaWebhook": "Discord Webhook",
}