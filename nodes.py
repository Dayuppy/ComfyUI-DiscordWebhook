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
import soundfile as sf
import ffmpeg
import torch
import torchvision.io as tvio
import hashlib
import folder_paths # type: ignore
import torchvision.transforms as transforms
from PIL import Image, ImageDraw, ImageOps
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

def process_audio(audio):
    """Process audio input (dict with waveform and sample_rate) and convert it to FLAC format."""

    # Debugging: Print the entire input to see what we are dealing with
    print("DEBUG: Received audio input:", audio)

    # Extract waveform and sample rate from the dictionary
    if isinstance(audio, dict):
        if 'waveform' in audio and 'sample_rate' in audio:
            audio_array = audio['waveform']
            sample_rate = audio['sample_rate']
        else:
            raise ValueError(f"Audio input is missing 'waveform' or 'sample_rate'. Available keys: {audio.keys()}")
    else:
        raise ValueError("Expected audio input to be a dictionary.")

    # Convert to NumPy array if it's a PyTorch tensor
    if hasattr(audio_array, "numpy"):
        audio_array = audio_array.numpy()

    # Ensure the array is 2D: (samples, channels)
    audio_array = np.squeeze(audio_array)  # Remove dimensions of size 1

    if audio_array.ndim == 1:
        # If mono (1D), reshape to (samples, 1)
        audio_array = audio_array[:, np.newaxis]

    # Debugging: Print the shape of the audio array
    print(f"DEBUG: Processed audio shape: {audio_array.shape}")

    # Save the audio input in FLAC format using soundfile
    temp_dir = tempfile.mkdtemp()
    
    # Preserve the original filename and change the extension to .flac
    file_path = os.path.join(temp_dir, "audio.flac")
    
    sf.write(file_path, audio_array, sample_rate, format='FLAC')

    with open(file_path, 'rb') as f:
        data = f.read()

    shutil.rmtree(temp_dir)  # Clean up temporary directory
    return {"data": data, "name": "audio.flac"}

def process_video_to_WEBM(video_frames, fps=15, max_width=1280, max_height=720):
    """Process video tensor frames and convert them to a WebM video file suitable for Discord."""

    # Debugging: Print the shape of the video tensor
    print(f"DEBUG: Video frames shape: {video_frames.shape}")

    # Transpose to (num_frames, height, width, channels) to match write_video's expected input
    video_frames = video_frames.permute(0, 2, 3, 1)  # Move channels to the last dimension

    # Resize video frames to ensure they fit within the desired width/height limits
    resized_video_frames = []
    for frame in video_frames:
        # Debugging: Check the shape of the individual frame
        print(f"DEBUG: Frame shape before conversion to PIL: {frame.shape}")

        # Convert the tensor frame to a NumPy array
        frame_np = frame.numpy()

        # Ensure the frame has 3 channels (RGB)
        if frame_np.shape[-1] > 4:
            raise ValueError(f"Expected the video frame to have 3 or 4 channels, but got {frame_np.shape[-1]} channels.")

        # Convert the NumPy array to a PIL image
        pil_image = Image.fromarray((frame_np * 255).astype(np.uint8))  # Scale the values to 0-255

        aspect_ratio = pil_image.width / pil_image.height

        # Resize the frame if it exceeds the max dimensions
        if pil_image.width > max_width or pil_image.height > max_height:
            if aspect_ratio > 1:
                new_width = max_width
                new_height = int(max_width / aspect_ratio)
            else:
                new_height = max_height
                new_width = int(max_height * aspect_ratio)
            pil_image = pil_image.resize((new_width, new_height))

        # Convert back to tensor and ensure the shape is (height, width, channels)
        resized_frame = transforms.ToTensor()(pil_image).permute(1, 2, 0)  # Ensure it's (height, width, channels)
        resized_frame = resized_frame * 255  # Scale back to 0-255 for video encoding
        resized_video_frames.append(resized_frame)

    # Stack the frames back into a single tensor with the correct shape
    resized_video_tensor = torch.stack(resized_video_frames).byte()  # Ensure the tensor is of byte type (0-255)

    # Create a temporary directory to store the video file
    temp_dir = tempfile.mkdtemp()
    temp_video_file = os.path.join(temp_dir, "temp_video.mp4")  # Save as mp4 initially

    # Save the tensor video frames to a temporary mp4 file (expected shape: num_frames, height, width, channels)
    tvio.write_video(temp_video_file, resized_video_tensor, fps=fps)

    # Now use ffmpeg to convert the saved video to WebM format (VP8 or VP9 codec)
    output_file = os.path.join(temp_dir, "video.webm")

    # Use ffmpeg to convert the mp4 video to WebM with VP8 codec
    ffmpeg.input(temp_video_file).output(output_file, vcodec='libvpx', crf=10, **{'b:v': '1M'}).run(overwrite_output=True)

    # Read the final WebM video file as binary data
    with open(output_file, 'rb') as f:
        video_data = f.read()

    # Clean up temporary files and directory
    shutil.rmtree(temp_dir)

    return {"data": video_data, "name": "video.webm"}


class DiscordLoadVideo:
    @classmethod
    def INPUT_TYPES(cls):
        # Allow users to either specify a directory or use the input directory
        input_dir = folder_paths.get_input_directory()

        # List video files with specific extensions
        files = folder_paths.filter_files_content_types(os.listdir(input_dir), ["video"])

        # Debugging: Print the input directory and list the files
        print("DEBUG: Input Directory:", input_dir)
        print("DEBUG: Files in Input Directory:", files)

        return {
            "required": {
                "file_path": ("STRING", {"default": input_dir}),  # The directory path
                "video": (sorted(files), {"video_upload": True})  # The video file name
            }
        }

    CATEGORY = "Video"
    RETURN_TYPES = ("VIDEO", "AUDIO")
    FUNCTION = "load_video"
    EXPERIMENTAL = True

    def load_video(self, video, file_path):
        # Combine file path and video filename to get the full video path
        video_path = os.path.join(file_path, video)

        # Load video frames and audio using torchvision's read_video
        video_frames, audio_frames, info = tvio.read_video(video_path, pts_unit="sec")

        # Normalize video frames (assumes RGB)
        video_frames = video_frames.float() / 255.0

        # Transpose to match the typical format (batch_size, channels, height, width, num_frames)
        video_frames = video_frames.permute(0, 3, 1, 2)

        # Check if audio is present before normalizing
        if audio_frames is not None and audio_frames.numel() > 0:
            audio_frames = audio_frames.float() / torch.abs(audio_frames).max(dim=0, keepdim=True).values  # Normalize audio
        else:
            print("DEBUG: No audio frames found, skipping audio normalization.")
            audio_frames = None

        return (video_frames, audio_frames)

    @classmethod
    def IS_CHANGED(cls, video):
        video_path = folder_paths.get_annotated_filepath(video)
        m = hashlib.sha256()
        with open(video_path, 'rb') as f:
            m.update(f.read())
        return m.digest().hex()

    @classmethod
    def VALIDATE_INPUTS(cls, video):
        if not folder_paths.exists_annotated_filepath(video):
            return "Invalid video file: {}".format(video)
        return True

class DiscordSetWebhook:
    RETURN_TYPES = ("IMAGE", "*")
    RETURN_NAMES = ("DUMMY IMAGE", "DUMMY OUTPUT")
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

        return (create_default_image(), None)

class DiscordPostViaWebhook:
    RETURN_TYPES = ("IMAGE",)
    OUTPUT_NODE = True
    FUNCTION = "execute"
    CATEGORY = "Discord"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "message": ("STRING", {"default": "", "multiline": True}),
            },
            "optional": {
                "image": ("IMAGE",),
                "audio": ("AUDIO",),
                "video": ("VIDEO",),
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
            image_array = image.cpu().numpy() if hasattr(image, "cpu") else image
            image_array = np.clip(image_array * 255, 0, 255).astype(np.uint8)

            if image_array.ndim == 4:  # Batch of images
                images_to_send = [Image.fromarray(image_array[i]) for i in range(image_array.shape[0])]
            elif image_array.ndim == 3:  # Single image
                images_to_send.append(Image.fromarray(image_array))
            else:
                raise ValueError("Input must be a 3D (single image) or 4D (batch) array.")

        temp_dir = tempfile.mkdtemp()
        files = []

        for idx, img in enumerate(images_to_send):
            file_path = os.path.join(temp_dir, f"image_{idx}.png")
            img.save(file_path, format="PNG", compress_level=1)

            if os.path.getsize(file_path) > 20 * 1024 * 1024:
                img = img.resize((img.width // 2, img.height // 2))
                img.save(file_path, format="PNG", compress_level=9)

            with open(file_path, "rb") as f:
                files.append({"data": f.read(), "name": f"image_{idx}.png"})

        shutil.rmtree(temp_dir)
        return files

    def execute(self, image=None, audio=None, video=None, message="", prepend_message=""):
        with open("discord_webhook_url.txt", "r") as f:
            webhook_url = f.read().strip()

        if not webhook_url:
            raise ValueError("Webhook URL is empty.")

        full_message = f"{prepend_message}\n{message}"

        files = []
        if image is not None:
            files.extend(self.process_image(image))
        if audio is not None:
            files.append(process_audio(audio))  # Handle audio as an array/tensor
        if video is not None:
            files.append(process_video_to_WEBM(video))  # Handle video

        # Ensure files are within size limit
        valid_files = [f for f in files if len(f["data"]) <= 25 * 1024 * 1024]

        # Split files into batches of 4 (Discord limit)
        batches = [valid_files[i:i + 4] for i in range(0, len(valid_files), 4)]

        for batch in batches:
            asyncio.run(self.send_webhook(webhook_url, full_message, batch))

        return (image,)

NODE_CLASS_MAPPINGS = {
    "DiscordSetWebhook": DiscordSetWebhook,
    "DiscordPostViaWebhook": DiscordPostViaWebhook,
    "DiscordLoadVideo": DiscordLoadVideo,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DiscordSetWebhook": "Set Discord Webhook",
    "DiscordPostViaWebhook": "Use Discord Webhook",
    "DiscordLoadVideo": "Load Video",
}