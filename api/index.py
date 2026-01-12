"""
YouTube 자막 추출기 백엔드 API - 검증된 라이브러리 버전
"""
import re
import io
import html
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from youtube_transcript_api import YouTubeTranscriptApi
import requests
import json

app = FastAPI(title="YouTube 자막 추출기", version="1.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ExtractRequest(BaseModel):
    url: HttpUrl
    language_code: Optional[str] = None
    format: str = "srt"

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
        raise HTTPException(status_code=400, detail="유효한 YouTube URL이 아닙니다.")
    return match.group(1)

def get_video_title(video_id: str) -> str:
    """비디오 제목을 가져오기 위한 최소한의 요청"""
    try:
        res = requests.get(f"https://www.youtube.com/watch?v={video_id}", timeout=10)
        match = re.search(r'<title>(.*?) - YouTube</title>', res.text)
        if match:
            return html.unescape(match.group(1))
    except:
        pass
    return f"YouTube_Video_{video_id}"

@app.post("/extract-info")
async def extract_info(request: ExtractRequest):
    video_id = get_video_id(request.url)
    title = get_video_title(video_id)
    
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        
        tracks = []
        # 수동 생성 및 자동 생성 자막 목록 추출
        for t in transcript_list:
            tracks.append({
                'languageCode': t.language_code,
                'name': t.language,
                'kind': 'asr' if t.is_generated else ''
            })
            
        return {"title": title, "available_captions": tracks}
    except Exception as e:
        print(f"Error in extract-info: {e}")
        raise HTTPException(status_code=404, detail="자막을 찾을 수 없거나 추출이 제한된 영상입니다.")

@app.post("/download-caption")
async def download_caption(request: ExtractRequest):
    video_id = get_video_id(request.url)
    title = get_video_title(video_id)
    
    if not request.language_code:
        raise HTTPException(status_code=400, detail="언어 코드를 지정해야 합니다.")

    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        
        # 요청된 언어 찾기 (자동생성 여부 상관없이 매칭되는 첫 번째 언어)
        try:
            transcript = transcript_list.find_transcript([request.language_code])
        except:
            # 해당 언어가 없으면 수동/자동 구분 없이 시도
            transcript = next((t for t in transcript_list if t.language_code == request.language_code), None)
            if not transcript:
                raise Exception("해당 언어의 자막을 찾을 수 없습니다.")

        data = transcript.fetch()
        
        # 포맷 변환
        output = io.StringIO()
        if request.format == "srt":
            for i, item in enumerate(data):
                start = item.start
                end = start + item.duration
                output.write(f"{i+1}\n{format_time(start)} --> {format_time(end)}\n{item.text}\n\n")
            ext, mime = "srt", "application/x-subrip"
        elif request.format == "vtt":
            output.write("WEBVTT\n\n")
            for item in data:
                start = item.start
                end = start + item.duration
                output.write(f"{format_time(start, True)} --> {format_time(end, True)}\n{item.text}\n\n")
            ext, mime = "vtt", "text/vtt"
        else: # txt
            for item in data:
                output.write(f"{item.text}\n")
            ext, mime = "txt", "text/plain"

        output.seek(0)
        safe_title = re.sub(r'[^\w\s.-]', '', title).replace(' ', '_')
        filename = f"{safe_title}_{request.language_code}.{ext}"

        return StreamingResponse(
            output,
            media_type=mime,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        print(f"Error in download-caption: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/preview-caption")
async def preview(request: ExtractRequest):
    video_id = get_video_id(request.url)
    title = get_video_title(video_id)
    
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        transcript = transcript_list.find_transcript([request.language_code])
        data = transcript.fetch()[:10] # 상위 10개
        
        return {
            "video_title": title,
            "language": transcript.language,
            "preview": [{"time": format_time(item.start), "text": item.text} for item in data]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
