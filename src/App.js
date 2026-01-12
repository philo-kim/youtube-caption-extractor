import React, { useState } from 'react';
import './App.css';

function App() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [videoInfo, setVideoInfo] = useState(null);
  const [selectedLanguage, setSelectedLanguage] = useState('');
  const [selectedFormat, setSelectedFormat] = useState('srt');
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState('');
  const [videoStreams, setVideoStreams] = useState(null);

  const API_BASE_URL = '/api';

  // 통합 추출 함수 - 자막 + 동영상 정보 한번에
  const extractAll = async () => {
    if (!url.trim()) {
      setError('YouTube URL을 입력해주세요.');
      return;
    }

    setLoading(true);
    setError('');
    setVideoInfo(null);
    setVideoStreams(null);
    setPreview(null);

    try {
      // 자막 정보와 동영상 스트림을 병렬로 가져오기
      const [captionResponse, streamResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/extract-info`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url }),
        }),
        fetch(`${API_BASE_URL}/get-video-streams`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url }),
        }),
      ]);

      // 자막 정보 처리
      if (captionResponse.ok) {
        const captionData = await captionResponse.json();
        setVideoInfo(captionData);
        if (captionData.available_captions?.length > 0) {
          setSelectedLanguage(captionData.available_captions[0].languageCode);
        }
      }

      // 동영상 스트림 처리
      if (streamResponse.ok) {
        const streamData = await streamResponse.json();
        setVideoStreams(streamData);
      } else {
        const errorData = await streamResponse.json();
        console.error('동영상 스트림 오류:', errorData.detail);
      }

      // 둘 다 실패한 경우에만 에러 표시
      if (!captionResponse.ok && !streamResponse.ok) {
        throw new Error('정보 추출에 실패했습니다.');
      }

    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const downloadCaption = async () => {
    if (!selectedLanguage) {
      setError('자막 언어를 선택해주세요.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${API_BASE_URL}/download-caption`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: url,
          language_code: selectedLanguage,
          format: selectedFormat
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '다운로드 실패');
      }

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;

      let filename = `caption_${selectedLanguage}.${selectedFormat}`;
      const contentDisposition = response.headers.get('content-disposition');
      if (contentDisposition && contentDisposition.includes('filename=')) {
        filename = contentDisposition.split('filename=')[1].replace(/"/g, '');
      }

      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);

    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const showPreview = async () => {
    if (!selectedLanguage) {
      setError('자막 언어를 선택해주세요.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${API_BASE_URL}/preview-caption`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: url,
          language_code: selectedLanguage,
          format: selectedFormat
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '미리보기 실패');
      }

      const data = await response.json();
      setPreview(data);

    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const downloadVideo = (streamUrl) => {
    window.open(streamUrl, '_blank');
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '알 수 없음';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) {
      return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const getLanguageDisplayName = (caption) => {
    const name = caption.name || caption.languageCode;
    const isAuto = caption.kind === 'asr';
    return isAuto ? `${name} (자동생성)` : name;
  };

  return (
    <div className="app">
      <header className="header">
        <h1>YouTube 자막 & 동영상 다운로더</h1>
      </header>

      <main className="main">
        {/* URL 입력 섹션 */}
        <div className="input-section">
          <div className="input-group">
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="YouTube URL을 입력하세요 (https://www.youtube.com/watch?v=...)"
              className="url-input"
              onKeyPress={(e) => e.key === 'Enter' && extractAll()}
            />
            <button
              onClick={extractAll}
              disabled={loading}
              className="extract-btn"
            >
              {loading ? '추출 중...' : '추출'}
            </button>
          </div>
        </div>

        {/* 에러 메시지 */}
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {/* 동영상 정보 섹션 */}
        {videoStreams && (
          <div className="video-section">
            <div className="video-info">
              <img src={videoStreams.thumbnail} alt="thumbnail" className="thumbnail" />
              <div className="video-details">
                <h3>{videoStreams.title}</h3>
                <p>길이: {formatDuration(videoStreams.duration)}</p>
              </div>
            </div>

            <h4>동영상 다운로드</h4>
            <div className="streams-list">
              {videoStreams.streams.filter(s => s.type === 'video').slice(0, 5).map((stream, index) => (
                <div key={index} className="stream-item">
                  <span className="stream-quality">🎬 {stream.quality}</span>
                  <span className="stream-size">{stream.filesize_mb ? `${stream.filesize_mb} MB` : ''}</span>
                  <button
                    onClick={() => downloadVideo(stream.url)}
                    className="stream-download-btn"
                  >
                    다운로드
                  </button>
                </div>
              ))}
              {videoStreams.streams.filter(s => s.type === 'audio').slice(0, 3).map((stream, index) => (
                <div key={`audio-${index}`} className="stream-item">
                  <span className="stream-quality">🎵 오디오 {stream.quality}</span>
                  <span className="stream-size">{stream.filesize_mb ? `${stream.filesize_mb} MB` : ''}</span>
                  <button
                    onClick={() => downloadVideo(stream.url)}
                    className="stream-download-btn"
                  >
                    다운로드
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 자막 선택 섹션 */}
        {videoInfo && videoInfo.available_captions?.length > 0 && (
          <div className="caption-section">
            <h4>자막 다운로드</h4>
            <div className="caption-list">
              {videoInfo.available_captions.map((caption, index) => (
                <label key={index} className="caption-option">
                  <input
                    type="radio"
                    name="language"
                    value={caption.languageCode}
                    checked={selectedLanguage === caption.languageCode}
                    onChange={(e) => setSelectedLanguage(e.target.value)}
                  />
                  <span>{getLanguageDisplayName(caption)}</span>
                </label>
              ))}
            </div>

            <div className="action-section">
              <div className="format-selector">
                <label>포맷:</label>
                <select
                  value={selectedFormat}
                  onChange={(e) => setSelectedFormat(e.target.value)}
                  className="format-select"
                >
                  <option value="srt">SRT</option>
                  <option value="vtt">VTT</option>
                  <option value="txt">TXT</option>
                </select>
              </div>

              <div className="action-buttons">
                <button
                  onClick={downloadCaption}
                  disabled={loading || !selectedLanguage}
                  className="download-btn"
                >
                  자막 다운로드
                </button>
                <button
                  onClick={showPreview}
                  disabled={loading || !selectedLanguage}
                  className="preview-btn"
                >
                  미리보기
                </button>
              </div>
            </div>
          </div>
        )}

        {/* 미리보기 섹션 */}
        {preview && (
          <div className="preview-section">
            <h4>자막 미리보기 ({preview.language})</h4>
            <div className="preview-content">
              {preview.preview.map((caption, index) => (
                <div key={index} className="caption-item">
                  <span className="caption-time">{caption.time}</span>
                  <span className="caption-text">{caption.text}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
