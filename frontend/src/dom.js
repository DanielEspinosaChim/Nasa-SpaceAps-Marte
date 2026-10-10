// Utilidades DOM. Todo texto externo entra con textContent/createTextNode, nunca con innerHTML.

export function el(tag, opts = {}, ...children) {
  const node = document.createElement(tag);
  if (opts.class) node.className = opts.class;
  if (opts.text != null) node.textContent = String(opts.text);
  if (opts.attrs) for (const [k, v] of Object.entries(opts.attrs)) node.setAttribute(k, String(v));
  if (opts.on) for (const [ev, fn] of Object.entries(opts.on)) node.addEventListener(ev, fn);
  for (const c of children.flat()) {
    if (c == null || c === false) continue;
    node.append(typeof c === 'string' || typeof c === 'number' ? document.createTextNode(String(c)) : c);
  }
  return node;
}

export function clear(node) {
  node.replaceChildren();
  return node;
}

export function fmtKm(m) {
  return m >= 1000 ? `${(m / 1000).toFixed(1)} km` : `${Math.round(m)} m`;
}

export function fmtNum(v, digits = 1) {
  return v == null || Number.isNaN(v) ? '—' : Number(v).toFixed(digits);
}

export function metric(key, value) {
  return el('div', { class: 'metric' }, el('div', { class: 'v', text: value }), el('div', { class: 'k', text: key }));
}

export function explanationList(items) {
  return el('ul', { class: 'explain' }, items.map((t) => el('li', { text: t })));
}
