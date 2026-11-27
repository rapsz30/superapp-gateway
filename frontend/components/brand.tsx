type BrandVariant = 'horizontal' | 'compact' | 'mark'

const brandAssets: Record<BrandVariant, string> = {
  horizontal: '/brand/student-gateway-horizontal.svg',
  compact: '/brand/student-gateway-compact.svg',
  mark: '/brand/student-gateway-mark.svg',
}

export function BrandLogo({ variant = 'horizontal', className }: { variant?: BrandVariant; className?: string }) {
  return <img className={className} src={brandAssets[variant]} alt="Student Gateway" />
}

export function BrandedLoading({ message = 'Memuat...' }: { message?: string }) {
  return (
    <div className="brand-loading" role="status" aria-live="polite">
      <BrandLogo variant="mark" className="brand-loading-logo" />
      <span className="brand-loading-spinner" aria-hidden="true" />
      <span className="brand-loading-message">{message}</span>
    </div>
  )
}
