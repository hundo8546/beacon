import { BeaconIcon } from './BeaconIcon';

interface BeaconLogoProps {
  size?: 'small' | 'medium' | 'large';
  theme?: 'dark' | 'light';
  showText?: boolean;
  className?: string;
}

export function BeaconLogo({
  size = 'medium',
  theme = 'light',
  showText = true,
  className = ''
}: BeaconLogoProps) {
  const sizeMap = {
    small: { icon: 40, text: 'text-2xl' },
    medium: { icon: 80, text: 'text-5xl' },
    large: { icon: 120, text: 'text-7xl' }
  };

  const { icon, text } = sizeMap[size];
  const textColor = theme === 'dark' ? 'text-slate-200' : 'text-slate-800';
  const variant = theme === 'dark' ? 'mixed' : 'navy';

  return (
    <div className={`flex items-center gap-4 ${className}`}>
      <BeaconIcon size={icon} variant={variant} />
      {showText && (
        <span className={`font-bold ${text} ${textColor}`}>
          Beacon
        </span>
      )}
    </div>
  );
}
