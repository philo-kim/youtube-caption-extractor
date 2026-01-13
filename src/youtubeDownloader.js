import { BG } from 'bgutils-js';

const GOOG_API_KEY = 'AIzaSyDyT5W0Jh49F30Pqqtyfdf7pDLFKLJoAnw';
const REQUEST_KEY = 'O43z0dpjhgX20SCx4KAo';

/**
 * WAA API를 통해 PO Token과 Visitor Data를 생성합니다.
 * WAA API는 CORS를 허용하므로 브라우저에서 직접 호출 가능합니다.
 */
export async function generatePoToken() {
  try {
    // 1. WAA Create API로 Challenge 가져오기
    const createResponse = await fetch(
      'https://jnn-pa.googleapis.com/$rpc/google.internal.waa.v1.Waa/Create',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json+protobuf',
          'x-goog-api-key': GOOG_API_KEY,
          'x-user-agent': 'grpc-web-javascript/0.1',
        },
        body: JSON.stringify([REQUEST_KEY]),
      }
    );

    if (!createResponse.ok) {
      throw new Error(`WAA Create API 오류: ${createResponse.status}`);
    }

    const createData = await createResponse.json();

    // Challenge 데이터 파싱
    // 응답 형식: [program, globalName, challenge, ...]
    const [program, globalName, challenge] = createData;

    if (!program || !challenge) {
      throw new Error('Challenge 데이터가 없습니다.');
    }

    // 2. BotGuard VM 로드 및 실행
    const interpreterUrl = `https://www.google.com/js/bg/${program}.js`;
    const vmResponse = await fetch(interpreterUrl);
    const vmScript = await vmResponse.text();

    // VM 스크립트 실행
    // eslint-disable-next-line no-new-func
    new Function(vmScript)();

    // 3. BotGuard 인스턴스 생성 및 Challenge 실행
    const bgInstance = new BG(globalName);
    const botguardResult = await bgInstance.invoke(challenge);

    if (!botguardResult || !botguardResult.botguardResponse) {
      throw new Error('BotGuard 실행 실패');
    }

    // 4. Integrity Token 생성
    const integrityResponse = await fetch(
      'https://jnn-pa.googleapis.com/$rpc/google.internal.waa.v1.Waa/GenerateIT',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json+protobuf',
          'x-goog-api-key': GOOG_API_KEY,
          'x-user-agent': 'grpc-web-javascript/0.1',
        },
        body: JSON.stringify([REQUEST_KEY, botguardResult.botguardResponse]),
      }
    );

    if (!integrityResponse.ok) {
      throw new Error(`Integrity Token 생성 오류: ${integrityResponse.status}`);
    }

    const integrityData = await integrityResponse.json();
    const integrityToken = integrityData[0];

    if (!integrityToken) {
      throw new Error('Integrity Token이 없습니다.');
    }

    // 5. Visitor Data 생성 (랜덤 생성)
    const visitorData = generateVisitorData();

    // 6. PO Token 민팅
    if (!botguardResult.webPoSignalOutput || !botguardResult.webPoSignalOutput[0]) {
      throw new Error('WebPoMinter를 찾을 수 없습니다.');
    }

    const getMinter = botguardResult.webPoSignalOutput[0];
    const mintCallback = await getMinter(base64ToU8(integrityToken));
    const mintResult = await mintCallback(new TextEncoder().encode(visitorData));
    const poToken = u8ToBase64(mintResult, true);

    console.log('PO Token 생성 성공:', { visitorData: visitorData.substring(0, 20) + '...', poToken: poToken.substring(0, 20) + '...' });

    return { visitorData, poToken };
  } catch (error) {
    console.error('PO Token 생성 실패:', error);
    throw error;
  }
}

/**
 * Visitor Data 생성 (YouTube 형식과 유사하게)
 */
function generateVisitorData() {
  // Visitor Data는 Base64 인코딩된 프로토버프 형식
  // 간단한 랜덤 ID 생성
  const randomBytes = new Uint8Array(16);
  crypto.getRandomValues(randomBytes);

  // YouTube 스타일 Visitor ID 생성
  const visitorId = u8ToBase64(randomBytes, true);

  // 프로토버프 형식으로 인코딩 (simplified)
  // 실제로는 더 복잡한 구조이지만, 기본적인 형식 사용
  const timestamp = Math.floor(Date.now() / 1000);
  const data = new Uint8Array([
    0x0a, 0x10, // field 1, length 16
    ...randomBytes,
    0x10, // field 2, varint
    ...encodeVarint(timestamp),
  ]);

  return u8ToBase64(data, false);
}

/**
 * Varint 인코딩
 */
function encodeVarint(value) {
  const result = [];
  while (value > 127) {
    result.push((value & 0x7f) | 0x80);
    value >>>= 7;
  }
  result.push(value);
  return result;
}

/**
 * Base64를 Uint8Array로 변환
 */
function base64ToU8(base64) {
  // URL-safe base64 처리
  const normalized = base64.replace(/-/g, '+').replace(/_/g, '/');
  const padded = normalized + '='.repeat((4 - normalized.length % 4) % 4);
  const binaryString = atob(padded);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes;
}

/**
 * Uint8Array를 Base64로 변환
 */
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
 * 비디오 다운로드를 시작합니다.
 */
export function downloadStream(streamUrl) {
  window.open(streamUrl, '_blank');
}
