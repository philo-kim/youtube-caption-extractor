let innertube = null;

async function getInnertube() {
  if (!innertube) {
    const { Innertube } = await import('youtubei.js');
    innertube = await Innertube.create();
  }
  return innertube;
}

function getVideoId(url) {
  const match = url.match(/(?:v=|\/|be\/|embed\/)([a-zA-Z0-9_-]{11})/);
  if (!match) throw new Error('유효한 YouTube URL이 아닙니다.');
  return match[1];
}

function formatTime(seconds, isVtt = false) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 1000);
  const sep = isVtt ? '.' : ',';
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}${sep}${ms.toString().padStart(3, '0')}`;
}

module.exports = async function handler(req, res) {
  // CORS preflight
  if (req.method === 'OPTIONS') {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    return res.status(200).end();
  }

  // Set CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  const path = req.url.split('?')[0];

  if (req.method === 'GET') {
    return res.json({
      status: 'ok',
      message: 'YouTube Caption & Video Downloader API',
      endpoints: [
        'POST /api/extract-info',
        'POST /api/download-caption',
        'POST /api/preview-caption',
        'POST /api/get-video-streams'
      ]
    });
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ detail: 'Method not allowed' });
  }

  const body = req.body || {};

  try {
    if (path === '/api/extract-info') {
      return await handleExtractInfo(body, res);
    } else if (path === '/api/download-caption') {
      return await handleDownloadCaption(body, res);
    } else if (path === '/api/preview-caption') {
      return await handlePreviewCaption(body, res);
    } else if (path === '/api/get-video-streams') {
      return await handleGetVideoStreams(body, res);
    } else {
      return res.status(404).json({ detail: `Not found: ${path}` });
    }
  } catch (error) {
    console.error('API Error:', error);
    return res.status(500).json({ detail: error.message });
  }
};

async function handleExtractInfo(body, res) {
  const { url } = body;
  if (!url) return res.status(400).json({ detail: 'URL is required' });

  const videoId = getVideoId(url);
  const yt = await getInnertube();
  const info = await yt.getInfo(videoId);

  const title = info.basic_info?.title || 'Unknown';
  const thumbnail = info.basic_info?.thumbnail?.[0]?.url || `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`;

  const captions = info.captions?.caption_tracks || [];
  const tracks = captions.map(track => ({
    languageCode: track.language_code,
    name: track.name?.text || track.language_code,
    kind: track.kind === 'asr' ? 'asr' : ''
  }));

  return res.json({
    title,
    thumbnail,
    video_id: videoId,
    available_captions: tracks
  });
}

async function handleDownloadCaption(body, res) {
  const { url, language_code, format = 'srt' } = body;
  if (!url) return res.status(400).json({ detail: 'URL is required' });
  if (!language_code) return res.status(400).json({ detail: 'language_code is required' });

  const videoId = getVideoId(url);
  const yt = await getInnertube();
  const info = await yt.getInfo(videoId);

  const captions = info.captions?.caption_tracks || [];
  const track = captions.find(t => t.language_code === language_code);
  if (!track) return res.status(404).json({ detail: 'Caption not found' });

  const transcript = await yt.getTranscript(videoId, { language_code });
  const segments = transcript?.transcript?.content?.body?.initial_segments || [];

  let content = '';
  let contentType = 'text/plain';
  let filename = 'subtitle.txt';

  if (format === 'srt') {
    segments.forEach((segment, i) => {
      const start = parseFloat(segment.start_ms) / 1000;
      const end = parseFloat(segment.end_ms) / 1000;
      const text = segment.snippet?.text || '';
      content += `${i + 1}\n${formatTime(start)} --> ${formatTime(end)}\n${text}\n\n`;
    });
    contentType = 'application/x-subrip';
    filename = 'subtitle.srt';
  } else if (format === 'vtt') {
    content = 'WEBVTT\n\n';
    segments.forEach(segment => {
      const start = parseFloat(segment.start_ms) / 1000;
      const end = parseFloat(segment.end_ms) / 1000;
      const text = segment.snippet?.text || '';
      content += `${formatTime(start, true)} --> ${formatTime(end, true)}\n${text}\n\n`;
    });
    contentType = 'text/vtt';
    filename = 'subtitle.vtt';
  } else {
    segments.forEach(segment => {
      content += (segment.snippet?.text || '') + '\n';
    });
  }

  res.setHeader('Content-Type', contentType);
  res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
  return res.send(content);
}

async function handlePreviewCaption(body, res) {
  const { url, language_code } = body;
  if (!url) return res.status(400).json({ detail: 'URL is required' });
  if (!language_code) return res.status(400).json({ detail: 'language_code is required' });

  const videoId = getVideoId(url);
  const yt = await getInnertube();
  const info = await yt.getInfo(videoId);

  const captions = info.captions?.caption_tracks || [];
  const track = captions.find(t => t.language_code === language_code);
  if (!track) return res.status(404).json({ detail: 'Caption not found' });

  const transcript = await yt.getTranscript(videoId, { language_code });
  const segments = transcript?.transcript?.content?.body?.initial_segments || [];

  const preview = segments.slice(0, 10).map(segment => ({
    time: formatTime(parseFloat(segment.start_ms) / 1000),
    text: segment.snippet?.text || ''
  }));

  return res.json({
    video_title: info.basic_info?.title || 'Unknown',
    language: track.name?.text || language_code,
    preview
  });
}

async function handleGetVideoStreams(body, res) {
  const { url } = body;
  if (!url) return res.status(400).json({ detail: 'URL is required' });

  const videoId = getVideoId(url);
  const yt = await getInnertube();
  const info = await yt.getInfo(videoId);

  const title = info.basic_info?.title || 'Unknown';
  const thumbnail = info.basic_info?.thumbnail?.[0]?.url || `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`;

  const streams = [];

  // Progressive formats (video + audio) - use chooseFormat or streaming_data
  const formatOptions = info.streaming_data?.formats || [];
  for (const format of formatOptions) {
    const streamUrl = format.decipher ? format.decipher(yt.session.player) : format.url;
    if (streamUrl) {
      streams.push({
        type: 'video',
        quality: format.quality_label || format.quality || 'unknown',
        url: streamUrl,
        mimeType: format.mime_type,
        size: format.content_length ? `${(format.content_length / (1024 * 1024)).toFixed(1)} MB` : null
      });
    }
  }

  // Audio only from adaptive formats
  const adaptiveFormats = info.streaming_data?.adaptive_formats || [];
  for (const format of adaptiveFormats) {
    if (format.mime_type?.includes('audio')) {
      const streamUrl = format.decipher ? format.decipher(yt.session.player) : format.url;
      if (streamUrl) {
        streams.push({
          type: 'audio',
          quality: format.audio_quality || (format.bitrate ? `${Math.round(format.bitrate / 1000)}kbps` : 'unknown'),
          url: streamUrl,
          mimeType: format.mime_type,
          size: format.content_length ? `${(format.content_length / (1024 * 1024)).toFixed(1)} MB` : null
        });
      }
    }
  }

  return res.json({
    title,
    thumbnail,
    video_id: videoId,
    streams
  });
}
