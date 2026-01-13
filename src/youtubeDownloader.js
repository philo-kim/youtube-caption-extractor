/**
 * 비디오 다운로드를 시작합니다.
 * @param {string} streamUrl - 스트림 URL
 */
export function downloadStream(streamUrl) {
  window.open(streamUrl, '_blank');
}
