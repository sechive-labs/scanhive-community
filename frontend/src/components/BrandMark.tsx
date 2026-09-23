interface BrandMarkProps {
  size?: number;
  className?: string;
}

export function BrandMark({ size = 24, className }: BrandMarkProps) {
  return (
    <img
      className={className}
      width={size}
      height={size}
      src="/scanhive-favicon.svg"
      alt=""
      aria-hidden="true"
    />
  );
}

export function BrandLogo({ size = 144, className }: BrandMarkProps) {
  return <img className={className} width={size} height={size} src="/scanhive-logo.svg" alt="ScanHive" />;
}
