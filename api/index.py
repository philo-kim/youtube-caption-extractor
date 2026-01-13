from http.server import BaseHTTPRequestHandler
from youtube_transcript_api import YouTubeTranscriptApi
from y2mate_api import Handler as Y2MateHandler
import json
import re
import html
import requests
import io
from urllib.parse import parse_qs, urlparse

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

def get_video_thumbnail(video_id: str) -> str:
    return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

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

class handler(BaseHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_GET(self):
        self.send_json_response({
            "status": "ok",
            "message": "YouTube Caption & Video Downloader API",
            "endpoints": [
                "POST /api/extract-info",
                "POST /api/download-caption",
                "POST /api/preview-caption",
                "POST /api/get-video-streams"
            ]
        })

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path

        content_length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(content_length)) if content_length > 0 else {}

        try:
            if path == '/api/extract-info':
                self.handle_extract_info(body)
            elif path == '/api/download-caption':
                self.handle_download_caption(body)
            elif path == '/api/preview-caption':
                self.handle_preview_caption(body)
            elif path == '/api/get-video-streams':
                self.handle_get_video_streams(body)
            else:
                self.send_error_response(404, f"Not found: {path}")
        except Exception as e:
            self.send_error_response(500, str(e))

    def send_json_response(self, data, status=200):
        response = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(response)

    def send_error_response(self, status, message):
        self.send_json_response({"detail": message}, status)

    def handle_extract_info(self, body):
        url = body.get('url', '')
        video_id = get_video_id(url)
        title = get_video_title(video_id)
        thumbnail = get_video_thumbnail(video_id)

        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)

        tracks = []
        for t in transcript_list:
            tracks.append({
                'languageCode': t.language_code,
                'name': t.language,
                'kind': 'asr' if t.is_generated else ''
            })

        self.send_json_response({
            "title": title,
            "thumbnail": thumbnail,
            "video_id": video_id,
            "available_captions": tracks
        })

    def handle_download_caption(self, body):
        url = body.get('url', '')
        language_code = body.get('language_code')
        format_type = body.get('format', 'srt')

        video_id = get_video_id(url)

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

        response_bytes = content.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(response_bytes)

    def handle_preview_caption(self, body):
        url = body.get('url', '')
        language_code = body.get('language_code')

        video_id = get_video_id(url)
        title = get_video_title(video_id)

        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        transcript = transcript_list.find_transcript([language_code])
        data = transcript.fetch()[:10]

        preview_data = [{"time": format_time(item.start), "text": item.text} for item in data]

        self.send_json_response({
            "video_title": title,
            "language": transcript.language,
            "preview": preview_data
        })

    def handle_get_video_streams(self, body):
        url = body.get('url', '')
        video_id = get_video_id(url)

        try:
            # y2mate-api로 다운로드 URL 가져오기
            handler = Y2MateHandler(url)
            streams = []

            # MP4 스트림 가져오기
            for video in handler.run(format="mp4"):
                streams.append({
                    'type': 'video',
                    'quality': video.quality,
                    'url': video.url,
                    'size': getattr(video, 'size', None)
                })

            # MP3 스트림 가져오기
            for audio in handler.run(format="mp3"):
                streams.append({
                    'type': 'audio',
                    'quality': audio.quality,
                    'url': audio.url,
                    'size': getattr(audio, 'size', None)
                })

            if streams:
                self.send_json_response({
                    "title": get_video_title(video_id),
                    "thumbnail": get_video_thumbnail(video_id),
                    "streams": streams
                })
            else:
                self.send_error_response(404, "다운로드 가능한 스트림을 찾을 수 없습니다.")

        except Exception as e:
            self.send_error_response(500, f"동영상 정보 추출 실패: {str(e)}")
