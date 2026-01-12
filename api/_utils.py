import re
import html
import requests

def get_video_id(url: str) -> str:
    match = re.search(r'(?:v=|\/|be\/|embed\/)([a-zA-Z0-9_-]{11})', str(url))
    if not match:
        raise ValueError("유효한 YouTube URL이 아닙니다.")
    return match.group(1)

def get_video_title(video_id: str) -> str:
    try:
        res = requests.get(f"https://www.youtube.com/watch?v={video_id}", timeout=10)
        match = re.search(r'<title>(.*?) - YouTube</title>', res.text)
        if match:
            return html.unescape(match.group(1))
    except:
        pass
    return f"YouTube_Video_{video_id}"

def format_time(seconds: float, is_vtt: bool = False) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds % 1) * 1000))
    if ms == 1000:
        s += 1
        ms = 0
    sep = "." if is_vtt else ","
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"

def add_cors_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    return response
