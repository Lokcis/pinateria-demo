/**
 * Conversor Markdown -> .docx para los documentos de Piñatería Demo.
 * Soporta: portada, encabezados #/##/###, párrafos, viñetas (2 niveles), listas numeradas,
 * tablas con pipes (<!-- kv --> antes de la tabla = sin fila de encabezado),
 * bloques ``` de código, imágenes ![][imageN] con definiciones data:URI, negrita/cursiva/código.
 *
 * Uso: node md2docx.js entrada.md salida.docx "Texto del pie"
 */
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType,
  AlignmentType, BorderStyle, ShadingType, ImageRun, Footer, PageNumber, LevelFormat, TabStopType,
} = require("docx");

const [entrada, salida, textoPie = ""] = process.argv.slice(2);
const FUENTE = "Calibri";
const ANCHO = 9360; // Letter, margenes de 1"
const COLOR_ENCABEZADO = "1F3864";
const COLOR_TITULO = "7A1F5C";

const lineas = fs.readFileSync(entrada, "utf8").replace(/\r\n/g, "\n").split("\n");

// ---------- imagenes: definiciones [imageN]: <data:image/png;base64,...>
const imagenes = {};
const cuerpo = [];
for (const l of lineas) {
  const m = l.match(/^\[(image\d+)\]:\s*<data:image\/(\w+);base64,(.*)>\s*$/);
  if (m) imagenes[m[1]] = { tipo: m[2] === "jpeg" ? "jpg" : m[2], datos: Buffer.from(m[3], "base64") };
  else cuerpo.push(l);
}

function dimensionesPng(buf) {
  if (buf.slice(1, 4).toString() === "PNG") return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) };
  return { w: 800, h: 450 };
}

// ---------- inline
function desescapar(t) {
  return t.replace(/\\([\\`*_{}\[\]()#+\-.!|<>~$])/g, "$1");
}

function inline(texto, base = {}) {
  const runs = [];
  const re = /(\*\*(.+?)\*\*|`([^`]+)`|\*(?!\s)(.+?)(?<!\s)\*)/g;
  let ultimo = 0;
  let m;
  const pushPlano = (t) => {
    if (!t) return;
    const partes = desescapar(t).split("\u0001");
    partes.forEach((p, i) => {
      if (i > 0) runs.push(new TextRun({ break: 1, ...base }));
      if (p) runs.push(new TextRun({ text: p, font: FUENTE, ...base }));
    });
  };
  texto = texto.replace(/<br\s*\/?>/g, "\u0001");
  while ((m = re.exec(texto)) !== null) {
    pushPlano(texto.slice(ultimo, m.index));
    if (m[2] !== undefined) runs.push(...inline(m[2], { ...base, bold: true }));
    else if (m[3] !== undefined) runs.push(new TextRun({ text: m[3], font: "Consolas", size: (base.size || 22) - 2, ...base, font: "Consolas" }));
    else runs.push(...inline(m[4], { ...base, italics: true }));
    ultimo = m.index + m[0].length;
  }
  pushPlano(texto.slice(ultimo));
  return runs;
}

// ---------- bloques
const hijos = [];
let i = 0;
let portada = true;
let primerH = -1;
let tocIdx = -1;
const encabezados1 = [];

function esTabla(l) { return /^\s*\|/.test(l); }
function celdas(l) {
  let t = l.trim();
  if (t.startsWith("|")) t = t.slice(1);
  if (t.endsWith("|")) t = t.slice(0, -1);
  // dividir por | no escapado
  return t.split(/(?<!\\)\|/).map((c) => c.trim());
}

function construirTabla(filas, kv) {
  const n = Math.max(...filas.map((f) => f.length));
  const largos = Array(n).fill(4);
  filas.forEach((f) => f.forEach((c, j) => { largos[j] = Math.max(largos[j], Math.min(60, desescapar(c).length)); }));
  const pesos = largos.map((x) => Math.sqrt(x) + 1.5);
  const suma = pesos.reduce((a, b) => a + b, 0);
  let anchos = pesos.map((p) => Math.floor((p / suma) * ANCHO));
  anchos[anchos.length - 1] += ANCHO - anchos.reduce((a, b) => a + b, 0);
  const borde = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
  const bordes = { top: borde, bottom: borde, left: borde, right: borde };
  const filasDocx = filas.map((f, r) => new TableRow({
    tableHeader: !kv && r === 0,
    cantSplit: true,
    children: Array.from({ length: n }, (_, j) => {
      const encabezado = !kv && r === 0;
      const llaveKv = kv && j === 0;
      const texto = f[j] || "";
      const parrafos = texto.split("\u0002").map((p) => new Paragraph({
        spacing: { before: 40, after: 40 },
        children: inline(p, { size: 21, ...(encabezado ? { bold: true, color: "FFFFFF" } : {}), ...(llaveKv ? { bold: true } : {}) }),
      }));
      return new TableCell({
        width: { size: anchos[j], type: WidthType.DXA },
        borders: bordes,
        margins: { top: 70, bottom: 70, left: 120, right: 120 },
        shading: encabezado
          ? { fill: COLOR_ENCABEZADO, type: ShadingType.CLEAR, color: "auto" }
          : llaveKv ? { fill: "EDEDED", type: ShadingType.CLEAR, color: "auto" }
          : (r % 2 === 0 ? { fill: "F7F9FC", type: ShadingType.CLEAR, color: "auto" } : undefined),
        children: parrafos,
      });
    }),
  }));
  return new Table({ width: { size: ANCHO, type: WidthType.DXA }, columnWidths: anchos, rows: filasDocx });
}

let proximaKv = false;
while (i < cuerpo.length) {
  const l = cuerpo[i];
  const t = l.trim();

  if (t === "") { i++; continue; }
  if (t === "<!-- kv -->") { proximaKv = true; i++; continue; }
  if (/^<!--.*-->$/.test(t)) { i++; continue; }

  // bloque de codigo
  if (t.startsWith("```")) {
    i++;
    const codigo = [];
    while (i < cuerpo.length && !cuerpo[i].trim().startsWith("```")) { codigo.push(cuerpo[i]); i++; }
    i++;
    codigo.forEach((c, k) => hijos.push(new Paragraph({
      spacing: { before: 0, after: 0, line: 240 },
      shading: { fill: "F2F2F2", type: ShadingType.CLEAR, color: "auto" },
      indent: { left: 120, right: 120 },
      keepLines: true,
      children: [new TextRun({ text: c.replace(/ /g, " ") || " ", font: "Consolas", size: 17 })],
    })));
    hijos.push(new Paragraph({ spacing: { after: 120 }, children: [] }));
    continue;
  }

  // encabezados
  const h = t.match(/^(#{1,3})\s+(.*)$/);
  if (h) {
    portada = false;
    const nivel = h[1].length;
    const texto = h[2].replace(/^\*\*(.*)\*\*$/, "$1");
    if (nivel === 1) encabezados1.push(desescapar(texto));
    if (primerH < 0) primerH = hijos.length;
    if (/Tabla de Contenido/i.test(texto)) tocIdx = hijos.length;
    hijos.push(new Paragraph({
      heading: [HeadingLevel.HEADING_1, HeadingLevel.HEADING_2, HeadingLevel.HEADING_3][nivel - 1],
      keepNext: true,
      children: [new TextRun({ text: desescapar(texto), font: FUENTE })],
    }));
    i++;
    continue;
  }

  // tabla
  if (esTabla(l)) {
    const filas = [];
    while (i < cuerpo.length && esTabla(cuerpo[i])) {
      const c = celdas(cuerpo[i]);
      if (!c.every((x) => /^:?-{2,}:?$/.test(x))) filas.push(c);
      i++;
    }
    const autoKv = filas.length >= 2 && filas.every((f) => f.length === 2) && /^\*\*/.test(filas[1][0] || "") && !/^\*\*/.test(filas[0][0] || "");
    hijos.push(construirTabla(filas, proximaKv || autoKv));
    hijos.push(new Paragraph({ spacing: { after: 160 }, children: [] }));
    proximaKv = false;
    continue;
  }

  // imagen enlazada a un archivo: ![texto](ruta/relativa.png)
  const imf = t.match(/^!\[[^\]]*\]\(([^)]+)\)$/);
  if (imf) {
    const ruta = require("path").resolve(require("path").dirname(entrada), imf[1]);
    if (fs.existsSync(ruta)) {
      const datos = fs.readFileSync(ruta);
      const { w, h: alto } = dimensionesPng(datos);
      const escala = Math.min(1, 620 / w);
      hijos.push(new Paragraph({
        alignment: AlignmentType.CENTER, spacing: { before: 120, after: 120 },
        children: [new ImageRun({ type: "png", data: datos, transformation: { width: Math.round(w * escala), height: Math.round(alto * escala) }, altText: { title: "Figura", description: "Figura", name: imf[1] } })],
      }));
      i++;
      continue;
    }
  }

  // imagen
  const im = t.match(/^!\[[^\]]*\]\[(image\d+)\]$/);
  if (im && imagenes[im[1]]) {
    const { datos, tipo } = imagenes[im[1]];
    const { w, h: alto } = dimensionesPng(datos);
    const maxW = 620;
    const escala = Math.min(1, maxW / w);
    hijos.push(new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { before: 120, after: 120 },
      children: [new ImageRun({ type: tipo, data: datos, transformation: { width: Math.round(w * escala), height: Math.round(alto * escala) }, altText: { title: "Figura", description: "Figura", name: im[1] } })],
    }));
    i++;
    continue;
  }

  // listas
  const vi = l.match(/^(\s*)[*\-+]\s+(.*)$/);
  if (vi) {
    const nivel = Math.min(1, Math.floor(vi[1].length / 2));
    hijos.push(new Paragraph({ numbering: { reference: "viñetas", level: nivel }, spacing: { after: 60 }, children: inline(vi[2], { size: 22 }) }));
    i++;
    continue;
  }
  const nu = l.match(/^\s*(\d+)[.)]\s+(.*)$/);
  if (nu) {
    hijos.push(new Paragraph({ numbering: { reference: "numeradas", level: 0 }, spacing: { after: 60 }, children: inline(nu[2], { size: 22 }) }));
    i++;
    continue;
  }

  // portada (antes del primer encabezado)
  if (portada) {
    const esTitulo = /^\*\*PIÑATERÍA/.test(t);
    const esDoc = /^\*\*[^*]+\*\*$/.test(t) && !esTitulo;
    hijos.push(new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: esTitulo ? 2400 : 120, after: 120 },
      children: inline(t, { size: esTitulo ? 52 : esDoc ? 40 : 26, color: esTitulo || esDoc ? COLOR_TITULO : "404040", ...(esTitulo || esDoc ? { bold: true } : {}) }),
    }));
    i++;
    continue;
  }

  // parrafo (une lineas contiguas)
  const partes = [t];
  i++;
  while (i < cuerpo.length && cuerpo[i].trim() !== "" && !/^(#{1,3}\s|\||```|\s*[*\-+]\s|\s*\d+[.)]\s|!\[|<!--)/.test(cuerpo[i])) { partes.push(cuerpo[i].trim()); i++; }
  hijos.push(new Paragraph({ spacing: { after: 120, line: 276 }, children: inline(partes.join(" "), { size: 22 }) }));
}

// tabla de contenido estatica y salto de pagina tras la portada (se inserta de mayor a menor indice)
if (tocIdx >= 0) {
  const items = encabezados1.filter((t) => !/Tabla de Contenido/i.test(t)).map((t) => new Paragraph({ spacing: { after: 60 }, indent: { left: 360 }, children: [new TextRun({ text: t, font: FUENTE, size: 22 })] }));
  hijos.splice(tocIdx + 1, 0, ...items);
}
if (primerH > 0) hijos.splice(primerH, 0, new Paragraph({ pageBreakBefore: true, children: [] }));

const doc = new Document({
  creator: "Santiago Chávez López",
  title: textoPie,
  styles: {
    default: { document: { run: { font: FUENTE, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 32, bold: true, font: FUENTE, color: COLOR_TITULO }, paragraph: { spacing: { before: 360, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 26, bold: true, font: FUENTE, color: COLOR_ENCABEZADO }, paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 23, bold: true, font: FUENTE, color: "404040" }, paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "viñetas", levels: [
        { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1080, hanging: 270 } } } },
      ] },
      { reference: "numeradas", levels: [
        { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 360 } } } },
      ] },
    ],
  },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          tabStops: [{ type: TabStopType.RIGHT, position: ANCHO }],
          border: { top: { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF", space: 4 } },
          children: [
            new TextRun({ text: textoPie, font: FUENTE, size: 16, color: "7F7F7F" }),
            new TextRun({ text: "\tPágina ", font: FUENTE, size: 16, color: "7F7F7F" }),
            new TextRun({ children: [PageNumber.CURRENT], font: FUENTE, size: 16, color: "7F7F7F" }),
          ],
        })],
      }),
    },
    children: hijos,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(salida, buf);
  console.log("OK", salida, (buf.length / 1024).toFixed(0) + " KB", "encabezados1:", encabezados1.length);
});
