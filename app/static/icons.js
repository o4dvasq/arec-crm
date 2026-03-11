/**
 * icons.js — Global icon registry for Overwatch
 * Uses Lucide Icons (loaded via CDN in _nav.html)
 *
 * Usage:
 *   - In HTML: <i data-lucide="pencil"></i>
 *   - In JS: ICONS.edit  →  '<i data-lucide="pencil"></i>'
 *   - After dynamic insertion: feather.replace()
 */

const ICONS = {
  edit: '<i data-lucide="pencil"></i>',
  delete: '<i data-lucide="trash-2"></i>',
  close: '<i data-lucide="x"></i>',
  refresh: '<i data-lucide="rotate-cw"></i>',
  spinner: '<i data-lucide="loader"></i>',
  chevronUp: '<i data-lucide="chevron-up"></i>',
  chevronDown: '<i data-lucide="chevron-down"></i>',
  chevronLeft: '<i data-lucide="chevron-left"></i>',
  chevronRight: '<i data-lucide="chevron-right"></i>',
  check: '<i data-lucide="check"></i>',
  arrowRight: '<i data-lucide="arrow-right"></i>',
  email: '<i data-lucide="mail"></i>',
  settings: '<i data-lucide="settings"></i>',
  menu: '<i data-lucide="menu"></i>',
  alert: '<i data-lucide="alert-circle"></i>',
  info: '<i data-lucide="info"></i>',
  search: '<i data-lucide="search"></i>',
  link: '<i data-lucide="link"></i>',
  externalLink: '<i data-lucide="external-link"></i>',
  download: '<i data-lucide="download"></i>',
  upload: '<i data-lucide="upload"></i>',
  copy: '<i data-lucide="copy"></i>',
  eye: '<i data-lucide="eye"></i>',
  eyeOff: '<i data-lucide="eye-off"></i>',
  plus: '<i data-lucide="plus"></i>',
  minus: '<i data-lucide="minus"></i>',
  redo: '<i data-lucide="redo"></i>',
  undo: '<i data-lucide="undo"></i>',
  zoomIn: '<i data-lucide="zoom-in"></i>',
  zoomOut: '<i data-lucide="zoom-out"></i>',
  clock: '<i data-lucide="clock"></i>',
  calendar: '<i data-lucide="calendar"></i>',
  trash: '<i data-lucide="trash-2"></i>',
  user: '<i data-lucide="user"></i>',
  users: '<i data-lucide="users"></i>',
  send: '<i data-lucide="send"></i>',
  bell: '<i data-lucide="bell"></i>',
  star: '<i data-lucide="star"></i>',
  home: '<i data-lucide="home"></i>',
  heart: '<i data-lucide="heart"></i>',
  flag: '<i data-lucide="flag"></i>',
  bookmark: '<i data-lucide="bookmark"></i>',
  folder: '<i data-lucide="folder"></i>',
  file: '<i data-lucide="file"></i>',
  zap: '<i data-lucide="zap"></i>',
  package: '<i data-lucide="package"></i>',
};

// Auto-initialize Lucide icons after DOM mutations
if (typeof feather !== 'undefined') {
  // On page load
  document.addEventListener('DOMContentLoaded', () => {
    feather.replace();
  });

  // Watch for dynamically added icons
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.addedNodes.length) {
        feather.replace();
      }
    });
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });
}
