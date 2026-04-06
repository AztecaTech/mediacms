import React from 'react';
import PropTypes from 'prop-types';

import ExternalEmbedClickShield, {
    isGoogleDriveFilePreviewEmbed,
} from './ExternalEmbedClickShield';

function getEmbedUrl(sourceUrl) {
    if (!sourceUrl) return null;

    const ytMatch = sourceUrl.match(
        /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/shorts\/)([a-zA-Z0-9_-]+)/
    );
    if (ytMatch) {
        return `https://www.youtube.com/embed/${ytMatch[1]}?modestbranding=1&rel=0&showinfo=0&disablekb=0`;
    }

    const vimeoMatch = sourceUrl.match(/vimeo\.com\/(\d+)/);
    if (vimeoMatch) {
        return `https://player.vimeo.com/video/${vimeoMatch[1]}?title=0&byline=0&portrait=0`;
    }

    const dmMatch = sourceUrl.match(/dailymotion\.com\/video\/([a-zA-Z0-9]+)/);
    if (dmMatch) {
        return `https://www.dailymotion.com/embed/video/${dmMatch[1]}?ui-logo=0&ui-start-screen-info=0`;
    }

    const driveMatch = sourceUrl.match(
        /(?:drive|docs)\.google\.com\/(?:file\/d\/|open\?(?:[^#]*&)?id=)([a-zA-Z0-9_-]+)/
    );
    if (driveMatch) {
        return `https://drive.google.com/file/d/${driveMatch[1]}/preview`;
    }

    return null;
}

export default function ExternalVideoEmbed({ sourceUrl, embedHtml, containerStyles }) {
    const embedUrl = getEmbedUrl(sourceUrl);
    const blockDriveFullscreen = isGoogleDriveFilePreviewEmbed(embedUrl);

    const wrapperStyle = {
        position: 'relative',
        width: '100%',
        paddingBottom: '56.25%',
        height: 0,
        overflow: 'hidden',
        background: '#000',
        borderRadius: '10px',
        ...(containerStyles || {}),
    };

    const iframeStyle = {
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        border: 'none',
    };

    if (embedUrl) {
        return (
            <div
                style={wrapperStyle}
                onContextMenu={(e) => e.preventDefault()}
            >
                <iframe
                    src={embedUrl}
                    style={iframeStyle}
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                    referrerPolicy="strict-origin-when-cross-origin"
                    allowFullScreen={!blockDriveFullscreen}
                    title="External video"
                />
                <ExternalEmbedClickShield embedUrl={embedUrl} sourceUrl={sourceUrl} />
            </div>
        );
    }

    if (embedHtml) {
        return (
            <div
                style={wrapperStyle}
                onContextMenu={(e) => e.preventDefault()}
            >
                <div
                    style={iframeStyle}
                    dangerouslySetInnerHTML={{ __html: embedHtml }}
                />
                <ExternalEmbedClickShield embedUrl="" sourceUrl={sourceUrl} />
            </div>
        );
    }

    return (
        <div style={{ ...wrapperStyle, display: 'flex', alignItems: 'center', justifyContent: 'center', paddingBottom: 0, height: '300px' }}>
            <span style={{ fontSize: '1.2em', color: '#fff' }}>
                Video unavailable
            </span>
        </div>
    );
}

ExternalVideoEmbed.propTypes = {
    sourceUrl: PropTypes.string.isRequired,
    embedHtml: PropTypes.string,
    containerStyles: PropTypes.object,
};

ExternalVideoEmbed.defaultProps = {
    embedHtml: '',
    containerStyles: null,
};
