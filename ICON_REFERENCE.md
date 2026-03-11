# Icon Reference — Lucide Icon Mappings

## Quick Reference Table

| Semantic Name | Lucide Icon | Old Format | Usage |
|---|---|---|---|
| edit | `pencil` | ✎ / SVG | Edit task/content |
| delete | `trash-2` | × | Delete task/item |
| close | `x` | &times; | Close modal/dialog |
| refresh | `rotate-cw` | ↻ / SVG | Refresh data |
| spinner | `loader` | ⟳ / SVG | Loading state |
| check | `check` | ✓ | Mark complete |
| undo | `undo` | ↶ | Restore/undo |
| arrowRight | `arrow-right` | → | In progress status |
| arrowUpDown | `arrow-up-down` | ↕ | Cycle priority |
| chevronUp | `chevron-up` | ▲ | Collapse/hide |
| chevronDown | `chevron-down` | ▾ | Expand/show |
| chevronLeft | `chevron-left` | ◀ | Navigate left |
| chevronRight | `chevron-right` | ▶ | Navigate right |
| email/mail | `mail` | 📧 | Send email |
| zap | `zap` | ⚡ | Highlight/important |
| circle | `circle` | ○ | New status |
| settings | `settings` | ⚙ | Settings/config |
| menu | `menu` | ☰ | Menu toggle |
| alert | `alert-circle` | ⚠ | Warning/alert |
| info | `info` | ℹ | Information |
| search | `search` | 🔍 | Search |
| link | `link` | 🔗 | Link/connect |
| externalLink | `external-link` | ↗ | Open external |
| download | `download` | ↓ | Download file |
| upload | `upload` | ↑ | Upload file |
| copy | `copy` | ⎘ | Copy to clipboard |
| eye | `eye` | 👁 | Show/visible |
| eyeOff | `eye-off` | 👁‍🗨 | Hide/invisible |
| plus | `plus` | + | Add/create |
| minus | `minus` | − | Subtract/remove |
| redo | `redo` | ↷ | Redo action |
| zoomIn | `zoom-in` | 🔍+ | Zoom in |
| zoomOut | `zoom-out` | 🔍− | Zoom out |
| clock | `clock` | ⏰ | Time/history |
| calendar | `calendar` | 📅 | Date/schedule |
| user | `user` | 👤 | Person/user |
| users | `users` | 👥 | Team/group |
| send | `send` | ▶ | Send/submit |
| bell | `bell` | 🔔 | Notifications |
| star | `star` | ⭐ | Favorite/rating |
| heart | `heart` | ❤ | Like/favorite |
| flag | `flag` | 🚩 | Flag/bookmark |
| bookmark | `bookmark` | 🔖 | Bookmark |
| folder | `folder` | 📁 | Folder/directory |
| file | `file` | 📄 | File/document |
| package | `package` | 📦 | Package/bundle |

## Icon Usage by Location

### Dashboard Page (`dashboard.html`)

#### Calendar Refresh Button
```html
<!-- Old -->
<svg width="14" height="14" viewBox="0 0 24 24" ...>
  <polyline points="23 4 23 10 17 10"></polyline>
  <!-- ... -->
</svg>

<!-- New -->
<i data-lucide="rotate-cw" style="width:14px;height:14px;"></i>
```

#### Task Edit Button
```html
<!-- Old -->
<svg width="14" height="14" viewBox="0 0 24 24" ...>
  <path d="M11 4H4a2 2 0 0 0-2 2v14..."/>
  <!-- ... -->
</svg>

<!-- New -->
<i data-lucide="pencil" style="width:14px;height:14px;"></i>
```

#### Loading Spinner (Animated)
```html
<!-- New -->
<i data-lucide="loader" style="width:14px;height:14px;animation:spin 1s linear infinite;"></i>
```

#### Status Dropdown
```html
<!-- Old -->
<span style="opacity:0.5;">○</span> New
<span style="color:#1d4ed8;">→</span> In Progress
<span style="color:#16a34a;">✓</span> Complete

<!-- New -->
<i data-lucide="circle" style="opacity:0.5;"></i> New
<i data-lucide="arrow-right" style="color:#1d4ed8;"></i> In Progress
<i data-lucide="check" style="color:#16a34a;"></i> Complete
```

### Tasks Board (`tasks/tasks.js`)

#### Priority Group Headers
```html
<!-- Old -->
<span class="chevron">▾</span>

<!-- New -->
<i data-lucide="chevron-down" style="width:14px;height:14px;" class="chevron"></i>
```

#### Task Card Actions
```html
<!-- Complete Button -->
<!-- Old -->
<button class="task-action-btn complete">✓</button>
<!-- New -->
<button class="task-action-btn complete"><i data-lucide="check"></i></button>

<!-- Restore Button -->
<!-- Old -->
<button class="task-action-btn">↶</button>
<!-- New -->
<button class="task-action-btn"><i data-lucide="undo"></i></button>

<!-- Priority Cycle -->
<!-- Old -->
<button class="task-action-btn">↕</button>
<!-- New -->
<button class="task-action-btn"><i data-lucide="arrow-up-down"></i></button>

<!-- Email Nudge -->
<!-- Old -->
<button class="task-action-btn">📧</button>
<!-- New -->
<button class="task-action-btn"><i data-lucide="mail"></i></button>

<!-- Edit -->
<!-- Old -->
<button class="task-action-btn">✎</button>
<!-- New -->
<button class="task-action-btn"><i data-lucide="pencil"></i></button>

<!-- Delete -->
<!-- Old -->
<button class="task-action-btn delete">×</button>
<!-- New -->
<button class="task-action-btn delete"><i data-lucide="trash-2"></i></button>
```

#### Done Footer Toggle
```html
<!-- Old -->
<span>Done (5)</span><span>&#9660;</span>

<!-- New -->
<span>Done (5)</span><i data-lucide="chevron-down"></i>

<!-- Expanded state -->
<i data-lucide="chevron-up"></i>
```

### Edit Modal (`task-edit-modal.js`)

#### Close Button
```html
<!-- Old -->
<button class="task-modal-close">&times;</button>

<!-- New -->
<button class="task-modal-close"><i data-lucide="x" style="width:18px;height:18px;"></i></button>
```

#### Send Nudge Button
```html
<!-- Old -->
<button>📧 Send Nudge</button>

<!-- New -->
<button><i data-lucide="mail" style="width:14px;height:14px;"></i> Send Nudge</button>
```

### Prospect Detail (`crm_prospect_detail.html`)

#### At a Glance Icon
```html
<!-- Old -->
<span class="glance-icon">⚡</span>

<!-- New -->
<i data-lucide="zap" class="glance-icon"></i>
```

## CSS Styling Rules

### Global Icon Styling (`crm.css`)
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

### Button Icon Sizing (`tasks.css`)
```css
.task-action-btn svg {
  width: 16px;
  height: 16px;
  stroke: currentColor;
  stroke-width: 2;
}
```

### Chevron Animations (`tasks.css`)
```css
.priority-group-header .chevron {
  transition: transform 0.2s ease;
  width: 14px;
  height: 14px;
}

.priority-group-header.collapsed .chevron {
  transform: rotate(-90deg);
}

.done-toggle i {
  transition: transform 0.2s ease;
}

.done-toggle.open i {
  transform: rotate(-180deg);
}
```

### Modal Close Button (`task-edit-modal.css`)
```css
.task-modal-close {
  display: flex;
  align-items: center;
  justify-content: center;
}

.task-modal-close svg {
  stroke: currentColor;
}
```

## JavaScript Usage

### HTML Generation with Icons
```javascript
// In tasks.js - Creating task card actions
const card = document.createElement('div');
card.innerHTML = `
  <div class="task-actions">
    <button class="task-action-btn complete" title="Complete">
      <i data-lucide="check"></i>
    </button>
    <button class="task-action-btn" title="Edit">
      <i data-lucide="pencil"></i>
    </button>
  </div>
`;
feather.replace(); // Initialize icons
```

### Using the ICONS Registry
```javascript
// In icons.js
const ICONS = {
  edit: '<i data-lucide="pencil"></i>',
  delete: '<i data-lucide="trash-2"></i>',
  check: '<i data-lucide="check"></i>',
  // ... etc
};

// Usage
myElement.innerHTML = ICONS.edit;
feather.replace(); // Required after dynamic insertion
```

### Dynamic Icon Updates
```javascript
// Change icon dynamically
const icon = document.querySelector('i[data-lucide="chevron-down"]');
icon.dataset.lucide = 'chevron-up';
feather.replace(); // Re-render
```

## Color Customization

### Using CSS Custom Properties
```css
:root {
  --icon-primary: #e2e8f0;
  --icon-success: #16a34a;
  --icon-danger: #dc2626;
  --icon-warning: #f59e0b;
}

i.success { color: var(--icon-success); }
i.danger { color: var(--icon-danger); }
i.warning { color: var(--icon-warning); }
```

### Inline Styling
```html
<!-- Red icon -->
<i data-lucide="alert-circle" style="color:#dc2626;"></i>

<!-- Green icon -->
<i data-lucide="check" style="color:#16a34a;"></i>

<!-- Custom size -->
<i data-lucide="zap" style="width:20px;height:20px;"></i>
```

## Animation Examples

### Spin/Loading
```css
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Usage */
<i data-lucide="loader" style="animation: spin 1s linear infinite;"></i>
```

### Pulse
```css
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

<i data-lucide="bell" style="animation: pulse 2s ease-in-out infinite;"></i>
```

### Bounce
```css
@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}

<i data-lucide="arrow-up" style="animation: bounce 1s infinite;"></i>
```

## Migration Checklist

When adding new icons to your code:

- [ ] Use Lucide icon name with `data-lucide="icon-name"`
- [ ] Call `feather.replace()` after dynamic HTML insertion
- [ ] Use CSS for sizing (prefer em/rem over px)
- [ ] Use `currentColor` for color inheritance
- [ ] Test on mobile (responsive sizing)
- [ ] Add icon to ICONS registry if it's commonly used
- [ ] Document in this reference file

## Resources

- **Icon Library**: https://lucide.dev
- **Icon Search**: https://lucide.dev/icons
- **CDN**: https://unpkg.com/lucide@latest
- **Documentation**: https://github.com/lucide-icons/lucide
