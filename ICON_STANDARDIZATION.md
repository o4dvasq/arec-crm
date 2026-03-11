# Icon Standardization — Overwatch Dashboard

## Overview

All icons across the Overwatch dashboard have been standardized to use **Lucide Icons**, a modern, lightweight SVG icon library. This replaces:
- Unicode/emoji characters (✎, ✕, ×, ▶, ◀, ▲, ▼, ⚙, 📧, ✓, etc.)
- Inline custom SVGs (edit, refresh icons)
- Inconsistent icon approaches across pages

## New Icon System

### Global Setup

**File**: `/app/static/icons.js`
- Global `ICONS` registry object with semantic names
- Automatic Lucide icon initialization
- MutationObserver for dynamically added icons

**Included in**: `_nav.html` (shared on every page)
- Lucide CDN: `https://unpkg.com/lucide@latest`
- Global icon registry script

### Usage

#### In HTML:
```html
<i data-lucide="pencil"></i>
<i data-lucide="trash-2"></i>
<i data-lucide="check"></i>
```

#### In JavaScript:
```javascript
// Generate icon HTML
const editIcon = ICONS.edit;  // → '<i data-lucide="pencil"></i>'

// After dynamic insertion, reinitialize icons
feather.replace();
```

## Icon Inventory

### Dashboard (`dashboard.html`)
| Usage | Old Format | New Format | Icon |
|-------|-----------|-----------|------|
| Calendar Refresh | SVG | `rotate-cw` | ↻ |
| Task Edit | SVG | `pencil` | ✏ |
| Loading State | SVG | `loader` | ⟳ |
| New Status | `○` | `circle` | ○ |
| In Progress | `→` | `arrow-right` | → |
| Complete | `✓` | `check` | ✔ |

### Tasks Board (`tasks/tasks.js`)
| Usage | Old Format | New Format | Icon |
|-------|-----------|-----------|------|
| Priority Groups | `▾` | `chevron-down` | ▼ |
| Complete Task | `✓` | `check` | ✔ |
| Restore Task | `↶` | `undo` | ↶ |
| Cycle Priority | `↕` | `arrow-up-down` | ⇅ |
| Email Nudge | `📧` | `mail` | ✉ |
| Edit Task | `✎` | `pencil` | ✏ |
| Delete Task | `×` | `trash-2` | 🗑 |
| Done Toggle | `▲`/`▼` | `chevron-up`/`chevron-down` | ▲/▼ |

### Edit Modal (`task-edit-modal.js`)
| Usage | Old Format | New Format | Icon |
|-------|-----------|-----------|------|
| Close | `&times;` | `x` | ✕ |
| Nudge | `📧` | `mail` | ✉ |

### Prospect Detail (`crm_prospect_detail.html`)
| Usage | Old Format | New Format | Icon |
|-------|-----------|-----------|------|
| At a Glance | `⚡` | `zap` | ⚡ |

## Global ICONS Registry

Available icons for future use:

```javascript
const ICONS = {
  edit, delete, close, refresh, spinner,
  chevronUp, chevronDown, chevronLeft, chevronRight,
  check, arrowRight, email, settings, menu,
  alert, info, search, link, externalLink,
  download, upload, copy, eye, eyeOff,
  plus, minus, redo, undo, zoomIn, zoomOut,
  clock, calendar, trash, user, users,
  send, bell, star, home, heart, flag, bookmark,
  folder, file, zap, package
}
```

## CSS Styling

### Global Icon Styles (`crm.css`)
```css
[data-lucide] {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  vertical-align: -0.125em;
}

[data-lucide] svg {
  width: 1em;
  height: 1em;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  fill: none;
}
```

### Custom Sizing
```html
<!-- Custom size (e.g., 14px) -->
<i data-lucide="pencil" style="width:14px;height:14px;"></i>

<!-- Color customization -->
<i data-lucide="check" style="color:#16a34a;"></i>

<!-- Animation -->
<i data-lucide="loader" style="animation:spin 1s linear infinite;"></i>
```

## Files Modified

1. **Created**:
   - `/app/static/icons.js` — Icon registry and initialization

2. **Templates**:
   - `/app/templates/_nav.html` — CDN + registry loading
   - `/app/templates/dashboard.html` — 6 icon replacements
   - `/app/templates/crm_prospect_detail.html` — 1 icon replacement

3. **JavaScript**:
   - `/app/static/tasks/tasks.js` — 8 icon replacements
   - `/app/static/task-edit-modal.js` — 2 icon replacements

4. **Styles**:
   - `/app/static/crm.css` — Global icon styling
   - `/app/static/tasks/tasks.css` — Task icon sizing + animations
   - `/app/static/task-edit-modal.css` — Modal icon styling

## Migration Notes

### Auto-Initialization
- Lucide icons are automatically initialized on page load
- MutationObserver watches for dynamically added icons
- Call `feather.replace()` after inserting new icons via JavaScript

### Browser Support
- Modern browsers with ES6 support
- Lucide CDN is served via unpkg (CDN fallback available)

### Performance
- Lucide CDN provides minified, cached SVG sprites
- No additional HTTP requests per icon
- Icons are CSS-sized (no sprite image needed)

## Future Enhancements

1. **Dark/Light Mode**: Icons inherit `currentColor`, so CSS variables can control icon colors
   ```css
   :root[data-theme="dark"] i { color: #e2e8f0; }
   :root[data-theme="light"] i { color: #1e293b; }
   ```

2. **Add New Icons**: Add to `ICONS` registry in `icons.js`
   ```javascript
   const ICONS = {
     // ... existing icons
     newIcon: '<i data-lucide="new-icon-name"></i>',
   };
   ```

3. **Icon Animation Library**: Create utilities for common animations
   ```javascript
   // icons.js could export animation helpers
   const animate = {
     spin: (el) => el.style.animation = 'spin 1s linear infinite',
     pulse: (el) => el.style.animation = 'pulse 2s ease-in-out infinite',
   };
   ```

## Testing Checklist

- [x] Dashboard: Refresh button (icon + rotation hover)
- [x] Dashboard: Edit button
- [x] Dashboard: Status dropdown (3 icons)
- [x] Tasks: Priority group headers (chevron, collapsible)
- [x] Tasks: Card actions (complete, restore, priority, nudge, edit, delete)
- [x] Tasks: Done footer toggle (chevron animation)
- [x] Modal: Close button
- [x] Modal: Nudge button
- [x] Prospect detail: At a glance icon

## Lucide Icon References

- **Lucide Docs**: https://lucide.dev
- **Icon Search**: https://lucide.dev/icons
- **CDN**: https://unpkg.com/lucide@latest
- **GitHub**: https://github.com/lucide-icons/lucide

## Rollback Plan

If issues arise:
1. Remove CDN and icons.js includes from `_nav.html`
2. Revert individual template/JS files to previous Git commit
3. Icons will automatically revert to original format
