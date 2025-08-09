import yt_dlp
import os
import shutil

DOWNLOAD_PATH = "real_bot_main/real_bot/downloads"
COOKIE_FILE = "real_bot_main/real_bot/cookies_instagram.txt"

os.makedirs(DOWNLOAD_PATH, exist_ok=True)

class SilentLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): print(f"[yt_dlp ERROR] {msg}")

def silent_download(url: str):
    ydl_opts = {
        "format": "mp4",
        "outtmpl": os.path.join(DOWNLOAD_PATH, "%(title)s.%(ext)s"),
        "cookiefile": COOKIE_FILE,
        "quiet": True,
        "no_warnings": True,
        "logger": SilentLogger(),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return filename
    except Exception as e:
        print(f"Download failed: {e}")
        return None
    finally:
        try:
            shutil.rmtree(DOWNLOAD_PATH)
            os.makedirs(DOWNLOAD_PATH, exist_ok=True)
        except Exception as cleanup_error:
            print(f"Cleanup failed: {cleanup_error}")

# Example usage:
# result = silent_download("https://www.instagram.com/reel/xyz")
# print("Downloaded:", result)
