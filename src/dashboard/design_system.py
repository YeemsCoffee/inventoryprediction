"""
DESIGN SYSTEM
==============

Comprehensive design system following industry best practices:
- Apple HIG principles
- Google Material Design 3
- Nielsen Norman Group UX guidelines
- WCAG 2.1 AA accessibility standards

Design Philosophy:
- 8px grid system for spacing and sizing
- Limited, purposeful color palette
- Clear visual hierarchy
- Consistent interaction patterns
- Progressive disclosure
- Accessible by default
"""


class DesignTokens:
    """Design tokens for the BI Dashboard."""

    # ==================== COLOR SYSTEM ====================

    # Light Theme Colors
    LIGHT_THEME = {
        # Primary Brand Colors
        'primary': {
            '50': '#EEF2FF',   # Lightest
            '100': '#E0E7FF',
            '200': '#C7D2FE',
            '300': '#A5B4FC',
            '400': '#818CF8',
            '500': '#6366F1',  # Base primary
            '600': '#4F46E5',  # Darker primary
            '700': '#4338CA',
            '800': '#3730A3',
            '900': '#312E81',  # Darkest
        },

        # Secondary Colors
        'secondary': {
            '50': '#F8FAFC',
            '100': '#F1F5F9',
            '200': '#E2E8F0',
            '300': '#CBD5E1',
            '400': '#94A3B8',
            '500': '#64748B',  # Base secondary
            '600': '#475569',
            '700': '#334155',
            '800': '#1E293B',
            '900': '#0F172A',
        },

        # Semantic Colors
        'success': {
            '50': '#F0FDF4',
            '500': '#10B981',  # Base
            '600': '#059669',
            '700': '#047857',
        },
        'warning': {
            '50': '#FFFBEB',
            '500': '#F59E0B',  # Base
            '600': '#D97706',
            '700': '#B45309',
        },
        'danger': {
            '50': '#FEF2F2',
            '500': '#EF4444',  # Base
            '600': '#DC2626',
            '700': '#B91C1C',
        },
        'info': {
            '50': '#EFF6FF',
            '500': '#3B82F6',  # Base
            '600': '#2563EB',
            '700': '#1D4ED8',
        },

        # Neutral Grays
        'neutral': {
            '0': '#FFFFFF',
            '50': '#F9FAFB',
            '100': '#F3F4F6',
            '200': '#E5E7EB',
            '300': '#D1D5DB',
            '400': '#9CA3AF',
            '500': '#6B7280',
            '600': '#4B5563',
            '700': '#374151',
            '800': '#1F2937',
            '900': '#111827',
            '950': '#030712',
        },

        # Surface Colors
        'background': '#F9FAFB',
        'surface': '#FFFFFF',
        'surface_elevated': '#FFFFFF',

        # Text Colors
        'text_primary': '#111827',
        'text_secondary': '#6B7280',
        'text_disabled': '#9CA3AF',
        'text_inverse': '#FFFFFF',

        # Border Colors
        'border': '#E5E7EB',
        'border_strong': '#D1D5DB',
        'divider': '#F3F4F6',
    }

    # Dark Theme Colors
    DARK_THEME = {
        # Primary (adjusted for dark backgrounds)
        'primary': {
            '50': '#312E81',
            '100': '#3730A3',
            '200': '#4338CA',
            '300': '#4F46E5',
            '400': '#6366F1',
            '500': '#818CF8',  # Base primary (lighter in dark mode)
            '600': '#A5B4FC',
            '700': '#C7D2FE',
            '800': '#E0E7FF',
            '900': '#EEF2FF',
        },

        # Secondary
        'secondary': {
            '50': '#0F172A',
            '100': '#1E293B',
            '200': '#334155',
            '300': '#475569',
            '400': '#64748B',
            '500': '#94A3B8',  # Base
            '600': '#CBD5E1',
            '700': '#E2E8F0',
            '800': '#F1F5F9',
            '900': '#F8FAFC',
        },

        # Semantic Colors (adjusted for dark)
        'success': {
            '50': '#047857',
            '500': '#10B981',
            '600': '#34D399',
            '700': '#6EE7B7',
        },
        'warning': {
            '50': '#B45309',
            '500': '#F59E0B',
            '600': '#FBBF24',
            '700': '#FCD34D',
        },
        'danger': {
            '50': '#B91C1C',
            '500': '#EF4444',
            '600': '#F87171',
            '700': '#FCA5A5',
        },
        'info': {
            '50': '#1D4ED8',
            '500': '#3B82F6',
            '600': '#60A5FA',
            '700': '#93C5FD',
        },

        # Neutral Grays (inverted)
        'neutral': {
            '0': '#030712',
            '50': '#111827',
            '100': '#1F2937',
            '200': '#374151',
            '300': '#4B5563',
            '400': '#6B7280',
            '500': '#9CA3AF',
            '600': '#D1D5DB',
            '700': '#E5E7EB',
            '800': '#F3F4F6',
            '900': '#F9FAFB',
            '950': '#FFFFFF',
        },

        # Surface Colors
        'background': '#0F172A',
        'surface': '#1E293B',
        'surface_elevated': '#334155',

        # Text Colors
        'text_primary': '#F9FAFB',
        'text_secondary': '#94A3B8',
        'text_disabled': '#64748B',
        'text_inverse': '#0F172A',

        # Border Colors
        'border': '#334155',
        'border_strong': '#475569',
        'divider': '#1E293B',
    }

    # ==================== TYPOGRAPHY ====================

    TYPOGRAPHY = {
        # Font Families
        'font_primary': '-apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
        'font_mono': '"SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, "Courier New", monospace',

        # Font Sizes (8px base)
        'text_xs': '12px',
        'text_sm': '14px',
        'text_base': '16px',
        'text_lg': '18px',
        'text_xl': '20px',
        'text_2xl': '24px',
        'text_3xl': '30px',
        'text_4xl': '36px',
        'text_5xl': '48px',

        # Line Heights
        'leading_tight': '1.25',
        'leading_normal': '1.5',
        'leading_relaxed': '1.75',

        # Font Weights
        'weight_normal': '400',
        'weight_medium': '500',
        'weight_semibold': '600',
        'weight_bold': '700',

        # Letter Spacing
        'tracking_tight': '-0.025em',
        'tracking_normal': '0em',
        'tracking_wide': '0.025em',
    }

    # ==================== SPACING ====================

    SPACING = {
        '0': '0px',
        '1': '4px',    # 0.5 * 8px
        '2': '8px',    # 1 * 8px
        '3': '12px',   # 1.5 * 8px
        '4': '16px',   # 2 * 8px
        '5': '20px',   # 2.5 * 8px
        '6': '24px',   # 3 * 8px
        '8': '32px',   # 4 * 8px
        '10': '40px',  # 5 * 8px
        '12': '48px',  # 6 * 8px
        '16': '64px',  # 8 * 8px
        '20': '80px',  # 10 * 8px
        '24': '96px',  # 12 * 8px
    }

    # ==================== BORDER RADIUS ====================

    RADIUS = {
        'none': '0px',
        'sm': '4px',
        'base': '8px',
        'md': '12px',
        'lg': '16px',
        'xl': '20px',
        '2xl': '24px',
        'full': '9999px',
    }

    # ==================== SHADOWS ====================

    SHADOWS = {
        'light': {
            'xs': '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
            'sm': '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1)',
            'base': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1)',
            'md': '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)',
            'lg': '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
            'xl': '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
        },
        'dark': {
            'xs': '0 1px 2px 0 rgba(0, 0, 0, 0.3)',
            'sm': '0 1px 3px 0 rgba(0, 0, 0, 0.4), 0 1px 2px -1px rgba(0, 0, 0, 0.4)',
            'base': '0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -2px rgba(0, 0, 0, 0.4)',
            'md': '0 10px 15px -3px rgba(0, 0, 0, 0.4), 0 4px 6px -4px rgba(0, 0, 0, 0.4)',
            'lg': '0 20px 25px -5px rgba(0, 0, 0, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.4)',
            'xl': '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
        }
    }

    # ==================== TRANSITIONS ====================

    TRANSITIONS = {
        'fast': '150ms cubic-bezier(0.4, 0, 0.2, 1)',
        'base': '200ms cubic-bezier(0.4, 0, 0.2, 1)',
        'slow': '300ms cubic-bezier(0.4, 0, 0.2, 1)',
        'ease_out': 'cubic-bezier(0, 0, 0.2, 1)',
        'ease_in': 'cubic-bezier(0.4, 0, 1, 1)',
        'ease_in_out': 'cubic-bezier(0.4, 0, 0.2, 1)',
    }

    # ==================== BREAKPOINTS ====================

    BREAKPOINTS = {
        'xs': '0px',      # Mobile portrait
        'sm': '640px',    # Mobile landscape
        'md': '768px',    # Tablet
        'lg': '1024px',   # Desktop
        'xl': '1280px',   # Large desktop
        '2xl': '1536px',  # Extra large
    }

    # ==================== Z-INDEX ====================

    Z_INDEX = {
        'base': '0',
        'dropdown': '1000',
        'sticky': '1020',
        'fixed': '1030',
        'modal_backdrop': '1040',
        'modal': '1050',
        'popover': '1060',
        'tooltip': '1070',
    }


def get_theme(theme_name='light'):
    """Get theme configuration."""
    if theme_name == 'dark':
        return DesignTokens.DARK_THEME
    return DesignTokens.LIGHT_THEME


def generate_custom_css(theme='light'):
    """Generate custom CSS with design tokens."""

    tokens = DesignTokens()
    colors = get_theme(theme)
    shadows = tokens.SHADOWS['dark' if theme == 'dark' else 'light']

    css = f"""
    /* ==================== GLOBAL STYLES ==================== */

    :root {{
        /* Color tokens */
        --color-primary: {colors['primary']['500']};
        --color-primary-hover: {colors['primary']['600']};
        --color-primary-light: {colors['primary']['50']};

        --color-success: {colors['success']['500']};
        --color-warning: {colors['warning']['500']};
        --color-danger: {colors['danger']['500']};
        --color-info: {colors['info']['500']};

        --color-background: {colors['background']};
        --color-surface: {colors['surface']};
        --color-surface-elevated: {colors['surface_elevated']};

        --color-text-primary: {colors['text_primary']};
        --color-text-secondary: {colors['text_secondary']};
        --color-text-disabled: {colors['text_disabled']};

        --color-border: {colors['border']};
        --color-border-strong: {colors['border_strong']};
        --color-divider: {colors['divider']};

        /* Typography */
        --font-primary: {tokens.TYPOGRAPHY['font_primary']};
        --font-mono: {tokens.TYPOGRAPHY['font_mono']};

        /* Spacing */
        --spacing-1: {tokens.SPACING['1']};
        --spacing-2: {tokens.SPACING['2']};
        --spacing-3: {tokens.SPACING['3']};
        --spacing-4: {tokens.SPACING['4']};
        --spacing-6: {tokens.SPACING['6']};
        --spacing-8: {tokens.SPACING['8']};

        /* Radius */
        --radius-sm: {tokens.RADIUS['sm']};
        --radius-base: {tokens.RADIUS['base']};
        --radius-md: {tokens.RADIUS['md']};
        --radius-lg: {tokens.RADIUS['lg']};

        /* Shadows */
        --shadow-sm: {shadows['sm']};
        --shadow-base: {shadows['base']};
        --shadow-md: {shadows['md']};
        --shadow-lg: {shadows['lg']};

        /* Transitions */
        --transition-fast: {tokens.TRANSITIONS['fast']};
        --transition-base: {tokens.TRANSITIONS['base']};
        --transition-slow: {tokens.TRANSITIONS['slow']};
    }}

    /* Base styles */
    body {{
        font-family: var(--font-primary);
        background-color: var(--color-background);
        color: var(--color-text-primary);
        font-size: {tokens.TYPOGRAPHY['text_base']};
        line-height: {tokens.TYPOGRAPHY['leading_normal']};
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }}

    /* ==================== COMPONENT STYLES ==================== */

    /* Cards */
    .dashboard-card {{
        background: var(--color-surface);
        border-radius: var(--radius-md);
        border: 1px solid var(--color-border);
        box-shadow: var(--shadow-sm);
        transition: all var(--transition-base);
    }}

    .dashboard-card:hover {{
        box-shadow: var(--shadow-md);
        transform: translateY(-2px);
    }}

    .card-elevated {{
        background: var(--color-surface-elevated);
        box-shadow: var(--shadow-md);
    }}

    /* Buttons */
    .btn-primary {{
        background: var(--color-primary);
        color: white;
        border: none;
        border-radius: var(--radius-base);
        padding: var(--spacing-2) var(--spacing-4);
        font-weight: {tokens.TYPOGRAPHY['weight_medium']};
        transition: all var(--transition-fast);
        cursor: pointer;
        font-size: {tokens.TYPOGRAPHY['text_sm']};
    }}

    .btn-primary:hover {{
        background: var(--color-primary-hover);
        transform: translateY(-1px);
        box-shadow: var(--shadow-sm);
    }}

    .btn-primary:active {{
        transform: translateY(0);
    }}

    .btn-primary:focus {{
        outline: 2px solid var(--color-primary);
        outline-offset: 2px;
    }}

    .btn-secondary {{
        background: transparent;
        color: var(--color-text-primary);
        border: 1px solid var(--color-border-strong);
        border-radius: var(--radius-base);
        padding: var(--spacing-2) var(--spacing-4);
        font-weight: {tokens.TYPOGRAPHY['weight_medium']};
        transition: all var(--transition-fast);
        cursor: pointer;
    }}

    .btn-secondary:hover {{
        background: var(--color-surface-elevated);
        border-color: var(--color-primary);
    }}

    /* KPI Cards */
    .kpi-card {{
        background: var(--color-surface);
        border-radius: var(--radius-md);
        padding: var(--spacing-6);
        border: 1px solid var(--color-border);
        transition: all var(--transition-base);
        position: relative;
        overflow: hidden;
    }}

    .kpi-card:hover {{
        box-shadow: var(--shadow-md);
        border-color: var(--color-primary);
    }}

    .kpi-value {{
        font-size: {tokens.TYPOGRAPHY['text_3xl']};
        font-weight: {tokens.TYPOGRAPHY['weight_bold']};
        color: var(--color-text-primary);
        margin: var(--spacing-2) 0;
    }}

    .kpi-label {{
        font-size: {tokens.TYPOGRAPHY['text_sm']};
        color: var(--color-text-secondary);
        text-transform: uppercase;
        letter-spacing: var(--tracking-wide);
        font-weight: {tokens.TYPOGRAPHY['weight_medium']};
    }}

    .kpi-change {{
        font-size: {tokens.TYPOGRAPHY['text_sm']};
        font-weight: {tokens.TYPOGRAPHY['weight_semibold']};
        padding: var(--spacing-1) var(--spacing-2);
        border-radius: var(--radius-sm);
        display: inline-flex;
        align-items: center;
        gap: var(--spacing-1);
    }}

    .kpi-change.positive {{
        color: {colors['success']['700']};
        background: {colors['success']['50']};
    }}

    .kpi-change.negative {{
        color: {colors['danger']['700']};
        background: {colors['danger']['50']};
    }}

    /* Loading States */
    .skeleton {{
        background: linear-gradient(
            90deg,
            var(--color-border) 0%,
            var(--color-divider) 50%,
            var(--color-border) 100%
        );
        background-size: 200% 100%;
        animation: shimmer 1.5s infinite;
        border-radius: var(--radius-base);
    }}

    @keyframes shimmer {{
        0% {{ background-position: -200% 0; }}
        100% {{ background-position: 200% 0; }}
    }}

    /* Filters */
    .filter-bar {{
        background: var(--color-surface);
        border-radius: var(--radius-md);
        padding: var(--spacing-4);
        border: 1px solid var(--color-border);
        margin-bottom: var(--spacing-6);
    }}

    /* Charts */
    .chart-container {{
        background: var(--color-surface);
        border-radius: var(--radius-md);
        padding: var(--spacing-4);
        border: 1px solid var(--color-border);
    }}

    /* Alerts */
    .alert {{
        border-radius: var(--radius-base);
        padding: var(--spacing-4);
        margin-bottom: var(--spacing-4);
        border-left: 4px solid;
        display: flex;
        align-items: flex-start;
        gap: var(--spacing-3);
    }}

    .alert-success {{
        background: {colors['success']['50']};
        border-color: {colors['success']['500']};
        color: {colors['success']['700']};
    }}

    .alert-warning {{
        background: {colors['warning']['50']};
        border-color: {colors['warning']['500']};
        color: {colors['warning']['700']};
    }}

    .alert-danger {{
        background: {colors['danger']['50']};
        border-color: {colors['danger']['500']};
        color: {colors['danger']['700']};
    }}

    .alert-info {{
        background: {colors['info']['50']};
        border-color: {colors['info']['500']};
        color: {colors['info']['700']};
    }}

    /* Focus visible for accessibility */
    *:focus-visible {{
        outline: 2px solid var(--color-primary);
        outline-offset: 2px;
    }}

    /* Smooth scrolling */
    html {{
        scroll-behavior: smooth;
    }}

    /* Selection */
    ::selection {{
        background: var(--color-primary-light);
        color: var(--color-text-primary);
    }}

    /* Scrollbar (webkit) */
    ::-webkit-scrollbar {{
        width: 12px;
        height: 12px;
    }}

    ::-webkit-scrollbar-track {{
        background: var(--color-background);
    }}

    ::-webkit-scrollbar-thumb {{
        background: var(--color-border-strong);
        border-radius: var(--radius-lg);
    }}

    ::-webkit-scrollbar-thumb:hover {{
        background: var(--color-text-secondary);
    }}

    /* Responsive utilities */
    @media (max-width: 768px) {{
        .kpi-value {{
            font-size: {tokens.TYPOGRAPHY['text_2xl']};
        }}

        .dashboard-card {{
            margin-bottom: var(--spacing-4);
        }}
    }}
    """

    return css


# Component presets
COMPONENT_STYLES = {
    'button_primary': {
        'base': 'btn-primary',
        'hover': 'btn-primary:hover',
        'focus': 'btn-primary:focus',
        'active': 'btn-primary:active',
        'disabled': 'btn-primary:disabled',
    },
    'card': {
        'base': 'dashboard-card',
        'elevated': 'card-elevated',
    },
    'kpi_card': {
        'base': 'kpi-card',
        'value': 'kpi-value',
        'label': 'kpi-label',
        'change': 'kpi-change',
    }
}
