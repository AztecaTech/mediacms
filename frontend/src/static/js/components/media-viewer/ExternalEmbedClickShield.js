import React from 'react';
import PropTypes from 'prop-types';

/** Blocks pointer events over host toolbars (Drive download bar, YouTube header, etc.). Cross-origin; cannot remove UI inside the iframe. */
const SHIELD_BASE = {
    position: 'absolute',
    left: 0,
    right: 0,
    zIndex: 2,
    pointerEvents: 'auto',
    background: 'transparent',
};

export function isGoogleDriveFilePreviewEmbed(embedUrl) {
    return (
        typeof embedUrl === 'string' &&
        embedUrl.includes('drive.google.com/file/d/') &&
        embedUrl.includes('/preview')
    );
}

const DRIVE_SOURCE_RE = /(?:drive|docs)\.google\.com\/(?:file\/d\/|open\?(?:[^#]*&)?id=)/;

export function isGoogleDriveSourceUrl(sourceUrl) {
    return typeof sourceUrl === 'string' && DRIVE_SOURCE_RE.test(sourceUrl);
}

export default function ExternalEmbedClickShield({ embedUrl, sourceUrl }) {
    const isDrive = isGoogleDriveFilePreviewEmbed(embedUrl) || isGoogleDriveSourceUrl(sourceUrl);
    const topHeight = isDrive ? '5.75rem' : '3.75rem';

    return (
        <div
            className="external-embed-click-shield"
            aria-hidden="true"
            style={{
                ...SHIELD_BASE,
                top: 0,
                height: topHeight,
            }}
        />
    );
}

ExternalEmbedClickShield.propTypes = {
    embedUrl: PropTypes.string,
    sourceUrl: PropTypes.string,
};

ExternalEmbedClickShield.defaultProps = {
    embedUrl: '',
    sourceUrl: '',
};
