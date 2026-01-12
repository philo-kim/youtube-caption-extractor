from flask import Flask, request, jsonify, Response
from youtube_transcript_api import YouTubeTranscriptApi
import re
import html
import requests
import io

app = Flask(__name__)

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

@app.route('/api/extract-info', methods=['POST', 'OPTIONS'])
def extract_info():
    if request.method == 'OPTIONS':
        return add_cors_headers(jsonify({}))

    try:
        body = request.get_json()
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

        return add_cors_headers(jsonify({"title": title, "available_captions": tracks}))
    except Exception as e:
        response = jsonify({"detail": str(e)})
        response.status_code = 500
        return add_cors_headers(response)

@app.route('/api/download-caption', methods=['POST', 'OPTIONS'])
def download_caption():
    if request.method == 'OPTIONS':
        return add_cors_headers(jsonify({}))

    try:
        body = request.get_json()
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

        response = Response(content, mimetype=content_type)
        response.headers.add('Content-Disposition', f'attachment; filename="{filename}"')
        return add_cors_headers(response)
    except Exception as e:
        response = jsonify({"detail": str(e)})
        response.status_code = 500
        return add_cors_headers(response)

@app.route('/api/preview-caption', methods=['POST', 'OPTIONS'])
def preview_caption():
    if request.method == 'OPTIONS':
        return add_cors_headers(jsonify({}))

    try:
        body = request.get_json()
        url = body.get('url', '')
        language_code = body.get('language_code')

        video_id = get_video_id(url)
        title = get_video_title(video_id)

        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        transcript = transcript_list.find_transcript([language_code])
        data = transcript.fetch()[:10]

        preview_data = [{"time": format_time(item.start), "text": item.text} for item in data]

        return add_cors_headers(jsonify({
            "video_title": title,
            "language": transcript.language,
            "preview": preview_data
        }))
    except Exception as e:
        response = jsonify({"detail": str(e)})
        response.status_code = 500
        return add_cors_headers(response)
