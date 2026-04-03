import React from 'react';
import PropTypes from 'prop-types';

function getEmbedUrl(sourceUrl) {
    if (!sourceUrl) return null;

    const ytMatch = sourceUrl.match(
        /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/shorts\/)([a-zA-Z0-9_-]+)/
    );
    if (ytMatch) {
        return `https://www.youtube-nocookie.com/embed/${ytMatch[1]}`;
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

export default function ExternalVideoEmbed({ sourceUrl, embedHtml, containerStyles }) {
    const embedUrl = getEmbedUrl(sourceUrl);

    if (embedUrl) {
        return (
            <div className="player-container external-video-container" style={containerStyles}>
                <div className="player-container-inner">
                    <iframe
                        src={embedUrl}
                        style={{
                            width: '100%',
                            height: '100%',
                            border: 'none',
                        }}
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                        allowFullScreen
                        title="External video"
                    />
                </div>
            </div>
        );
    }

    if (embedHtml) {
        return (
            <div
                className="player-container external-video-container"
                style={containerStyles}
                dangerouslySetInnerHTML={{ __html: embedHtml }}
            />
        );
    }

    return (
        <div className="player-container external-video-container" style={containerStyles}>
            <div className="player-container-inner" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <a href={sourceUrl} target="_blank" rel="noopener noreferrer" style={{ fontSize: '1.2em' }}>
                    Open video in new tab
                </a>
            </div>
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
    containerStyles: {},
};
