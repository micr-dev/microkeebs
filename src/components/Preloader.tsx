import { useEffect, useMemo, useRef, useState } from 'react';
import gsap from 'gsap';
import { useTheme } from '../contexts/use-theme';
import buildsData from '../data/builds.json';

/**
 * GSAP Preloader inspired by 888 Studio's "Preloader 1"
 * (https://gsap-preloaders.webflow.io/)
 *
 * A full-screen overlay with a responsive 3-row grid of keyboard
 * thumbnails. Images scale up from 0 with a stagger, then the panel
 * slides up and disappears to reveal the site.
 *
 * The brand text is absolutely positioned over the middle row at the
 * far right edge so it doesn't overlap any thumbnail.
 */

type SlotVisibility = 'all' | 'tablet-up' | 'desktop-only';

type PreloaderSlot =
  | {
      type: 'image';
      id: string;
      visibility?: SlotVisibility;
    }
  | {
      type: 'empty';
      key: string;
      visibility?: SlotVisibility;
    };

// Six desktop slots per row mirror the Webflow source. Smaller breakpoints
// hide selected slots so each row still reads as a single 5-column or 3-column strip.
function getPreloaderRows(randomIds: string[]): PreloaderSlot[][] {
  return [
    [
      { type: 'image', id: randomIds[0] },
      { type: 'image', id: randomIds[1] },
      { type: 'empty', key: 'top-space', visibility: 'desktop-only' },
      { type: 'image', id: randomIds[2], visibility: 'tablet-up' },
      { type: 'image', id: randomIds[3], visibility: 'tablet-up' },
      { type: 'image', id: randomIds[4] },
    ],
    [
      { type: 'image', id: randomIds[5] },
      { type: 'image', id: randomIds[6], visibility: 'tablet-up' },
      { type: 'image', id: randomIds[13], visibility: 'tablet-up' },
      { type: 'empty', key: 'middle-space', visibility: 'desktop-only' },
      { type: 'empty', key: 'middle-space-r1', visibility: 'all' },
      { type: 'empty', key: 'middle-space-r2', visibility: 'all' },
    ],
    [
      { type: 'image', id: randomIds[9] },
      { type: 'empty', key: 'bottom-space-a', visibility: 'tablet-up' },
      { type: 'image', id: randomIds[10] },
      { type: 'image', id: randomIds[11], visibility: 'tablet-up' },
      { type: 'empty', key: 'bottom-space-b', visibility: 'desktop-only' },
      { type: 'image', id: randomIds[12] },
    ],
  ];
}

const visibilityClasses: Record<SlotVisibility, string> = {
  all: '',
  'tablet-up': 'hidden sm:block',
  'desktop-only': 'hidden lg:block',
};

export function Preloader() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(true);
  const { isDark } = useTheme();
  const eligibleBuildIds = useMemo(() => {
    // Only use builds as recent as or newer than Chilkey ND TKL and the first Diversity TKL
    const cutoff = new Date('2024-11-19T15:18:00Z').getTime();
    return buildsData
      .filter((build: { id: string; timestamp: string }) => new Date(build.timestamp).getTime() >= cutoff)
      .map((build: { id: string }) => build.id);
  }, []);
  const randomIds = useMemo(() => {
    const shuffled = [...eligibleBuildIds].sort(() => Math.random() - 0.5);
    return shuffled.slice(0, 16);
  }, [eligibleBuildIds]);
  const preloaderRows = useMemo(() => getPreloaderRows(randomIds), [randomIds]);

  useEffect(() => {
    const preloader = containerRef.current;

    if (!visible || !preloader) return;

    const ctx = gsap.context(() => {
      const images = gsap.utils.toArray<HTMLImageElement>('.image_preloader');

      gsap.timeline({ onComplete: () => setVisible(false) })
        .from(images, {
          scale: 0,
          yPercent: -50,
          duration: 1,
          ease: 'power1.out',
          stagger: 0.2,
          force3D: true,
          transformOrigin: '50% 50%',
        })
        .from(
          '.preloader-brand',
          {
            opacity: 0,
            xPercent: 25,
            duration: 0.5,
            ease: 'power1.out',
          },
          0.5,
        )
        .to(preloader, {
          yPercent: -110,
          duration: 0.6,
          ease: 'power1.out',
          force3D: true,
        });
    }, preloader);

    return () => ctx.revert();
  }, [visible]);

  if (!visible) return null;

  const themeClasses = isDark
    ? 'bg-[#1c1c1c] text-[#a7a495]'
    : 'bg-[#a7a495] text-[#1c1c1c]';

  return (
    <div
      ref={containerRef}
      aria-hidden="true"
      className={`fixed inset-0 z-[9999] grid grid-rows-3 gap-2 overflow-hidden p-2 transform-gpu backface-hidden will-change-transform ${themeClasses}`}
    >
      {preloaderRows.map((row, rowIndex) => (
        <div
          key={rowIndex}
          className="relative grid min-h-0 grid-cols-3 gap-2 place-items-center sm:grid-cols-5 lg:grid-cols-6"
        >
          {row.map((slot) => {
            const slotClasses = `relative h-full min-h-0 w-full ${
              visibilityClasses[slot.visibility ?? 'all']
            }`;

            if (slot.type === 'empty') {
              return <div key={slot.key} className={slotClasses} />;
            }

            return (
              <div key={slot.id} className={`${slotClasses} overflow-hidden`}>
                <img
                  src={`./images/${slot.id}/thumbnail.jpg`}
                  alt=""
                  loading="eager"
                  decoding="async"
                  className="image_preloader absolute inset-0 h-full w-full origin-center object-cover will-change-transform"
                />
              </div>
            );
          })}
        </div>
      ))}

      {/* Brand text — absolutely positioned over middle row only, right-aligned */}
      <div className="preloader-brand pointer-events-none absolute right-0 flex items-center justify-end pr-4 sm:pr-8 lg:pr-12" style={{ top: '33.333%', bottom: '33.333%' }}>
        <div className="text-right uppercase">
          <div className="text-3xl font-bold leading-none tracking-normal sm:text-4xl lg:text-5xl">
            MICROKEEBS
          </div>
          <div className="mt-2 text-xs font-semibold tracking-normal opacity-70 sm:text-sm">
            SOUND TESTS
          </div>
        </div>
      </div>
    </div>
  );
}
