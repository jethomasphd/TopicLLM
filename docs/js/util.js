/* String-preserving CSV and browser downloads. */

/** RFC-4180-ish CSV parser. Returns { header: string[], rows: object[] }. */
export function parseCSV(text) {
  if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1);  // Excel's UTF-8 BOM
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
  if (inQuotes) throw new Error('CSV contains an unclosed quoted field.');
  while (rows.length && rows[rows.length - 1].every(f => f === "")) rows.pop();
  const header = (rows.shift() || []).map(h => h.trim());
  if (header.some(h => !h) || new Set(header).size !== header.length) throw new Error('CSV headers must be non-empty and unique.');
  if (rows.some(r => r.length !== header.length)) throw new Error('CSV rows do not match the header column count.');
  return {
    header,
    rows: rows.map(r => Object.fromEntries(header.map((h, i) => [h, r[i] ?? ""]))),
  };
}

/** Serialize an array of objects to CSV using the given column order. */
export function toCSV(objs, columns) {
  const cols = columns || [...new Set(objs.flatMap(o => Object.keys(o)))];
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
