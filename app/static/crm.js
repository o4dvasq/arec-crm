/* ═══════════════════════════════════════════════════════════
   Person Name Linking — app-wide
   Finds [data-person-name] elements and wraps them in links
   using window.SEARCH_INDEX (injected by _nav.html).
   Safe to call multiple times; already-linked elements are
   skipped because they no longer carry data-person-name.
   ═══════════════════════════════════════════════════════════ */

// Built once per page load — SEARCH_INDEX never changes at runtime.
let _personNameIndex = null;

function _getPersonNameIndex() {
    if (_personNameIndex !== null) return _personNameIndex;
    _personNameIndex = (window.SEARCH_INDEX || [])
        .filter(function (e) { return e.type === 'person'; })
        .reduce(function (map, e) {
            map[e.name.toLowerCase()] = e.url;
            return map;
        }, {});
    return _personNameIndex;
}

function linkifyPersonNames() {
    const index = _getPersonNameIndex();
    document.querySelectorAll('[data-person-name]').forEach(function (el) {
        const name = el.textContent.trim();
        const url = index[name.toLowerCase()];
        if (url && !el.closest('a')) {
            const link = document.createElement('a');
            link.href = url;
            link.className = 'person-link';
            link.textContent = name;
            link.addEventListener('click', function (e) { e.stopPropagation(); });
            el.replaceWith(link);
        }
    });
}

document.addEventListener('DOMContentLoaded', linkifyPersonNames);

/* ═══════════════════════════════════════════════════════════
   Utility — Markdown stripping
   Removes bold/italic markdown wrappers from display text.
   ═══════════════════════════════════════════════════════════ */

function stripMarkdown(text) {
    if (!text) return '';
    return text
        .replace(/\*\*(.+?)\*\*/g, '$1')
        .replace(/\*(.+?)\*/g, '$1')
        .replace(/__(.+?)__/g, '$1')
        .replace(/_(.+?)_/g, '$1');
}

/* ═══════════════════════════════════════════════════════════
   Utility — Markdown to HTML conversion
   Converts markdown bold, italic, and links to HTML.
   ═══════════════════════════════════════════════════════════ */

function markdownToHtml(text) {
    if (!text) return '';
    return text
        // Convert **bold** to <strong>bold</strong>
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        // Convert __bold__ to <strong>bold</strong>
        .replace(/__(.+?)__/g, '<strong>$1</strong>')
        // Convert _italic_ to <em>italic</em> (after __, to avoid double-replacing)
        .replace(/_(.+?)_/g, '<em>$1</em>')
        // Convert *italic* to <em>italic</em>
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // Convert [text](url) to <a href="url" target="_blank">text</a>
        .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank">$1</a>');
}

/* ═══════════════════════════════════════════════════════════
   Overwatch — Global Search Autocomplete
   Reads window.SEARCH_INDEX injected by _nav.html
   ═══════════════════════════════════════════════════════════ */

(function () {
    const TYPE_PRIORITY = { prospect: 0, person: 1, org: 2 };

    function filterResults(query) {
        const q = query.toLowerCase();
        const prefix = [];
        const substring = [];

        for (const entry of window.SEARCH_INDEX) {
            const name = entry.name.toLowerCase();
            if (name.startsWith(q)) {
                prefix.push(entry);
            } else if (name.includes(q)) {
                substring.push(entry);
            }
        }

        function sortEntries(arr) {
            arr.sort(function (a, b) {
                const tp = TYPE_PRIORITY[a.type] - TYPE_PRIORITY[b.type];
                if (tp !== 0) return tp;
                return a.name.localeCompare(b.name);
            });
        }

        sortEntries(prefix);
        sortEntries(substring);
        return prefix.concat(substring).slice(0, 10);
    }

    function renderDropdown(dropdown, results) {
        dropdown.innerHTML = '';

        if (results.length === 0) {
            const row = document.createElement('div');
            row.className = 'search-no-results';
            row.textContent = 'No results found';
            dropdown.appendChild(row);
        } else {
            for (const entry of results) {
                const row = document.createElement('div');
                row.className = 'search-result-row';

                const primary = document.createElement('span');
                primary.className = 'search-result-primary';
                primary.textContent = entry.name;
                row.appendChild(primary);

                if (entry.secondary) {
                    const secondary = document.createElement('span');
                    secondary.className = 'search-result-secondary';
                    secondary.textContent = entry.secondary;
                    row.appendChild(secondary);
                }

                if (entry.typeLabel) {
                    const typeLabel = document.createElement('span');
                    typeLabel.className = 'search-result-type';
                    typeLabel.textContent = entry.typeLabel;
                    row.appendChild(typeLabel);
                }

                row.addEventListener('click', function () {
                    window.location.href = entry.url;
                });

                dropdown.appendChild(row);
            }
        }

        dropdown.style.display = 'block';
    }

    function closeDropdown(input, dropdown) {
        dropdown.style.display = 'none';
        dropdown.innerHTML = '';
    }

    document.addEventListener('DOMContentLoaded', function () {
        if (!window.SEARCH_INDEX) return;

        const container = document.getElementById('global-search');
        const input = document.getElementById('global-search-input');
        const dropdown = document.getElementById('global-search-dropdown');

        if (!container || !input || !dropdown) return;

        let highlighted = -1;

        input.addEventListener('input', function () {
            highlighted = -1;
            const q = this.value.trim();
            if (q.length < 2) {
                closeDropdown(input, dropdown);
                return;
            }
            renderDropdown(dropdown, filterResults(q));
        });

        input.addEventListener('keydown', function (e) {
            const rows = dropdown.querySelectorAll('.search-result-row');

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                highlighted = Math.min(highlighted + 1, rows.length - 1);
                rows.forEach(function (r, i) {
                    r.classList.toggle('search-result-row--highlighted', i === highlighted);
                });
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                highlighted = Math.max(highlighted - 1, 0);
                rows.forEach(function (r, i) {
                    r.classList.toggle('search-result-row--highlighted', i === highlighted);
                });
            } else if (e.key === 'Enter') {
                if (highlighted >= 0 && rows[highlighted]) {
                    rows[highlighted].click();
                    highlighted = -1;
                }
            } else if (e.key === 'Escape') {
                input.value = '';
                highlighted = -1;
                closeDropdown(input, dropdown);
                input.blur();
            }
        });

        document.addEventListener('click', function (e) {
            if (!container.contains(e.target)) {
                closeDropdown(input, dropdown);
            }
        });
    });
}());
