from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from _utils import get_video_id, get_video_title, add_cors_headers

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

        response = jsonify({"title": title, "available_captions": tracks})
        return add_cors_headers(response)
    except Exception as e:
        response = jsonify({"detail": str(e)})
        response.status_code = 500
        return add_cors_headers(response)
