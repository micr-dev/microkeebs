import { useEffect, useRef, useState } from 'react';
import gsap from 'gsap';
import { useTheme } from '../contexts/use-theme';

/**
 * GSAP Preloader inspired by 888 Studio's "Preloader 1"
 * (https://gsap-preloaders.webflow.io/)
 *
 * A full-screen overlay with a responsive 3-row grid of keyboard
 * thumbnails. Images scale up from 0 with a stagger, then the panel
 * slides up and disappears to reveal the site.
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
    }
  | {
      type: 'brand';
      key: string;
      visibility?: SlotVisibility;
    };

// Six desktop slots per row mirror the Webflow source. Smaller breakpoints
// hide selected slots so each row still reads as a single 5-column or 3-column strip.
const PRELOADER_ROWS: PreloaderSlot[][] = [
  [
    { type: 'image', id: '7aM8Dg6wePs' },
    { type: 'image', id: 'bNFwVyN-PAA' },
    { type: 'empty', key: 'top-space', visibility: 'desktop-only' },
    { type: 'image', id: 'Qmlj4zgzUac', visibility: 'tablet-up' },
    { type: 'image', id: 'XdNu4YX4PSE', visibility: 'tablet-up' },
    { type: 'image', id: 'Vgo9UKqfSbI' },
  ],
  [
    { type: 'image', id: 'yYX5OJg1mIo' },
    { type: 'image', id: 'XYydztEvHdk', visibility: 'tablet-up' },
    { type: 'brand', key: 'microkeebs' },
    { type: 'empty', key: 'middle-space', visibility: 'desktop-only' },
    { type: 'image', id: 'oP6QJU2zwNg', visibility: 'tablet-up' },
    { type: 'image', id: 'H2IkaUvgVhs' },
  ],
  [
    { type: 'image', id: 'ISZuY2U3-6A' },
    { type: 'empty', key: 'bottom-space-a', visibility: 'tablet-up' },
    { type: 'image', id: 'tHxVcRIHGqU' },
    { type: 'image', id: 'dDN38OwMLnw', visibility: 'tablet-up' },
    { type: 'empty', key: 'bottom-space-b', visibility: 'desktop-only' },
    { type: 'image', id: 'BVmT-khkd5E' },
  ],
];

const visibilityClasses: Record<SlotVisibility, string> = {
  all: '',
  'tablet-up': 'hidden sm:block',
  'desktop-only': 'hidden lg:block',
};

export function Preloader() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(true);
  const { isDark } = useTheme();

  useEffect(() => {
    const preloader = containerRef.current;

    if (!visible || !preloader) return;

    const ctx = gsap.context(() => {
      const images = gsap.utils.toArray<HTMLImageElement>('.image_preloader');

      gsap.timeline({ onComplete: () => setVisible(false) })
        .from(images, {
          scale: 0,
          duration: 0.9,
          ease: 'power3.out',
          stagger: 0.12,
          force3D: true,
          transformOrigin: '50% 50%',
        })
        .from(
          '.preloader-brand',
          {
            opacity: 0,
            duration: 0.5,
            ease: 'power2.out',
          },
          0.5,
        )
        .to(preloader, {
          yPercent: -110,
          duration: 0.8,
          ease: 'power2.inOut',
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
      {PRELOADER_ROWS.map((row, rowIndex) => (
        <div
          key={rowIndex}
          className="grid min-h-0 grid-cols-3 gap-2 place-items-center sm:grid-cols-5 lg:grid-cols-6"
        >
          {row.map((slot) => {
            const slotClasses = `relative h-full min-h-0 w-full ${
              visibilityClasses[slot.visibility ?? 'all']
            }`;

            if (slot.type === 'empty') {
              return <div key={slot.key} className={slotClasses} />;
            }

            if (slot.type === 'brand') {
              return (
                <div
                  key={slot.key}
                  className={`${slotClasses} overflow-hidden text-center uppercase`}
                >
                  <div className="preloader-brand absolute inset-0 flex flex-col items-center justify-center">
                    <div className="text-3xl font-bold leading-none tracking-normal sm:text-4xl lg:text-5xl">
                      MICROKEEBS
                    </div>
                    <div className="mt-2 text-xs font-semibold tracking-normal opacity-70 sm:text-sm">
                      SOUND TESTS
                    </div>
                  </div>
                </div>
              );
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
    </div>
  );
}
