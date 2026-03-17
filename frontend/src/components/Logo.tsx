

// OpenPond Custom Logo
export const OpenPondLogo = ({ className = "w-8 h-8" }: { className?: string }) => (
  <svg
    viewBox="0 0 100 100"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    fill="none"
  >
    {/* The Pond/Wave (Deep Cyan/Teal) */}
    <path
      d="M 10 70 Q 30 50, 50 70 T 90 70 L 90 90 L 10 90 Z"
      fill="#0ea5e9"
    />
    <path
      d="M 0 80 Q 25 60, 50 80 T 100 80 L 100 100 L 0 100 Z"
      fill="#0284c7"
    />

    {/* The '0' Leaping (Silver/White, angled) */}
    <g transform="translate(30, 45) rotate(15)">
      <ellipse
        cx="0"
        cy="-20"
        rx="8"
        ry="14"
        stroke="#1e293b"
        strokeWidth="4"
        fill="#f8fafc"
      />
    </g>

    {/* The '1' Leaping (Silver/White, angled, following the 0) */}
    <g transform="translate(60, 40) rotate(35)">
      <path
        d="M -3 -15 L 2 -25 L 2 5 M -6 5 L 10 5"
        stroke="#1e293b"
        strokeWidth="4"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Fill behind the 1 for solidity against wave */}
      <path
        d="M -3 -15 L 2 -25 L 2 5 M -6 5 L 10 5"
        stroke="#f8fafc"
        strokeWidth="2"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </g>

    {/* Small Splash droplets */}
    <circle cx="20" cy="55" r="3" fill="#38bdf8" />
    <circle cx="80" cy="45" r="4" fill="#38bdf8" />
    <circle cx="65" cy="55" r="2" fill="#7dd3fc" />
  </svg>
);
