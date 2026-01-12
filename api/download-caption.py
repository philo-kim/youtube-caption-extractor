from http.server import BaseHTTPRequestHandler
import json
import re
import io
import html
from youtube_transcript_api import YouTubeTranscriptApi
import requests

def format_time(seconds: float, is_vtt: bool = False) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds % 1) * 1000))
    if ms == 1000: s += 1; ms = 0
    sep = "." if is_vtt else ","
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"

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
            language_code = body.get('language_code')
            format_type = body.get('format', 'srt')
            
            video_id = get_video_id(url)
            title = get_video_title(video_id)
            
            api = YouTubeTranscriptApi()
            transcript_list = api.list(video_id)
            transcript = transcript_list.find_transcript([language_code])
            data = transcript.fetch()
            
            output = io.StringIO()
            if format_type == "srt":
                for i, item in enumerate(data):
                    start = item.start
                    end = start + item.duration
                    output.write(f"{i+1}\n{format_time(start)} --> {format_time(end)}\n{item.text}\n\n")
                content = output.getvalue()
                content_type = 'application/x-subrip'
                filename = "subtitle.srt"
            elif format_type == "vtt":
                output.write("WEBVTT\n\n")
                for item in data:
                    start = item.start
                    end = start + item.duration
                    output.write(f"{format_time(start, True)} --> {format_time(end, True)}\n{item.text}\n\n")
                content = output.getvalue()
                content_type = 'text/vtt'
                filename = "subtitle.vtt"
            else:
                for item in data:
                    output.write(f"{item.text}\n")
                content = output.getvalue()
                content_type = 'text/plain'
                filename = "subtitle.txt"
            
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
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
