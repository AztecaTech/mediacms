import React, { useCallback, useEffect, useState } from 'react';

import '../../../css/home-promo-carousel.css';

type PromoSlide = { image: string; link: string; alt: string };

function readSlides(): PromoSlide[] {
    try {
        const raw = window.MediaCMS?.site?.homePromoSlides;
        if (Array.isArray(raw) && raw.length) {
            return raw.filter((s) => s && typeof s.image === 'string' && s.image) as PromoSlide[];
        }
    } catch (e) {
        /* ignore */
    }
    return [];
}

export const HomePromoCarousel: React.FC = () => {
    const [slides] = useState(readSlides);
    const [index, setIndex] = useState(0);
    const [paused, setPaused] = useState(false);

    useEffect(() => {
        if (slides.length <= 1 || paused) {
            return undefined;
        }
        const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
        if (mq.matches) {
            return undefined;
        }
        const id = window.setInterval(() => {
            setIndex((i) => (i + 1) % slides.length);
        }, 6000);
        return () => window.clearInterval(id);
    }, [slides.length, paused]);

    const go = useCallback(
        (delta: number) => {
            setIndex((i) => (i + delta + slides.length) % slides.length);
        },
        [slides.length]
    );

    if (!slides.length) {
        return null;
    }

    const slide = slides[index];
    const img = (
        <img
            className="home-promo-carousel__img"
            src={slide.image}
            alt={slide.alt || 'Promotional slide'}
            loading={index === 0 ? 'eager' : 'lazy'}
        />
    );

    return (
        <section
            className="home-promo-carousel"
            aria-label="Promotional slides"
            onMouseEnter={() => setPaused(true)}
            onMouseLeave={() => setPaused(false)}
        >
            <div className="home-promo-carousel__viewport">
                {slide.link ? (
                    <a href={slide.link} className="home-promo-carousel__link">
                        {img}
                    </a>
                ) : (
                    img
                )}
                {slides.length > 1 ? (
                    <>
                        <button
                            type="button"
                            className="home-promo-carousel__nav home-promo-carousel__nav--prev"
                            aria-label="Previous slide"
                            onClick={() => go(-1)}
                        >
                            ‹
                        </button>
                        <button
                            type="button"
                            className="home-promo-carousel__nav home-promo-carousel__nav--next"
                            aria-label="Next slide"
                            onClick={() => go(1)}
                        >
                            ›
                        </button>
                    </>
                ) : null}
            </div>
            {slides.length > 1 ? (
                <div className="home-promo-carousel__dots" role="tablist" aria-label="Slides">
                    {slides.map((_, i) => (
                        <button
                            key={i}
                            type="button"
                            role="tab"
                            aria-selected={i === index}
                            aria-label={`Slide ${i + 1}`}
                            className={'home-promo-carousel__dot' + (i === index ? ' is-active' : '')}
                            onClick={() => setIndex(i)}
                        />
                    ))}
                </div>
            ) : null}
        </section>
    );
};
