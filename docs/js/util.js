/* util.js — shared utilities: seeded PRNG, CSV, downloads, zip, misc. */

/** Mulberry32 PRNG — deterministic, seedable. Returns () => float in [0,1). */
export function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** FNV-1a 32-bit string hash (for deterministic per-word seeds). */
export function fnv1a(str) {
  let h = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

/** Sample k items without replacement using a seeded RNG. */
export function sample(arr, k, rng) {
  const idx = arr.map((_, i) => i);
  for (let i = idx.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [idx[i], idx[j]] = [idx[j], idx[i]];
  }
  return idx.slice(0, Math.min(k, arr.length)).map(i => arr[i]);
}

/** Pick one item with a seeded RNG. */
export function choice(arr, rng) { return arr[Math.floor(rng() * arr.length)]; }

/* ------------------------------ CSV ------------------------------------- */

/** RFC-4180-ish CSV parser. Returns { header: string[], rows: object[] }. */
export function parseCSV(text) {
  const rows = [];
  let row = [], field = "", inQuotes = false;
  const pushField = () => { row.push(field); field = ""; };
  const pushRow = () => { rows.push(row); row = []; };
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; }
        else inQuotes = false;
      } else field += c;
    } else if (c === '"') inQuotes = true;
    else if (c === ",") pushField();
    else if (c === "\n") { pushField(); pushRow(); }
    else if (c === "\r") { /* swallow; \n handles the row */ }
    else field += c;
  }
  if (field !== "" || row.length) { pushField(); pushRow(); }
  while (rows.length && rows[rows.length - 1].every(f => f === "")) rows.pop();
  const header = (rows.shift() || []).map(h => h.trim());
  return {
    header,
    rows: rows.map(r => Object.fromEntries(header.map((h, i) => [h, r[i] ?? ""]))),
  };
}

/** Serialize an array of objects to CSV using the given column order. */
export function toCSV(objs, columns) {
  const cols = columns || (objs.length ? Object.keys(objs[0]) : []);
  const esc = v => {
    const s = v == null ? "" : String(v);
    return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  return [cols.join(","), ...objs.map(o => cols.map(c => esc(o[c])).join(","))].join("\n");
}

/* --------------------------- Downloads ---------------------------------- */

export function downloadBlob(name, blob) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}

export function downloadText(name, text, mime = "text/plain") {
  downloadBlob(name, new Blob([text], { type: mime + ";charset=utf-8" }));
}

/* ------------------------- Store-only ZIP -------------------------------- */

const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();

function crc32(bytes) {
  let c = 0xFFFFFFFF;
  for (let i = 0; i < bytes.length; i++) c = CRC_TABLE[(c ^ bytes[i]) & 0xFF] ^ (c >>> 8);
  return (c ^ 0xFFFFFFFF) >>> 0;
}

/** Build an uncompressed (store) ZIP from { "path/name.ext": stringOrBytes }. */
export function buildZip(files) {
  const enc = new TextEncoder();
  const chunks = [], central = [];
  let offset = 0;
  const now = new Date();
  const dosTime = ((now.getHours() << 11) | (now.getMinutes() << 5) | (now.getSeconds() >> 1)) & 0xFFFF;
  const dosDate = (((now.getFullYear() - 1980) << 9) | ((now.getMonth() + 1) << 5) | now.getDate()) & 0xFFFF;

  const u16 = n => new Uint8Array([n & 0xFF, (n >> 8) & 0xFF]);
  const u32 = n => new Uint8Array([n & 0xFF, (n >> 8) & 0xFF, (n >> 16) & 0xFF, (n >>> 24) & 0xFF]);

  for (const [name, content] of Object.entries(files)) {
    const nameB = enc.encode(name);
    const data = typeof content === "string" ? enc.encode(content) : content;
    const crc = crc32(data);
    const localParts = [u32(0x04034b50), u16(20), u16(0x0800), u16(0), u16(dosTime), u16(dosDate),
      u32(crc), u32(data.length), u32(data.length), u16(nameB.length), u16(0), nameB, data];
    const localLen = localParts.reduce((s, p) => s + p.length, 0);
    central.push({ nameB, crc, size: data.length, offset, dosTime, dosDate });
    for (const p of localParts) chunks.push(p);
    offset += localLen;
  }
  const centralStart = offset;
  let centralLen = 0;
  for (const f of central) {
    const parts = [u32(0x02014b50), u16(20), u16(20), u16(0x0800), u16(0), u16(f.dosTime), u16(f.dosDate),
      u32(f.crc), u32(f.size), u32(f.size), u16(f.nameB.length), u16(0), u16(0), u16(0), u16(0),
      u32(0), u32(f.offset), f.nameB];
    for (const p of parts) chunks.push(p);
    centralLen += parts.reduce((s, p) => s + p.length, 0);
  }
  chunks.push(u32(0x06054b50), u16(0), u16(0), u16(central.length), u16(central.length),
    u32(centralLen), u32(centralStart), u16(0));
  return new Blob(chunks, { type: "application/zip" });
}

/* ----------------------------- Misc -------------------------------------- */

export function slug(name) { return String(name).replace(/[^A-Za-z0-9]+/g, "_").replace(/^_+|_+$/g, ""); }

export function pct(x, digits = 1) { return (100 * x).toFixed(digits) + "%"; }

export function escapeHTML(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
