interface PageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

export function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  return (
    <div className="flex items-start justify-between px-6 pt-6 pb-4 border-b border-border">
      <div>
        <h1 className="text-lg font-semibold text-fg-base tracking-wide">{title}</h1>
        {subtitle && (
          <p className="text-xs text-fg-subtle mt-0.5">{subtitle}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
