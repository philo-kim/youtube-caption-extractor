from http.server import BaseHTTPRequestHandler
import json
import re
import html
from youtube_transcript_api import YouTubeTranscriptApi
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

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data.decode('utf-8'))
            
            url = body.get('url', '')
            video_id = get_video_id(url)
            title = get_video_title(video_id)
            
            api = YouTubeTranscriptApi()
            transcript_list = api.list(video_id)
            
            tracks = []
            for t in transcript_list:
                tracks.append({
                    'languageCode': t.language_code,
                    'name': t.language,
                    'kind': 'asr' if t.is_generated else ''
                })
            
            response = {"title": title, "available_captions": tracks}
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"detail": str(e)}).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
