import React from 'react';
import PropTypes from 'prop-types';

function getEmbedUrl(sourceUrl) {
    if (!sourceUrl) return null;

    const ytMatch = sourceUrl.match(
        /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/shorts\/)([a-zA-Z0-9_-]+)/
    );
    if (ytMatch) {
        return `https://www.youtube.com/embed/${ytMatch[1]}`;
    }

    const vimeoMatch = sourceUrl.match(/vimeo\.com\/(\d+)/);
    if (vimeoMatch) {
        return `https://player.vimeo.com/video/${vimeoMatch[1]}`;
    }

    const dmMatch = sourceUrl.match(/dailymotion\.com\/video\/([a-zA-Z0-9]+)/);
    if (dmMatch) {
        return `https://www.dailymotion.com/embed/video/${dmMatch[1]}`;
    }

    return null;
}

export default function ExternalVideoEmbed({ sourceUrl, embedHtml }) {
    const embedUrl = getEmbedUrl(sourceUrl);

    const wrapperStyle = {
        position: 'relative',
        width: '100%',
        paddingBottom: '56.25%',
        height: 0,
        overflow: 'hidden',
        background: '#000',
        borderRadius: '10px',
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
            <div style={wrapperStyle}>
                <iframe
                    src={embedUrl}
                    style={iframeStyle}
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                    referrerPolicy="strict-origin-when-cross-origin"
                    allowFullScreen
                    title="External video"
                />
            </div>
        );
    }

    if (embedHtml) {
        return (
            <div style={wrapperStyle} dangerouslySetInnerHTML={{ __html: embedHtml }} />
        );
    }

    return (
        <div style={{ ...wrapperStyle, display: 'flex', alignItems: 'center', justifyContent: 'center', paddingBottom: 0, height: '300px' }}>
            <a href={sourceUrl} target="_blank" rel="noopener noreferrer" style={{ fontSize: '1.2em', color: '#fff' }}>
                Open video in new tab
            </a>
        </div>
    );
}

ExternalVideoEmbed.propTypes = {
    sourceUrl: PropTypes.string.isRequired,
    embedHtml: PropTypes.string,
};

ExternalVideoEmbed.defaultProps = {
    embedHtml: '',
};
