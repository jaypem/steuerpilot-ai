"use client";

import { ReactNode, ButtonHTMLAttributes } from 'react';
import { LucideIcon } from 'lucide-react';

type ButtonVariant =
  | 'primary'
  | 'secondary'
  | 'danger'
  | 'ghost'
  | 'icon'
  | 'icon-sm'
  | 'tab'
  | 'filter'
  | 'toggle'
  | 'pill';

type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: LucideIcon;
  iconPosition?: 'left' | 'right';
  children?: ReactNode;
  loading?: boolean;
  fullWidth?: boolean;
  active?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'secondary',
  size = 'md',
  icon: Icon,
  iconPosition = 'left',
  children,
  loading = false,
  fullWidth = false,
  active = false,
  className = '',
  disabled,
  ...props
}) => {
  const baseStyles = 'inline-flex items-center justify-center gap-2 font-medium transition-all focus:outline-none focus:ring-2 focus:ring-offset-2';

  const variantStyles: Record<ButtonVariant, string> = {
    primary:    'bg-accent hover:bg-accent-hover active:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed text-white focus:ring-accent',
    secondary:  'text-foreground hover:bg-border active:bg-border disabled:opacity-50 disabled:cursor-not-allowed focus:ring-border',
    danger:     'text-red-600 hover:bg-red-50 active:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed focus:ring-red-500',
    ghost:      'text-muted hover:text-foreground hover:bg-border active:bg-border disabled:opacity-50 disabled:cursor-not-allowed focus:ring-border',
    icon:       'p-2.5 sm:p-2 text-muted hover:bg-border active:bg-border disabled:opacity-50 disabled:cursor-not-allowed focus:ring-border rounded-lg min-w-[44px] min-h-[44px] sm:min-w-0 sm:min-h-0',
    'icon-sm':  'p-2 sm:p-1.5 text-muted hover:bg-border active:bg-border disabled:opacity-50 disabled:cursor-not-allowed focus:ring-border rounded transition-colors min-w-[40px] min-h-[40px] sm:min-w-0 sm:min-h-0',
    tab: active
      ? 'px-4 py-2 text-sm bg-surface-raised text-foreground shadow-sm rounded-md border border-border focus:ring-accent'
      : 'px-4 py-2 text-sm text-muted hover:text-foreground hover:bg-border rounded-md border border-transparent focus:ring-border',
    filter:     'w-full justify-between py-2 px-2 text-sm hover:bg-surface text-foreground rounded transition-colors focus:ring-border',
    toggle: active
      ? 'px-3 py-2 text-sm border-2 border-accent bg-accent-subtle text-accent rounded-lg shadow-sm focus:ring-accent'
      : 'px-3 py-2 text-sm border-2 border-border hover:border-muted text-muted rounded-lg focus:ring-border',
    pill: active
      ? 'px-2.5 py-1 text-xs rounded-full bg-accent text-white hover:bg-accent-hover focus:ring-accent'
      : 'px-2.5 py-1 text-xs rounded-full bg-border text-muted hover:bg-border focus:ring-border',
  };

  const sizeStyles: Record<ButtonSize, string> = {
    sm: ['icon', 'icon-sm', 'tab', 'filter', 'toggle', 'pill'].includes(variant) ? '' : 'px-3 py-1.5 text-sm rounded-lg',
    md: ['icon', 'icon-sm', 'tab', 'filter', 'toggle', 'pill'].includes(variant) ? '' : 'px-4 py-2 text-sm rounded-lg',
    lg: ['icon', 'icon-sm', 'tab', 'filter', 'toggle', 'pill'].includes(variant) ? '' : 'px-6 py-3 text-base rounded-xl',
  };

  const iconSizeClass: Record<ButtonSize, string> = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6',
  };

  const combinedClassName = `${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${fullWidth ? 'w-full' : ''} ${className}`.trim().replace(/\s+/g, ' ');

  return (
    <button className={combinedClassName} disabled={disabled || loading} {...props}>
      {loading ? (
        <>
          <div className={`animate-spin rounded-full border-2 border-border border-t-transparent ${iconSizeClass[size]}`} />
          {children && <span>{children}</span>}
        </>
      ) : (
        <>
          {Icon && iconPosition === 'left'  && <Icon className={iconSizeClass[size]} />}
          {children && <span>{children}</span>}
          {Icon && iconPosition === 'right' && <Icon className={iconSizeClass[size]} />}
        </>
      )}
    </button>
  );
};
