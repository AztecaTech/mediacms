/**
 * Minimal safe markdown subset for LMS text lessons (instructor-authored).
 * Escapes HTML first, then applies a few inline patterns and paragraph breaks.
 */
export function renderLmsMarkdownToHtml(src) {
  if (src == null || src === '') {
    return '';
  }
  let s = String(src)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  const paras = s.split(/\n\n+/);
  return paras
    .map((p) => {
      const inner = p.replace(/\n/g, '<br/>');
      return `<p>${inner}</p>`;
    })
    .join('');
}
