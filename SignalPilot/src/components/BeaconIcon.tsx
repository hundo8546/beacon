interface BeaconIconProps {
  size?: number;
  variant?: 'blue' | 'navy' | 'mixed';
  className?: string;
}

export function BeaconIcon({ size = 120, variant = 'mixed', className = '' }: BeaconIconProps) {
  const waveColor = variant === 'navy' ? '#1e3a5f' : '#3b82f6';
  const baseColor = variant === 'blue' ? '#3b82f6' : '#475569';

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 120 120"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <circle
        cx="60"
        cy="32"
        r="6"
        fill={variant === 'mixed' ? waveColor : baseColor}
      />

      <path
        d="M42 28C42 20.268 48.268 14 56 14C63.732 14 70 20.268 70 28"
        stroke={waveColor}
        strokeWidth="6"
        strokeLinecap="round"
        transform="translate(4 0)"
      />

      <path
        d="M32 28C32 14.745 42.745 4 56 4C69.255 4 80 14.745 80 28"
        stroke={waveColor}
        strokeWidth="6"
        strokeLinecap="round"
        transform="translate(4 0)"
      />

      <path
        d="M45 46H75C77.2091 46 79 47.7909 79 50V58C79 60.2091 77.2091 62 75 62H45C42.7909 62 41 60.2091 41 58V50C41 47.7909 42.7909 46 45 46Z"
        stroke={baseColor}
        strokeWidth="4"
        fill="none"
      />

      <path
        d="M40 68H80C82.2091 68 84 69.7909 84 72V82C84 84.2091 82.2091 86 80 86H40C37.7909 86 36 84.2091 36 82V72C36 69.7909 37.7909 68 40 68Z"
        stroke={baseColor}
        strokeWidth="4"
        fill="none"
      />

      <path
        d="M35 92H85C87.2091 92 89 93.7909 89 96V108C89 110.209 87.2091 112 85 112H35C32.7909 112 31 110.209 31 108V96C31 93.7909 32.7909 92 35 92Z"
        stroke={baseColor}
        strokeWidth="4"
        fill="none"
      />
    </svg>
  );
}
