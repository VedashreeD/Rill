import type { IllustrationVariant } from "../types";

/**
 * Small stylized scene illustrations for each of the 10 fictional Cindervale
 * Watershed locations. Entirely original geometric art (no photos, no real
 * places) — five variants, reused across the 10 locations per app/world.py.
 */

const SKY = (
  <>
    <rect x="0" y="0" width="240" height="95" fill="var(--sky-top)" />
    <rect x="0" y="70" width="240" height="30" fill="var(--sky-bottom)" opacity="0.6" />
  </>
);

function Water({ variant }: { variant: IllustrationVariant }) {
  return (
    <>
      <rect x="0" y="95" width="240" height="65" fill="var(--water)" />
      {variant === "wetland" ? (
        <rect x="0" y="95" width="240" height="65" fill="var(--water-light)" opacity="0.35" />
      ) : (
        <>
          <path d="M0 108 Q 30 103 60 108 T 120 108 T 180 108 T 240 108" stroke="var(--water-light)" strokeWidth="2" fill="none" opacity="0.55" />
          <path d="M0 126 Q 30 121 60 126 T 120 126 T 180 126 T 240 126" stroke="var(--water-light)" strokeWidth="2" fill="none" opacity="0.4" />
          <path d="M0 144 Q 30 139 60 144 T 120 144 T 180 144 T 240 144" stroke="var(--water-light)" strokeWidth="2" fill="none" opacity="0.3" />
        </>
      )}
    </>
  );
}

function Calm() {
  return (
    <>
      <circle cx="195" cy="35" r="14" fill="var(--paper-raised)" opacity="0.85" />
    </>
  );
}

function Rocky() {
  return (
    <>
      <polygon points="40,95 55,72 70,95" fill="var(--rock)" />
      <polygon points="90,95 108,65 128,95" fill="var(--rock)" />
      <polygon points="150,95 162,78 176,95" fill="var(--rock)" />
      <path d="M50 88 q6 -5 12 0" stroke="var(--paper-raised)" strokeWidth="2" fill="none" opacity="0.7" />
      <path d="M100 88 q7 -5 14 0" stroke="var(--paper-raised)" strokeWidth="2" fill="none" opacity="0.7" />
    </>
  );
}

function Wooded() {
  const trees = [18, 44, 205, 222];
  return (
    <>
      {trees.map((x, i) => (
        <g key={x}>
          <rect x={x - 2} y={78} width="4" height="20" fill="var(--earth)" />
          <polygon
            points={`${x},50 ${x - 14},80 ${x + 14},80`}
            fill={i % 2 === 0 ? "var(--foliage)" : "var(--foliage-dark)"}
          />
          <polygon
            points={`${x},62 ${x - 11},85 ${x + 11},85`}
            fill={i % 2 === 0 ? "var(--foliage-dark)" : "var(--foliage)"}
          />
        </g>
      ))}
    </>
  );
}

function Bridge() {
  return (
    <>
      <rect x="20" y="70" width="10" height="26" fill="var(--structure)" />
      <rect x="210" y="70" width="10" height="26" fill="var(--structure)" />
      <rect x="15" y="64" width="210" height="8" fill="var(--structure)" />
      <rect x="45" y="72" width="6" height="20" fill="var(--structure)" opacity="0.8" />
      <rect x="85" y="72" width="6" height="20" fill="var(--structure)" opacity="0.8" />
      <rect x="125" y="72" width="6" height="20" fill="var(--structure)" opacity="0.8" />
      <rect x="165" y="72" width="6" height="20" fill="var(--structure)" opacity="0.8" />
    </>
  );
}

function Wetland() {
  const reeds = [30, 42, 58, 175, 190, 205];
  return (
    <>
      {reeds.map((x, i) => (
        <g key={x}>
          <path
            d={`M${x} 100 Q ${x + 3} 80 ${x} 62`}
            stroke="var(--foliage)"
            strokeWidth="2.5"
            fill="none"
          />
          <ellipse cx={x} cy={62} rx="2.5" ry="6" fill={i % 2 === 0 ? "var(--foliage)" : "var(--foliage-dark)"} />
        </g>
      ))}
    </>
  );
}

const VARIANT_OVERLAY: Record<IllustrationVariant, () => JSX.Element> = {
  calm: Calm,
  rocky: Rocky,
  wooded: Wooded,
  bridge: Bridge,
  wetland: Wetland,
};

export default function LocationArt({
  variant,
  className,
}: {
  variant: IllustrationVariant;
  className?: string;
}) {
  const Overlay = VARIANT_OVERLAY[variant];
  return (
    <svg viewBox="0 0 240 160" className={className} role="img" aria-label={`${variant} stream scene`}>
      {SKY}
      <Overlay />
      <Water variant={variant} />
    </svg>
  );
}
