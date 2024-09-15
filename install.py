import os
import subprocess
import sys

def install_ffmpeg():
    try:
        # Check if ffmpeg is already installed
        subprocess.run(['ffmpeg', '-version'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("FFmpeg is already installed.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("FFmpeg is not installed. Installing FFmpeg...")

        try:
            # Check if the user has root access
            if os.geteuid() != 0:
                # Request sudo permission to install FFmpeg
                print("Requesting sudo privileges to install FFmpeg...")
                subprocess.run(['sudo', 'apt', 'update'], check=True)
                subprocess.run(['sudo', 'apt', 'install', '-y', 'ffmpeg'], check=True)
                print("FFmpeg has been installed successfully.")
            else:
                # If the script is already running as root, no need for sudo
                subprocess.run(['apt', 'update'], check=True)
                subprocess.run(['apt', 'install', '-y', 'ffmpeg'], check=True)
                print("FFmpeg has been installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error during FFmpeg installation: {e}")
            sys.exit(1)
        except FileNotFoundError as e:
            print("Error: `sudo` command not found or user does not have sudo privileges.")
            sys.exit(1)

if __name__ == "__main__":
    install_ffmpeg()