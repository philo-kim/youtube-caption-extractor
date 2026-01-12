from flask import Flask, request, jsonify, Response
from youtube_transcript_api import YouTubeTranscriptApi
from _utils import get_video_id, get_video_title, format_time, add_cors_headers
import io

app = Flask(__name__)

@app.route('/', methods=['POST', 'OPTIONS'])
@app.route('/<path:path>', methods=['POST', 'OPTIONS'])
def handler(path=''):
    if request.method == 'OPTIONS':
        response = jsonify({})
        return add_cors_headers(response)

    try:
        body = request.get_json()
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

        response = Response(content, mimetype=content_type)
        response.headers.add('Content-Disposition', f'attachment; filename="{filename}"')
        return add_cors_headers(response)
    except Exception as e:
        response = jsonify({"detail": str(e)})
        response.status_code = 500
        return add_cors_headers(response)
