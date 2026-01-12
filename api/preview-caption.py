from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from _utils import get_video_id, get_video_title, format_time, add_cors_headers

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

        video_id = get_video_id(url)
        title = get_video_title(video_id)

        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        transcript = transcript_list.find_transcript([language_code])
        data = transcript.fetch()[:10]

        preview_data = [{"time": format_time(item.start), "text": item.text} for item in data]

        response = jsonify({
            "video_title": title,
            "language": transcript.language,
            "preview": preview_data
        })
        return add_cors_headers(response)
    except Exception as e:
        response = jsonify({"detail": str(e)})
        response.status_code = 500
        return add_cors_headers(response)
