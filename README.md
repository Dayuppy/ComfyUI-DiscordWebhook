# ComfyUI-DiscordWebhook
A very simple Discord webhook integration node for ComfyUI that lets you post images and text with optional metadata.

![image](https://github.com/user-attachments/assets/c2459fc5-ff7e-454a-b691-4baf7999d1ea)
![image](https://github.com/user-attachments/assets/29b24147-4f42-486e-a052-ee022f6b13d2)

# Installation:
Clone or download this repo into your ComfyUI/custom_nodes folder.

![image](https://github.com/user-attachments/assets/71450181-a788-4fc7-ad5f-236c994100c1)
![image](https://github.com/user-attachments/assets/eb5a0bc5-1c7f-4aec-9bb6-e7a11de946b8)

Modify your .bat or .sh to include an environment variable containing your your Discord Webhook: https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks

# For Windows:

set DISCORD_HOOK="your_webhook_here"

Ex. custom_launcher.bat
```
set DISCORD_HOOK="https://discord.com/api/webhooks/012345678910987654321/abcdefghijklmnopqrstuvwxyz"
.\python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build
pause
```

# For Linux:

export 'DISCORD_HOOK=your_webhook_here'

Ex. custom_launcher.sh
```
export 'DISCORD_HOOK=https://discord.com/api/webhooks/012345678910987654321/abcdefghijklmnopqrstuvwxyz'
./bin/python3 -s ./main.py
pause
```
