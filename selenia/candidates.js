// Collects every visible element worth targeting, including inside open shadow roots.
// Each element gets a data-selenia-id attribute so it can be found again after scoring.
// Run with: driver.execute_script(open("candidates.js").read())
// Returns a list of plain objects; features.py turns each into the text the model reads.
return (function () {
  const INTERACTIVE =
    'a,button,input,select,textarea,summary,label,img[alt],' +
    '[role],[onclick],[tabindex]:not([tabindex="-1"]),[contenteditable="true"],[data-testid],' +
    'h1,h2,h3,h4,h5,h6';
  const LANDMARKS = 'form,nav,header,footer,aside,main,dialog,section,[role=dialog],[role=navigation],[role=search],[role=banner]';
  const CLICKABLE_PARENT = 'a,button,[role=button],[role=link],[role=menuitem],[role=tab],label,summary';

  const clean = (s, n) => (s || '').replace(/\s+/g, ' ').trim().slice(0, n || 100);
  const pageW = Math.max(document.documentElement.scrollWidth, window.innerWidth) || 1;
  const pageH = Math.max(document.documentElement.scrollHeight, window.innerHeight) || 1;

  function visible(el) {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return null;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || Number(cs.opacity) === 0) return null;
    return r;
  }

  function byIds(root, ids) {
    return (ids || '').split(/\s+/).filter(Boolean)
      .map(id => { const t = root.getElementById ? root.getElementById(id) : document.getElementById(id); return t ? t.innerText || t.textContent : ''; })
      .join(' ');
  }

  function labelOf(el, root) {
    let parts = [];
    if (el.labels && el.labels.length) parts = Array.from(el.labels).map(l => l.innerText || l.textContent);
    const lb = el.getAttribute('aria-labelledby');
    if (lb) parts.push(byIds(root, lb));
    return clean(parts.join(' '), 80);
  }

  function contextOf(el) {
    // Nearest landmark (form, nav, dialog...) and its name, crossing shadow boundaries.
    let node = el.parentElement || (el.getRootNode() && el.getRootNode().host);
    while (node) {
      if (node.matches && node.matches(LANDMARKS)) {
        const kind = (node.getAttribute('role') || node.tagName).toLowerCase();
        let name = node.getAttribute('aria-label') || node.getAttribute('title') || '';
        if (!name) {
          const h = node.querySelector('legend,h1,h2,h3,h4,[role=heading]');
          if (h) name = h.innerText || h.textContent;
        }
        return clean(kind + (name ? ' ' + name : ''), 60);
      }
      node = node.parentElement || (node.getRootNode && node.getRootNode().host);
    }
    return '';
  }

  function nearOf(el, own) {
    // Heading of the card/row the element sits in, e.g. the product name next to "Add to cart".
    let node = el.parentElement, depth = 0;
    while (node && depth < 4 && !(node.matches && node.matches(LANDMARKS))) {
      if (node.tagName === 'TR') {
        const cell = node.querySelector('th,td');
        const t = cell && !cell.contains(el) ? clean(cell.innerText || cell.textContent, 60) : '';
        if (t && t !== own) return t;
      }
      const h = node.querySelector('h1,h2,h3,h4,h5,h6,[role=heading],legend,strong');
      if (h && h !== el && !el.contains(h) && !h.contains(el)) {
        const t = clean(h.innerText || h.textContent, 60);
        if (t && t !== own) return t;
      }
      node = node.parentElement;
      depth++;
    }
    return '';
  }

  function ownText(el) {
    if (el.tagName === 'INPUT' && ['submit', 'button', 'reset'].includes(el.type)) return el.value;
    if (el.tagName === 'SELECT') { const o = el.options[el.selectedIndex]; return o ? o.text : ''; }
    if (['INPUT', 'TEXTAREA'].includes(el.tagName)) return '';
    return el.innerText || el.textContent;
  }

  function shortHref(el) {
    const h = el.getAttribute('href');
    if (!h || h.startsWith('javascript:') || h === '#') return '';
    try { const u = new URL(h, location.href); return clean((u.host !== location.host ? u.host : '') + u.pathname, 50); }
    catch (e) { return clean(h, 50); }
  }

  const out = [];
  const seen = new Set();
  let next = 0;

  function consider(el, root) {
    if (seen.has(el)) return;
    seen.add(el);
    const r = visible(el);
    if (!r) return;
    const text = clean(ownText(el));
    const tag = el.tagName.toLowerCase();
    // Skip plain text nodes nested inside something clickable: the parent already represents them.
    const isLeafText = !el.matches(INTERACTIVE);
    if (isLeafText && el.parentElement && el.parentElement.closest(CLICKABLE_PARENT)) return;
    const id = next++;
    el.setAttribute('data-selenia-id', String(id));
    out.push({
      id: id,
      tag: tag,
      type: clean(el.getAttribute('type'), 20),
      role: clean(el.getAttribute('role'), 20),
      text: text,
      label: labelOf(el, root),
      aria: clean(el.getAttribute('aria-label'), 80),
      placeholder: clean(el.getAttribute('placeholder'), 60),
      name: clean(el.getAttribute('name'), 40),
      title: clean(el.getAttribute('title'), 60),
      alt: clean(el.getAttribute('alt'), 60),
      testid: clean(el.getAttribute('data-testid') || el.getAttribute('data-test'), 40),
      href: tag === 'a' ? shortHref(el) : '',
      context: contextOf(el),
      near: nearOf(el, text),
      x: +(((r.left + r.width / 2) + window.scrollX) / pageW).toFixed(3),
      y: +(((r.top + r.height / 2) + window.scrollY) / pageH).toFixed(3),
      in_shadow: root !== document,
    });
  }

  function walk(root) {
    root.querySelectorAll('[data-selenia-id]').forEach(el => el.removeAttribute('data-selenia-id'));
    root.querySelectorAll(INTERACTIVE).forEach(el => consider(el, root));
    // Short leaf text (prices, messages, table cells) that people also ask for.
    root.querySelectorAll('p,span,div,li,td,th,dd,dt,strong,em,small').forEach(el => {
      if (el.childElementCount === 0) {
        const t = clean(el.textContent, 200);
        if (t.length > 0 && t.length <= 120) consider(el, root);
      }
    });
    root.querySelectorAll('*').forEach(el => { if (el.shadowRoot) walk(el.shadowRoot); });
  }

  walk(document);
  return out;
})();
