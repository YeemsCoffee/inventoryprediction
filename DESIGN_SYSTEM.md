# Modern Design System

## Overview

A comprehensive design system built on industry-standard principles from Apple HIG, Google Material Design 3, and Nielsen Norman Group guidelines. Ensures consistency, accessibility, and professional appearance across the entire dashboard.

## Design Principles

### 1. **Clear Visual Hierarchy**
- Use size, weight, and color to establish importance
- Primary content: large, bold, high contrast
- Secondary content: smaller, medium weight, lower contrast
- Tertiary content: smallest, regular weight, muted

### 2. **8px Grid System**
- All spacing is a multiple of 8px
- Ensures perfect alignment across all screen sizes
- Creates visual rhythm and consistency
- Easier to scale responsively

### 3. **Limited Color Palette**
- Primary: Brand identity (Indigo #6366F1)
- Secondary: Supporting content (Slate)
- Semantic: Success, Warning, Danger, Info
- Neutral: Grays for text and surfaces

### 4. **Accessibility First**
- WCAG 2.1 AA compliant (minimum 4.5:1 contrast)
- Keyboard navigable
- Screen reader friendly
- Color-blind safe (don't rely on color alone)

### 5. **Progressive Disclosure**
- Show only what's needed
- Hide complexity until required
- Use expandable sections
- Minimize cognitive load

## Design Tokens

### Color System

#### Light Theme

**Primary Colors:**
```
primary-50:  #EEF2FF (lightest)
primary-100: #E0E7FF
primary-200: #C7D2FE
primary-300: #A5B4FC
primary-400: #818CF8
primary-500: #6366F1 (base)
primary-600: #4F46E5 (hover)
primary-700: #4338CA
primary-800: #3730A3
primary-900: #312E81 (darkest)
```

**Semantic Colors:**
```
success-500: #10B981 (green)
warning-500: #F59E0B (amber)
danger-500:  #EF4444 (red)
info-500:    #3B82F6 (blue)
```

**Neutral Colors:**
```
neutral-0:   #FFFFFF (white)
neutral-50:  #F9FAFB
neutral-100: #F3F4F6
neutral-200: #E5E7EB
neutral-300: #D1D5DB
neutral-400: #9CA3AF
neutral-500: #6B7280
neutral-600: #4B5563
neutral-700: #374151
neutral-800: #1F2937
neutral-900: #111827
neutral-950: #030712 (black)
```

**Surface Colors:**
```
background:        #F9FAFB
surface:           #FFFFFF
surface-elevated:  #FFFFFF
```

**Text Colors:**
```
text-primary:   #111827 (high contrast)
text-secondary: #6B7280 (medium contrast)
text-disabled:  #9CA3AF (low contrast)
text-inverse:   #FFFFFF (on dark backgrounds)
```

**Border Colors:**
```
border:        #E5E7EB
border-strong: #D1D5DB
divider:       #F3F4F6
```

#### Dark Theme

Colors are inverted for dark backgrounds:
- Primary colors are lighter/brighter
- Text is light on dark backgrounds
- Surfaces use dark grays
- Borders are more subtle

### Typography

**Font Families:**
```
Primary: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, Arial, sans-serif
Monospace: "SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, monospace
```

**Font Sizes** (8px based):
```
text-xs:   12px
text-sm:   14px
text-base: 16px (default)
text-lg:   18px
text-xl:   20px
text-2xl:  24px
text-3xl:  30px
text-4xl:  36px
text-5xl:  48px
```

**Line Heights:**
```
leading-tight:   1.25 (headings)
leading-normal:  1.5  (body text)
leading-relaxed: 1.75 (long-form content)
```

**Font Weights:**
```
weight-normal:    400 (body text)
weight-medium:    500 (emphasis)
weight-semibold:  600 (subheadings)
weight-bold:      700 (headings)
```

**Letter Spacing:**
```
tracking-tight:  -0.025em (large headings)
tracking-normal: 0em      (default)
tracking-wide:   0.025em  (labels, buttons)
```

### Spacing

Based on 8px grid:

```
0:  0px
1:  4px   (0.5 × 8)
2:  8px   (1 × 8)
3:  12px  (1.5 × 8)
4:  16px  (2 × 8)
5:  20px  (2.5 × 8)
6:  24px  (3 × 8)
8:  32px  (4 × 8)
10: 40px  (5 × 8)
12: 48px  (6 × 8)
16: 64px  (8 × 8)
20: 80px  (10 × 8)
24: 96px  (12 × 8)
```

**Usage Guide:**
- **spacing-1 (4px)**: Icon margins, tight spacing
- **spacing-2 (8px)**: Button padding, small gaps
- **spacing-3 (12px)**: Form field spacing
- **spacing-4 (16px)**: Card padding, medium gaps
- **spacing-6 (24px)**: Section spacing
- **spacing-8 (32px)**: Component spacing
- **spacing-12 (48px)**: Large section breaks

### Border Radius

```
none: 0px
sm:   4px   (small elements)
base: 8px   (buttons, inputs)
md:   12px  (cards)
lg:   16px  (large cards)
xl:   20px  (hero elements)
2xl:  24px  (extra large)
full: 9999px (circles, pills)
```

### Shadows

**Light Theme:**
```
xs:   0 1px 2px 0 rgba(0,0,0,0.05)
sm:   0 1px 3px 0 rgba(0,0,0,0.1)
base: 0 4px 6px -1px rgba(0,0,0,0.1)
md:   0 10px 15px -3px rgba(0,0,0,0.1)
lg:   0 20px 25px -5px rgba(0,0,0,0.1)
xl:   0 25px 50px -12px rgba(0,0,0,0.25)
```

**Dark Theme:**
Stronger shadows for better depth perception on dark backgrounds.

**Usage Guide:**
- **xs**: Subtle elevation (dropdowns)
- **sm**: Cards at rest
- **base**: Cards on hover
- **md**: Modals, popovers
- **lg**: Dialogs
- **xl**: Full-screen overlays

### Transitions

```
fast: 150ms cubic-bezier(0.4, 0, 0.2, 1)
base: 200ms cubic-bezier(0.4, 0, 0.2, 1)
slow: 300ms cubic-bezier(0.4, 0, 0.2, 1)
```

**Usage Guide:**
- **fast (150ms)**: Hover states, focus rings
- **base (200ms)**: Color changes, opacity
- **slow (300ms)**: Transform, layout changes

**Never exceed 300ms** - keeps interactions feeling snappy.

### Breakpoints

Mobile-first approach:

```
xs:  0px     (mobile portrait)
sm:  640px   (mobile landscape)
md:  768px   (tablet)
lg:  1024px  (desktop)
xl:  1280px  (large desktop)
2xl: 1536px  (extra large)
```

### Z-Index Scale

Consistent layering:

```
base:           0
dropdown:       1000
sticky:         1020
fixed:          1030
modal-backdrop: 1040
modal:          1050
popover:        1060
tooltip:        1070
```

## Component Library

### Buttons

**Primary Button:**
- Background: primary-500
- Hover: primary-600 + translateY(-1px) + shadow
- Active: translateY(0)
- Focus: 2px outline at primary-500
- Disabled: opacity 0.5 + no hover

**Secondary Button:**
- Background: transparent
- Border: 1px solid border-strong
- Hover: background surface-elevated + border primary

**Sizing:**
```
sm:   padding 8px 16px, font 14px
base: padding 12px 24px, font 16px
lg:   padding 16px 32px, font 18px
```

### Cards

**Base Card:**
- Background: surface
- Border: 1px solid border
- Border radius: 12px (md)
- Shadow: sm
- Hover: shadow md + translateY(-2px)
- Transition: 200ms

**Elevated Card:**
- Background: surface-elevated
- Shadow: md (always)

**KPI Card:**
- Padding: 24px (spacing-6)
- Icon: 24px, colored
- Value: 30px bold
- Label: 14px uppercase, medium weight
- Change indicator: inline pill with color

### Alerts

**Structure:**
- Border-left: 4px solid (semantic color)
- Padding: 16px
- Background: semantic-50
- Icon: semantic-500
- Text: semantic-700

**Types:**
- Success: green
- Warning: amber
- Danger: red
- Info: blue

### Forms

**Input Fields:**
- Height: 40px
- Padding: 8px 12px
- Border: 1px solid border
- Border radius: 8px (base)
- Focus: 2px outline primary-500
- Error: border danger-500

**Labels:**
- Font: 14px semibold
- Color: text-primary
- Margin-bottom: 8px
- Position: above field (not placeholder)

**Validation:**
- Inline (as user types)
- Success indicator: green checkmark
- Error message: red text below field

## Accessibility Guidelines

### Color Contrast

Minimum ratios (WCAG 2.1 AA):
- **Normal text**: 4.5:1
- **Large text** (18px+): 3:1
- **UI components**: 3:1

**Testing:**
Use browser DevTools or online contrast checkers.

### Keyboard Navigation

**Required:**
- All interactive elements reachable via Tab
- Logical tab order (left-to-right, top-to-bottom)
- Escape closes modals/dropdowns
- Enter activates buttons/links
- Arrow keys for menus

**Focus Indicators:**
- Visible on all interactive elements
- 2px solid outline
- Color: primary-500
- Offset: 2px

### Screen Readers

**Best Practices:**
- Semantic HTML (header, nav, main, footer)
- ARIA labels where needed
- Alt text for images
- Label for form fields
- Role attributes for custom widgets

### Touch Targets

**Minimum size:** 44×44px (Apple) / 48×48px (Google)

Ensures easy tapping on mobile devices.

## Usage Examples

### Implementing a KPI Card

```python
html.Div([
    html.I(className="fas fa-dollar-sign", style={
        'fontSize': tokens.TYPOGRAPHY['text_2xl'],
        'color': colors['success']['500'],
        'marginBottom': tokens.SPACING['3']
    }),
    html.Div("$45,231", className='kpi-value'),
    html.Div("Revenue", className='kpi-label'),
    html.Span([
        html.I(className="fas fa-arrow-up"),
        "12.5%"
    ], className='kpi-change positive')
], className='kpi-card')
```

### Creating a Button

```python
dbc.Button([
    html.I(className="fas fa-download", style={
        'marginRight': tokens.SPACING['2']
    }),
    "Export Data"
], className='btn-primary', id="export-btn")
```

### Spacing Components

```python
# Section spacing
html.Div([
    html.H2("Section Title"),
    html.P("Content...")
], style={
    'marginBottom': tokens.SPACING['8']  # 32px
})

# Card padding
html.Div([...], style={
    'padding': tokens.SPACING['6']  # 24px
})
```

### Responsive Layout

```python
dbc.Row([
    dbc.Col([...], lg=6, md=12, xs=12),  # Half on desktop, full on mobile
    dbc.Col([...], lg=6, md=12, xs=12)
])
```

## Theme Switching

The dashboard supports light and dark themes. When theme changes:

1. Update `theme-store` data
2. Regenerate CSS with `generate_custom_css(theme)`
3. Update chart colors to match theme
4. Automatic re-render with new styles

**Implementation:**
```python
@app.callback(
    Output('theme-store', 'data'),
    Input('theme-toggle', 'n_clicks'),
    State('theme-store', 'data')
)
def toggle_theme(n_clicks, current_theme):
    new_theme = 'dark' if current_theme == 'light' else 'light'
    return new_theme
```

## Best Practices

### Do's ✅

- Use design tokens (never hard-code colors/spacing)
- Follow 8px grid for all measurements
- Provide focus states for all interactive elements
- Use semantic HTML elements
- Test with keyboard navigation
- Check color contrast ratios
- Use loading states for async operations
- Provide helpful error messages
- Keep animations under 300ms
- Design mobile-first

### Don'ts ❌

- Don't hard-code colors or spacing values
- Don't use color alone to convey information
- Don't forget focus indicators
- Don't make tap targets smaller than 44px
- Don't use animations longer than 300ms
- Don't rely on hover for mobile
- Don't use ALL CAPS for long text
- Don't use low contrast text
- Don't forget empty states
- Don't skip error handling

## Tools & Resources

### Design Tools
- **Figma**: Design mockups
- **Contrast Checker**: WebAIM Contrast Checker
- **Accessibility**: WAVE browser extension

### Code Tools
- **Browser DevTools**: Inspect accessibility tree
- **Lighthouse**: Audit accessibility scores
- **axe DevTools**: Automated accessibility testing

### Reference
- [Apple HIG](https://developer.apple.com/design/human-interface-guidelines/)
- [Material Design 3](https://m3.material.io/)
- [WCAG 2.1](https://www.w3.org/WAI/WCAG21/quickref/)
- [Nielsen Norman Group](https://www.nngroup.com/)

---

**Version:** 1.0.0
**Last Updated:** 2025-11-09
**Maintained by:** Business Intelligence Team
