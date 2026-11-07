// Genera docs/final/NexoGuard_ProyectoFinal.docx a partir de los Markdown de las Partes A, B y C
// (fuente única: se corrigen los .md y se vuelve a ejecutar). Mismo estilo que docs/generar_docx.js del parcial.
//   npm install --no-save docx@9      (una vez)
//   node docs/final/generar_informe_final.js
// Las capturas se insertan solas si existen en docs/final/capturas/<nombre>.png (ver CAPTURAS más abajo).
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun, Header, Footer, AlignmentType,
  LevelFormat, HeadingLevel, BorderStyle, WidthType, ShadingType, PageNumber, VerticalAlign, TableOfContents, ExternalHyperlink,
} = require("docx");

const DIR = __dirname;
const OUT = process.env.OUT || path.join(DIR, "NexoGuard_ProyectoFinal.docx");
const NAVY = "0E1B33", BLUE = "1F4FD8", NARANJA = "FF8C00", GRIS = "E6E6E6", AZUL_HU = "C6DAFC", CW = 9026;
const FONT = "Arial";

// Capturas: si el archivo existe se inserta en lugar del recuadro [PENDIENTE] cuyo texto contiene la clave.
const CAPTURAS = [
  ["grafo de Step Functions", "step_functions.png"],
  ["tabla `nexo-validaciones`", "dynamodb_validaciones.png"],
  ["Collection Runner", "postman_runner.png"],
  ["capturas en la web desplegada", "web.png"],
  ["recursos del stack", "cloudformation.png"],
];

// ------------------------------------------------------------------ texto en línea
function enLinea(s, base = {}) {   // **negrita**, *cursiva*, `código`, [texto](url)
  const out = [];
  String(s).split(/(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\)|(?<![*\w])\*[^*\s][^*]*\*(?![*\w]))/).forEach((t) => {
    if (!t) return;
    if (t.startsWith("**")) out.push(...enLinea(t.slice(2, -2), { ...base, bold: true }));
    else if (t.startsWith("`")) out.push(new TextRun({ text: t.slice(1, -1), font: "Courier New", ...base, size: (base.size || 21) - 2 }));
    else if (/^\[[^\]]+\]\([^)]+\)$/.test(t)) {
      const m = t.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      out.push(/^https?:/.test(m[2])
        ? new ExternalHyperlink({ link: m[2], children: [new TextRun({ text: m[1], font: FONT, ...base, color: BLUE, underline: {} })] })
        : new TextRun({ text: m[1], font: FONT, ...base }));
    } else if (t.startsWith("*")) out.push(new TextRun({ text: t.slice(1, -1), font: FONT, ...base, italics: true }));
    else out.push(new TextRun({ text: t, font: FONT, ...base }));
  });
  return out;
}
const P = (s, o = {}) => new Paragraph({ children: enLinea(s, o.run || {}), spacing: { after: o.after ?? 120, before: o.before ?? 0, line: 300 },
  alignment: o.align, keepNext: o.keepNext });
const spacer = (n = 120) => new Paragraph({ children: [], spacing: { after: n } });

// ------------------------------------------------------------------ bloques
const borde = { style: BorderStyle.SINGLE, size: 4, color: "BFC7D5" };
const bordes = { top: borde, bottom: borde, left: borde, right: borde };
function celda(texto, w, o = {}) {
  return new TableCell({ width: { size: w, type: WidthType.DXA }, borders: bordes, verticalAlign: VerticalAlign.TOP,
    shading: o.fill ? { fill: o.fill, type: ShadingType.CLEAR, color: "auto" } : undefined, margins: { top: 50, bottom: 50, left: 90, right: 90 },
    children: [new Paragraph({ children: enLinea(texto, { size: o.size, bold: o.bold, color: o.color }), spacing: { after: 0, line: 250 },
      alignment: o.align })] });
}
function anchos(filas) {   // proporcional al largo (máximo y promedio) del texto de cada columna, con mínimo y máximo
  const n = filas[0].length;
  const largo = (t) => String(t || "").replace(/[*`]/g, "").length;
  const pesos = Array.from({ length: n }, (_, i) => {
    const ls = filas.map((f) => largo(f[i]));
    return Math.min(70, Math.max(6, 0.25 * Math.max(...ls) + 0.75 * (ls.reduce((a, b) => a + b, 0) / ls.length)));
  });
  const s = pesos.reduce((a, b) => a + b, 0);
  const w = pesos.map((p) => Math.floor((p / s) * CW));
  w[n - 1] += CW - w.reduce((a, b) => a + b, 0);
  return w;
}
function tabla(cab, filas) {
  const w = anchos([cab, ...filas]);
  const size = cab.length >= 6 ? 15 : cab.length >= 4 ? 16 : 18;
  const num = (t) => /^\*?\*?(US\$ )?[≈\d.,\s%$]+\*?\*?$/.test(t.trim()) && t.trim() !== "";
  const rows = [];
  if (cab.some((c) => c.trim())) rows.push(new TableRow({ tableHeader: true, cantSplit: true,
    children: cab.map((h, i) => celda(h, w[i], { fill: NAVY, bold: true, color: "FFFFFF", size })) }));
  filas.forEach((f, ri) => rows.push(new TableRow({ cantSplit: true, children: f.map((c, i) => celda(c, w[i], {
    size, fill: i === 0 ? "EEF3FF" : (ri % 2 ? "F7F9FC" : undefined), align: i > 0 && num(c) ? AlignmentType.RIGHT : undefined })) })));
  return new Table({ width: { size: CW, type: WidthType.DXA }, columnWidths: w, rows });
}
function caja(parrafos, fill) {
  return new Table({ width: { size: CW, type: WidthType.DXA }, columnWidths: [CW], rows: [new TableRow({ cantSplit: true, children: [new TableCell({
    children: parrafos, width: { size: CW, type: WidthType.DXA }, borders: bordes, shading: { fill, type: ShadingType.CLEAR, color: "auto" },
    margins: { top: 90, bottom: 90, left: 160, right: 160 } })] })] });
}
function codigo(lineas, gherkin) {
  const kids = lineas.map((l) => {
    const k = l.split(" ")[0];
    if (gherkin && ["GIVEN", "WHEN", "THEN", "AND"].includes(k)) {
      return new Paragraph({ spacing: { after: 20, line: 260 }, children: [
        new TextRun({ text: k + " ", bold: true, color: k === "AND" ? "2F5CB8" : "000000", font: FONT, size: 18 }),
        new TextRun({ text: l.slice(k.length + 1), font: FONT, size: 18 })] });
    }
    return new Paragraph({ spacing: { after: 0, line: 240 }, children: [new TextRun({ text: l === "" ? " " : l, font: gherkin ? FONT : "Courier New", size: gherkin ? 18 : 15 })] });
  });
  return caja(kids, gherkin ? GRIS : "F3F4F6");
}
function imagen(ruta, ancho = 600, pie) {
  const b = fs.readFileSync(ruta);
  const alto = Math.round((ancho * b.readUInt32BE(20)) / b.readUInt32BE(16));   // proporción real del PNG
  const out = [new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { after: 60 }, children: [new ImageRun({
    type: "png", data: b, transformation: { width: ancho, height: alto }, altText: { title: path.basename(ruta), description: pie || ruta, name: path.basename(ruta) } })] })];
  if (pie) out.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({ text: pie, italics: true, size: 17, color: "555555", font: FONT })] }));
  return out;
}

// ------------------------------------------------------------------ Markdown → docx
let instancias = 0;
function convertir(md, base) {
  const out = [];
  const lineas = md.replace(/\r/g, "").split("\n");
  let i = 0, primerH1 = true;
  const esTabla = (l) => /^\s*\|/.test(l);
  while (i < lineas.length) {
    const l = lineas[i];
    if (!l.trim() || /^---+$/.test(l.trim())) { i++; continue; }
    let m;
    if ((m = l.match(/^(#{1,3}) (.*)$/))) {
      const nivel = m[1].length;
      out.push(new Paragraph({ heading: [HeadingLevel.HEADING_1, HeadingLevel.HEADING_2, HeadingLevel.HEADING_3][nivel - 1],
        pageBreakBefore: nivel === 1 && !primerH1, keepNext: true, children: enLinea(m[2]) }));
      if (nivel === 1) primerH1 = false;
      i++; continue;
    }
    if (l.startsWith("```")) {
      const lang = l.slice(3).trim(), bloque = [];
      i++;
      while (i < lineas.length && !lineas[i].startsWith("```")) bloque.push(lineas[i++]);
      i++;
      out.push(codigo(bloque, lang === "gherkin"), spacer(80));
      continue;
    }
    if (esTabla(l)) {
      const filas = [];
      while (i < lineas.length && esTabla(lineas[i])) {
        const celdas = lineas[i].trim().replace(/^\||\|$/g, "").split(/(?<!\\)\|/).map((c) => c.trim().replace(/\\\|/g, "|"));
        if (!celdas.every((c) => /^:?-+:?$/.test(c))) filas.push(celdas);
        i++;
      }
      out.push(tabla(filas[0], filas.slice(1)), spacer(100));
      continue;
    }
    if (l.startsWith(">")) {
      const bloque = [];
      while (i < lineas.length && lineas[i].startsWith(">")) bloque.push(lineas[i++].replace(/^>\s?/, ""));
      // keepNext: el recuadro COMO/QUIERO/PARA no se separa de su título ni de sus criterios
      out.push(caja(bloque.filter((x) => x.trim()).map((x) => P(x, { after: 30, keepNext: true, run: { size: 19 } })), AZUL_HU), spacer(80));
      continue;
    }
    if ((m = l.match(/^!\[([^\]]*)\]\(([^)]+)\)/))) {
      const ruta = path.join(base, m[2]);
      if (fs.existsSync(ruta)) out.push(...imagen(ruta, 620));
      i++; continue;
    }
    if ((m = l.match(/^(\s*)([-*]|\d+\.) (.*)$/))) {
      const instancia = ++instancias;   // cada lista numerada empieza en 1
      while (i < lineas.length && (m = lineas[i].match(/^(\s*)([-*]|\d+\.) (.*)$/))) {
        const nivel = m[1].length >= 2 ? 1 : 0, numerado = /\d/.test(m[2]);
        let texto = m[3];
        i++;
        while (i < lineas.length && /^\s{2,}\S/.test(lineas[i]) && !/^\s*([-*]|\d+\.) /.test(lineas[i]) && !lineas[i].trim().startsWith("```")) texto += " " + lineas[i++].trim();
        out.push(new Paragraph({ numbering: { reference: numerado ? "num" : "bul", level: nivel, ...(numerado ? { instance: instancia } : {}) },
          children: enLinea(texto), spacing: { after: 50, line: 280 } }));
        if (i < lineas.length && /^\s+```/.test(lineas[i])) {   // bloque de código dentro de una lista
          const bloque = []; i++;
          while (i < lineas.length && !lineas[i].trim().startsWith("```")) bloque.push(lineas[i++].trim());
          i++; out.push(codigo(bloque, false));
          const sigue = [];   // texto con sangría después del bloque: sigue siendo parte del mismo ítem
          while (i < lineas.length && /^\s{2,}\S/.test(lineas[i]) && !/^\s*([-*]|\d+\.) /.test(lineas[i])) sigue.push(lineas[i++].trim());
          if (sigue.length) out.push(new Paragraph({ indent: { left: 540 }, spacing: { after: 50, line: 280 }, children: enLinea(sigue.join(" ")) }));
        }
      }
      out.push(spacer(60));
      continue;
    }
    if ((m = l.match(/^\*\*\[PENDIENTE: (.*)\]\*\*$/))) {
      const cap = CAPTURAS.find(([clave]) => m[1].includes(clave));
      const ruta = cap && path.join(DIR, "capturas", cap[1]);
      if (ruta && fs.existsSync(ruta)) out.push(...imagen(ruta, 600));
      else out.push(caja([P(`📷 **Captura pendiente:** ${m[1]}` + (cap ? `  (archivo esperado: docs/final/capturas/${cap[1]})` : ""), { after: 0, run: { size: 19 } })], "FFF8E1"), spacer(100));
      i++; continue;
    }
    const parrafo = [l.trim()];   // párrafo: líneas seguidas hasta un bloque
    i++;
    while (i < lineas.length && lineas[i].trim() && !/^(#|```|>|\s*\||!\[|\s*([-*]|\d+\.) )/.test(lineas[i])) parrafo.push(lineas[i++].trim());
    out.push(P(parrafo.join(" ")));
  }
  return out;
}

// ------------------------------------------------------------------ portada
const portada = [
  spacer(1100),
  P("Universidad de Ingeniería y Tecnología — UTEC Posgrado", { after: 40, run: { size: 22, color: "555555" } }),
  P("Maestría en Ciencia de Datos e Inteligencia Artificial (CDIA V5)", { after: 40, run: { size: 22, color: "555555" } }),
  P("Curso: Cloud Computing", { after: 500, run: { size: 22, color: "555555" } }),
  P("Proyecto Final", { after: 60, run: { size: 30, bold: true, color: BLUE } }),
  P("NexoGuard", { after: 60, run: { size: 76, bold: true, color: NAVY } }),
  new Paragraph({ border: { bottom: { style: BorderStyle.SINGLE, size: 18, color: NARANJA, space: 8 } }, spacing: { after: 500 },
    children: enLinea("Validación inteligente de operaciones de cambio — Workflow agéntico de Nivel 4 sobre NexoCambio en AWS", { size: 28, color: NAVY }) }),
  tabla(["", ""], [
    ["**Docente**", "Geraldo Colchado"],
    ["**Integrantes**", "Frank Laura Borja · Josue Aron Campos Quiroz · Mauricio Elias Vallejos García · Axel Fuentes Pacheco · Sebastian Tadeo Gallegos Mostajo"],
    ["**Entrega**", "Martes 17-Nov-2026, 23:59 h"],
    ["**Exposición virtual**", "Miércoles 18-Nov-2026, 19:00 h"],
    ["**Repositorio GitHub**", "[https://github.com/frankcg/nexocambio](https://github.com/frankcg/nexocambio)"],
    ["**Aplicación web**", "[https://nexo-dev-web-899678635044-us-east-1.s3.us-east-1.amazonaws.com/index.html](https://nexo-dev-web-899678635044-us-east-1.s3.us-east-1.amazonaws.com/index.html) (back-office: `#/admin`)"],
    ["**API**", "https://ryipifjwef.execute-api.us-east-1.amazonaws.com/v1"],
  ]),
  spacer(300),
  P("Lima – Perú, noviembre de 2026", { align: AlignmentType.CENTER, run: { size: 20, color: "555555" } }),
  new Paragraph({ pageBreakBefore: true, heading: HeadingLevel.HEADING_1, children: enLinea("Contenido") }),
  new TableOfContents("Contenido", { hyperlink: true, headingStyleRange: "1-2" }),
  P("*Si el índice aparece vacío, en Word: clic derecho sobre él → «Actualizar campos».*", { before: 120, run: { size: 17, color: "777777" } }),
];

// ------------------------------------------------------------------ documento
const partes = ["parte_a_nexoguard.md", "parte_b_nexoguard.md", "parte_c_nexoguard.md"].map((f) => fs.readFileSync(path.join(DIR, f), "utf8"));
const anexo = fs.readFileSync(path.join(DIR, "guion_demo.md"), "utf8").replace(/^# .*$/m, "# ANEXO — GUION DE LA DEMO");
const cuerpo = [...partes, anexo].flatMap((md, k) => {
  const bloques = convertir(md, DIR);
  if (k === 0 && bloques[0]) bloques[0] = new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, keepNext: true, children: enLinea("PARTE A — ANÁLISIS (QUÉ)") });
  else if (bloques[0]) bloques[0] = new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, keepNext: true,
    children: enLinea(md.match(/^# (.*)$/m)[1]) });
  return bloques;
});

const header = new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "BFC7D5", space: 4 } },
  children: [new TextRun({ text: "NexoGuard · Proyecto Final · Cloud Computing (CDIA V5) · UTEC Posgrado", font: FONT, size: 16, color: "777777" })] })] });
const footer = new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
  new TextRun({ text: "Página ", font: FONT, size: 16, color: "777777" }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: "777777" })] })] });
const estilo = (size, color, before, after, extra = {}) => ({ run: { size, bold: true, font: FONT, color }, paragraph: { spacing: { before, after }, keepNext: true, ...extra } });
const doc = new Document({
  creator: "Equipo NexoCambio", title: "NexoGuard — Proyecto Final de Cloud Computing", features: { updateFields: true },
  styles: {
    default: {
      document: { run: { font: FONT, size: 21 } },
      heading1: estilo(34, NAVY, 120, 200, { border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: NARANJA, space: 6 } } }),
      heading2: estilo(26, BLUE, 280, 120),
      heading3: estilo(22, NAVY, 200, 80),
    },
  },
  numbering: { config: [
    { reference: "bul", levels: [
      { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } },
      { level: 1, format: LevelFormat.BULLET, text: "◦", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1000, hanging: 270 } } } }] },
    { reference: "num", levels: [
      { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 360 } } } },
      { level: 1, format: LevelFormat.LOWER_LETTER, text: "%2)", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1000, hanging: 360 } } } }] }] },
  sections: [{
    properties: { titlePage: true, page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, right: 1440, bottom: 1300, left: 1440 } } },
    headers: { default: header, first: new Header({ children: [new Paragraph({ children: [] })] }) },
    footers: { default: footer, first: new Footer({ children: [new Paragraph({ children: [] })] }) },
    children: [...portada, ...cuerpo],
  }],
});
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(OUT, b); console.log("docx ok", OUT, b.length, "bytes"); });
