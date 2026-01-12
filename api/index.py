"""
Vercel Python Serverless Function for YouTube Caption Extraction
"""
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

def extract_info_handler(body, headers):
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
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({"title": title, "available_captions": tracks})
    }

def download_caption_handler(body, headers):
    url = body.get('url', '')
    language_code = body.get('language_code')
    format_type = body.get('format', 'srt')
    
    video_id = get_video_id(url)
    title = get_video_title(video_id)
    
    api = YouTubeTranscriptApi()
    transcript_list = api.list(video_id)
    transcript = transcript_list.find_transcript([language_code])
    data = transcript.fetch()
    
    # 포맷 변환
    output = io.StringIO()
    if format_type == "srt":
        for i, item in enumerate(data):
            start = item.start
            end = start + item.duration
            output.write(f"{i+1}\n{format_time(start)} --> {format_time(end)}\n{item.text}\n\n")
        content = output.getvalue()
        headers['Content-Type'] = 'application/x-subrip'
        headers['Content-Disposition'] = f'attachment; filename="subtitle.srt"'
    elif format_type == "vtt":
        output.write("WEBVTT\n\n")
        for item in data:
            start = item.start
            end = start + item.duration
            output.write(f"{format_time(start, True)} --> {format_time(end, True)}\n{item.text}\n\n")
        content = output.getvalue()
        headers['Content-Type'] = 'text/vtt'
        headers['Content-Disposition'] = f'attachment; filename="subtitle.vtt"'
    else: # txt
        for item in data:
            output.write(f"{item.text}\n")
        content = output.getvalue()
        headers['Content-Type'] = 'text/plain'
        headers['Content-Disposition'] = f'attachment; filename="subtitle.txt"'
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': content
    }

def preview_handler(body, headers):
    url = body.get('url', '')
    language_code = body.get('language_code')
    
    video_id = get_video_id(url)
    title = get_video_title(video_id)
    
    api = YouTubeTranscriptApi()
    transcript_list = api.list(video_id)
    transcript = transcript_list.find_transcript([language_code])
    data = transcript.fetch()[:10]
    
    preview_data = [{"time": format_time(item.start), "text": item.text} for item in data]
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({
            "video_title": title,
            "language": transcript.language,
            "preview": preview_data
        })
    }

def handler(event, context):
    """Vercel 서버리스 함수 핸들러"""
    # CORS 헤더
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }
    
    # 요청 경로 파싱
    path = event.get('path', '')
    method = event.get('httpMethod', 'POST')
    body = event.get('body', '{}')
    
    if isinstance(body, str):
        body = json.loads(body)
    
    # OPTIONS 요청 처리 (CORS preflight)
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    try:
        # 경로에 따라 엔드포인트 분기
        if '/extract-info' in path:
            return extract_info_handler(body, headers)
        elif '/download-caption' in path:
            return download_caption_handler(body, headers)
        elif '/preview-caption' in path:
            return preview_handler(body, headers)
        else:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'detail': 'Not found'})
            }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'detail': str(e)})
        }
