const EXT_TO_MIME = {
    '.mp4': 'video/mp4',
    '.m4v': 'video/mp4',
    '.mov': 'video/quicktime',
    '.webm': 'video/webm',
    '.ogv': 'video/ogg',
};

/**
 * MIME type hint for Video.js when playing a remote progressive file from URL path.
 */
export function mimeTypeForDirectProgressiveUrl(url) {
    if (typeof url !== 'string' || !url.trim()) {
        return 'video/mp4';
    }
    try {
        const path = new URL(url.trim()).pathname.toLowerCase();
        const entries = Object.entries(EXT_TO_MIME);
        for (let i = 0; i < entries.length; i += 1) {
            if (path.endsWith(entries[i][0])) {
                return entries[i][1];
            }
        }
    } catch (e) {
        // invalid URL — fall through
    }
    return 'video/mp4';
}
