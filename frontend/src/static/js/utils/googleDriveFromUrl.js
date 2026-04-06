/**
 * Extract Google Drive file id from common share / open / uc URLs.
 * @see https://developers.google.com/drive/api/guides/about-files
 */
const GOOGLE_DRIVE_FILE_ID_RE =
    /(?:drive|docs)\.google\.com(?:\/a\/[^/]+)?\/(?:(?:drive\/(?:u\/\d+\/)?)?file\/d\/|file\/(?:u\/\d+\/)?d\/|open\?(?:[^#]*&)?id=|uc\?(?:[^#]*&)?id=)([a-zA-Z0-9_-]+)/;

export function extractGoogleDriveFileId(sourceUrl) {
    if (!sourceUrl || typeof sourceUrl !== 'string') return null;
    const m = sourceUrl.trim().match(GOOGLE_DRIVE_FILE_ID_RE);
    return m ? m[1] : null;
}

export function getGoogleDrivePreviewEmbedUrl(sourceUrl) {
    const id = extractGoogleDriveFileId(sourceUrl);
    return id ? `https://drive.google.com/file/d/${id}/preview` : null;
}

export function isGoogleDriveVideoUrl(sourceUrl) {
    return extractGoogleDriveFileId(sourceUrl) != null;
}
