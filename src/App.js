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

  const API_BASE_URL = '/api';

  const extractVideoInfo = async () => {
    if (!url.trim()) {
      setError('YouTube URL을 입력해주세요.');
      return;
    }

    setLoading(true);
    setError('');
    setVideoInfo(null);
    setPreview(null);

    try {
      const response = await fetch(`${API_BASE_URL}/extract-info`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url: url,
          language_code: selectedLanguage,
          format: selectedFormat
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '비디오 정보 추출 실패');
      }

      const data = await response.json();
      setVideoInfo(data);

      if (data.available_captions.length > 0) {
        setSelectedLanguage(data.available_captions[0].languageCode);
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
        headers: {
          'Content-Type': 'application/json',
        },
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

      // 파일 다운로드
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      
      // 파일명 설정 로직 개선
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
        headers: {
          'Content-Type': 'application/json',
        },
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

  const getLanguageDisplayName = (caption) => {
    const name = caption.name || caption.languageCode;
    const isAuto = caption.kind === 'asr';
    return isAuto ? `${name} (자동생성)` : name;
  };

  return (
    <div className="app">
      <header className="header">
        <h1>YouTube 자막 추출기</h1>
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
            />
            <button
              onClick={extractVideoInfo}
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

        {/* 자막 선택 섹션 */}
        {videoInfo && (
          <div className="caption-section">
            <h3>사용 가능한 자막</h3>
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

            {/* 포맷 및 액션 섹션 */}
            <div className="action-section">
              <div className="format-selector">
                <label>다운로드 포맷:</label>
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
                  {loading ? '처리 중...' : '다운로드'}
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
            <h3>미리보기 - {preview.video_title} ({preview.language})</h3>
            <div className="preview-content">
              {preview.preview.map((caption, index) => (
                <div key={index} className="caption-item">
                  <span className="caption-time">{caption.time}</span>
                  <span className="caption-text">{caption.text}</span>
                </div>
              ))}
              {preview.total_captions > 10 && (
                <div className="more-captions">
                  ... 외 {preview.total_captions - 10}개 자막
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
