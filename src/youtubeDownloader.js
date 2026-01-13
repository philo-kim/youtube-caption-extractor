import { Innertube } from 'youtubei.js';
import { BG, buildURL, GOOG_API_KEY } from 'bgutils-js';

// Visitor Data와 PO Token을 저장하는 캐시
let cachedSession = null;

/**
 * PO Token과 Visitor Data를 생성합니다.
 */
async function generatePoToken() {
  try {
    // InnerTube 인스턴스 생성
    const innertube = await Innertube.create({ retrieve_player: false });

    // Challenge 데이터 가져오기
    const requestKey = 'O43z0dpjhgX20SCx4KAo';
    const challengeResponse = await innertube.session.player?.getPoToken(requestKey);

    if (!challengeResponse) {
      // Challenge가 없으면 기본 방식으로 시도
      const visitorData = innertube.session.context.client.visitorData;
      return { visitorData, poToken: null };
    }

    const { program, globalName, bgChallenge } = challengeResponse;

    // BotGuard VM 초기화
    if (program) {
      const interpreterUrl = buildURL(program, true);
      const vmResponse = await fetch(interpreterUrl);
      const vmScript = await vmResponse.text();
      new Function(vmScript)();
    }

    const bgInstance = new BG(globalName);

    // BotGuard 실행
    const poTokenResult = await bgInstance.invoke(bgChallenge);

    // Integrity Token 가져오기
    const integrityTokenResponse = await fetch(
      'https://jnn-pa.googleapis.com/$rpc/google.internal.waa.v1.Waa/GenerateIT',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json+protobuf',
          'x-goog-api-key': GOOG_API_KEY,
        },
        body: JSON.stringify([requestKey, poTokenResult.botguardResponse]),
      }
    );

    const integrityTokenData = await integrityTokenResponse.json();
    const integrityToken = integrityTokenData[0];

    // PO Token 민팅
    const getMinter = poTokenResult.webPoSignalOutput[0];
    const mintCallback = await getMinter(base64ToU8(integrityToken));
    const visitorData = innertube.session.context.client.visitorData;
    const result = await mintCallback(new TextEncoder().encode(visitorData));
    const poToken = u8ToBase64(result, true);

    return { visitorData, poToken };
  } catch (error) {
    console.error('PO Token 생성 실패:', error);
    return { visitorData: null, poToken: null };
  }
}

// Base64 변환 유틸리티
function base64ToU8(base64) {
  const binaryString = atob(base64);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes;
}

function u8ToBase64(u8, urlSafe = false) {
  let binary = '';
  for (let i = 0; i < u8.length; i++) {
    binary += String.fromCharCode(u8[i]);
  }
  let base64 = btoa(binary);
  if (urlSafe) {
    base64 = base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }
  return base64;
}

/**
 * 비디오 스트림 정보를 가져옵니다.
 * @param {string} videoUrl - YouTube 비디오 URL
 * @returns {Promise<Object>} - 비디오 정보와 스트림 목록
 */
export async function getVideoStreams(videoUrl) {
  try {
    // InnerTube 인스턴스 생성 (브라우저 환경에서 자동으로 PO Token 처리)
    const innertube = await Innertube.create({
      fetch: async (input, init) => {
        // 기본 fetch 사용
        return fetch(input, init);
      }
    });

    // Video ID 추출
    const videoIdMatch = videoUrl.match(/(?:v=|\/|be\/|embed\/)([a-zA-Z0-9_-]{11})/);
    if (!videoIdMatch) {
      throw new Error('유효한 YouTube URL이 아닙니다.');
    }
    const videoId = videoIdMatch[1];

    // 비디오 정보 가져오기
    const info = await innertube.getInfo(videoId);

    // 스트림 목록 구성
    const streams = [];

    // Progressive 스트림 (영상+오디오)
    const formats = info.streaming_data?.formats || [];
    for (const format of formats) {
      if (format.url) {
        streams.push({
          type: 'video',
          quality: format.quality_label || format.quality || 'unknown',
          url: format.url,
          mimeType: format.mime_type,
          size: format.content_length ? `${(format.content_length / (1024 * 1024)).toFixed(1)} MB` : null,
        });
      }
    }

    // Adaptive 스트림에서 오디오만 추출
    const adaptiveFormats = info.streaming_data?.adaptive_formats || [];
    for (const format of adaptiveFormats) {
      if (format.url && format.mime_type?.includes('audio')) {
        streams.push({
          type: 'audio',
          quality: format.audio_quality || format.bitrate ? `${Math.round(format.bitrate / 1000)}kbps` : 'unknown',
          url: format.url,
          mimeType: format.mime_type,
          size: format.content_length ? `${(format.content_length / (1024 * 1024)).toFixed(1)} MB` : null,
        });
      }
    }

    return {
      title: info.basic_info?.title || 'Unknown',
      thumbnail: info.basic_info?.thumbnail?.[0]?.url || `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`,
      duration: info.basic_info?.duration,
      streams: streams,
    };
  } catch (error) {
    console.error('비디오 스트림 가져오기 실패:', error);
    throw error;
  }
}

/**
 * 비디오 다운로드를 시작합니다.
 * @param {string} streamUrl - 스트림 URL
 */
export function downloadStream(streamUrl) {
  window.open(streamUrl, '_blank');
}
