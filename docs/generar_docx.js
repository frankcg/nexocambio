const fs = require("fs");
const D = require("docx");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun, Header, Footer, AlignmentType,
  PageOrientation, LevelFormat, HeadingLevel, BorderStyle, WidthType, ShadingType, PageNumber, PageBreak, VerticalAlign } = D;

const costos = JSON.parse(fs.readFileSync("docs/costos.json", "utf8"));
const NAVY = "0E1B33", BLUE = "1F4FD8", GRIS = "E6E6E6", AZUL_HU = "C6DAFC", CW = 9026;
const FONT = "Arial";

// ---------------------------------------------------------------- helpers
function md(s, base = {}) {            // **negrita** y `codigo`
  const out = [];
  String(s).split(/(\*\*[^*]+\*\*|`[^`]+`)/).forEach((t) => {
    if (!t) return;
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, font: FONT, ...base }));
    else if (t.startsWith("`")) out.push(new TextRun({ text: t.slice(1, -1), font: "Courier New", ...base, size: (base.size || 21) - 2 }));
    else out.push(new TextRun({ text: t, font: FONT, ...base }));
  });
  return out;
}
const P = (s, o = {}) => new Paragraph({ children: md(s, o.run || {}), spacing: { after: o.after ?? 120, before: o.before ?? 0, line: 300 },
  alignment: o.align, keepNext: o.keepNext, indent: o.indent });
const H1 = (s) => new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, children: [new TextRun({ text: s, font: FONT })] });
const H1s = (s) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: s, font: FONT })] });
const H2 = (s) => new Paragraph({ heading: HeadingLevel.HEADING_2, keepNext: true, children: [new TextRun({ text: s, font: FONT })] });
const H3 = (s) => new Paragraph({ heading: HeadingLevel.HEADING_3, keepNext: true, children: [new TextRun({ text: s, font: FONT })] });
const bullets = (arr) => arr.map((t) => new Paragraph({ numbering: { reference: "bul", level: 0 }, children: md(t), spacing: { after: 60, line: 290 } }));
let nInst = 0;
const numbered = (arr) => { const inst = ++nInst; return arr.map((t) => new Paragraph({ numbering: { reference: "num", level: 0, instance: inst }, children: md(t), spacing: { after: 60, line: 290 } })); };
const spacer = (n = 120) => new Paragraph({ children: [], spacing: { after: n } });

const borde = { style: BorderStyle.SINGLE, size: 4, color: "BFC7D5" };
const bordes = { top: borde, bottom: borde, left: borde, right: borde };
function celda(contenido, w, o = {}) {
  const items = Array.isArray(contenido) ? contenido : [contenido];
  const kids = items.map((c) => (c instanceof Paragraph ? c : new Paragraph({ children: md(c, { size: o.size || 18, bold: o.bold, color: o.color }), spacing: { after: 40, line: 260 }, alignment: o.align })));
  return new TableCell({ children: kids, width: { size: w, type: WidthType.DXA }, borders: bordes, verticalAlign: o.valign || VerticalAlign.TOP,
    shading: o.fill ? { fill: o.fill, type: ShadingType.CLEAR, color: "auto" } : undefined, margins: { top: 60, bottom: 60, left: 100, right: 100 }, columnSpan: o.span });
}
function escala(pesos, total = CW) { const s = pesos.reduce((a, b) => a + b, 0); const r = pesos.map((p) => Math.floor((p / s) * total)); r[r.length - 1] += total - r.reduce((a, b) => a + b, 0); return r; }
function tabla(pesos, head, filas, o = {}) {
  const w = escala(pesos, o.total || CW);
  const rows = [];
  if (head) rows.push(new TableRow({ tableHeader: true, cantSplit: true, children: head.map((h, i) => celda(h, w[i], { fill: NAVY, bold: true, color: "FFFFFF", size: o.size || 18 })) }));
  filas.forEach((f, ri) => rows.push(new TableRow({ cantSplit: true, children: f.map((c, i) => celda(c, w[i], { size: o.size || 18, fill: o.firstColFill && i === 0 ? "EEF3FF" : (o.zebra && ri % 2 ? "F7F9FC" : undefined), bold: o.firstColBold && i === 0 })) })));
  return new Table({ width: { size: o.total || CW, type: WidthType.DXA }, columnWidths: w, rows });
}
function caja(parrafos, fill, o = {}) {   // una celda con fondo
  return new Table({ width: { size: CW, type: WidthType.DXA }, columnWidths: [CW], rows: [new TableRow({ children: [new TableCell({
    children: parrafos, width: { size: CW, type: WidthType.DXA }, borders: bordes, shading: { fill, type: ShadingType.CLEAR, color: "auto" }, margins: { top: 100, bottom: 100, left: 160, right: 160 } })] })] });
}
function historia(id, titulo, como, quiero, para, mvp) {
  const linea = (k, v) => new Paragraph({ spacing: { after: 20, line: 270 }, children: [new TextRun({ text: k + " ", bold: true, font: FONT, size: 19 }), new TextRun({ text: v, font: FONT, size: 19 })] });
  const w = [CW - 1100, 1100];
  return new Table({ width: { size: CW, type: WidthType.DXA }, columnWidths: w, rows: [new TableRow({ cantSplit: true, children: [
    new TableCell({ width: { size: w[0], type: WidthType.DXA }, borders: bordes, shading: { fill: AZUL_HU, type: ShadingType.CLEAR, color: "auto" }, margins: { top: 90, bottom: 90, left: 140, right: 100 },
      children: [linea("COMO", como + ","), linea("QUIERO", quiero + ","), linea("PARA", para)] }),
    new TableCell({ width: { size: w[1], type: WidthType.DXA }, borders: bordes, verticalAlign: VerticalAlign.CENTER, shading: { fill: mvp ? "B7E36B" : "EDEDED", type: ShadingType.CLEAR, color: "auto" },
      children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: mvp ? "MVP" : "POST-MVP", bold: true, font: FONT, size: mvp ? 24 : 16 })] })] })] })] });
}
function gherkin(lineas) {   // lineas: "GIVEN ...", "WHEN ...", "AND ...", "THEN ..."
  const kids = lineas.map((l) => { const [k, ...r] = l.split(" "); const azul = k === "AND";
    return new Paragraph({ spacing: { after: 30, line: 265 }, children: [new TextRun({ text: k + " ", bold: true, color: azul ? "2F5CB8" : "000000", font: FONT, size: 18 }), new TextRun({ text: r.join(" "), font: FONT, size: 18 })] }); });
  return new Table({ width: { size: CW, type: WidthType.DXA }, columnWidths: [CW], rows: [new TableRow({ cantSplit: true, children: [new TableCell({ children: kids, width: { size: CW, type: WidthType.DXA }, borders: bordes,
    shading: { fill: GRIS, type: ShadingType.CLEAR, color: "auto" }, margins: { top: 90, bottom: 90, left: 140, right: 140 } })] })] });
}
function codigo(lineas, o = {}) {
  const kids = lineas.map((l) => new Paragraph({ spacing: { after: 0, line: 240 }, children: [new TextRun({ text: l === "" ? " " : l, font: "Courier New", size: o.size || 16 })] }));
  return new Table({ width: { size: CW, type: WidthType.DXA }, columnWidths: [CW], rows: [new TableRow({ children: [new TableCell({ children: kids, width: { size: CW, type: WidthType.DXA }, borders: bordes,
    shading: { fill: "F3F4F6", type: ShadingType.CLEAR, color: "auto" }, margins: { top: 80, bottom: 80, left: 140, right: 140 } })] })] });
}
function img(path, w, h) { return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 }, children: [new ImageRun({ type: "png", data: fs.readFileSync(path), transformation: { width: w, height: h }, altText: { title: path, description: path, name: path } })] }); }
const pie = (s) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({ text: s, italics: true, size: 17, color: "555555", font: FONT })] });
const nota = (s) => caja([P(s, { after: 0, run: { size: 19 } })], "FFF8E1");
const usd = (n) => "US$ " + n.toFixed(2);

const SH = "/tmp/shots/";
const c = []; // contenido sección 1

// ================================================================ PORTADA
c.push(spacer(1400));
c.push(new Paragraph({ alignment: AlignmentType.LEFT, children: [new TextRun({ text: "Maestría en Ciencia de Datos e Inteligencia Artificial (CDIA V5)", font: FONT, size: 22, color: "555555" })] }));
c.push(new Paragraph({ children: [new TextRun({ text: "Curso: Cloud Computing", font: FONT, size: 22, color: "555555" })], spacing: { after: 500 } }));
c.push(new Paragraph({ children: [new TextRun({ text: "Proyecto Parcial", font: FONT, size: 30, bold: true, color: BLUE })], spacing: { after: 60 } }));
c.push(new Paragraph({ children: [new TextRun({ text: "NexoCambio", font: FONT, size: 76, bold: true, color: NAVY })], spacing: { after: 60 } }));
c.push(new Paragraph({ children: [new TextRun({ text: "Casa de cambio de divisas y criptoactivos 100% digital en AWS", font: FONT, size: 28, color: NAVY })],
  border: { bottom: { style: BorderStyle.SINGLE, size: 18, color: "FF8C00", space: 8 } }, spacing: { after: 500 } }));
c.push(tabla([30, 70], null, [
  ["**Docente**", "Geraldo Colchado"], ["**Entrega**", "Martes 06-Oct-2026, 23:59 h"], ["**Exposición virtual**", "Miércoles 07-Oct-2026, 19:00 h"],
  ["**Integrantes**", ["[Integrante 1]", "[Integrante 2]", "[Integrante 3]", "[Integrante 4]", "[Integrante 5]"]],
  ["**Repositorio GitHub**", "[https://github.com/<organización>/nexocambio]"],
  ["**Prototipo (FrontEnd)**", "https://claude.ai/artifact/AR38oPWroLtipBBGz6fXRP"],
], { firstColFill: true, size: 20 }));
c.push(spacer(200));
c.push(nota("**Antes de entregar:** complete los campos entre [corchetes], pegue las capturas indicadas en la sección C.3 (Postman, consola de AWS y AWS Pricing Calculator) y verifique los precios en la calculadora."));

// ================================================================ PARTE A
c.push(H1("PARTE A — ANÁLISIS (QUÉ)"));
c.push(H2("1. Empresa y producto 100% digital propuesto"));
c.push(tabla([28, 72], null, [
  ["**Empresa**", "NexoCambio — startup fintech ficticia (proyecto académico)."],
  ["**Producto / servicio 100% digital**", "**NexoCambio Digital**: casa de cambio de divisas y de criptoactivos."],
  ["**Tipo de solución**", "Plataforma web responsive (desktop, tablet y móvil), sin agencias físicas."],
  ["**Monedas y activos**", "Divisas: PEN, USD, EUR. Cripto: USDT, USDC, BTC, ETH (contra PEN o USD)."],
  ["**Identidad visual**", "Casa de Cambio: azul. Cripto: verde oscuro. El usuario alterna entre ambas desde el mismo cotizador, sin salir de la página."],
], { firstColFill: true }));
c.push(P("NexoCambio Digital permite a personas y empresas cotizar y registrar operaciones de cambio de divisas y de activos virtuales desde una sola experiencia web: cotizar, registrarse, confirmar la operación, adjuntar el comprobante de la transferencia y hacer seguimiento del estado.", { before: 140 }));
c.push(nota("Aviso académico: las tasas de demostración, cuentas bancarias y direcciones de billetera que muestra el prototipo son ficticias. El MVP no procesa fondos reales."));

c.push(H2("2. Benchmark"));
c.push(P("Se revisaron cuatro productos similares que operan en Perú: tres de cambio de divisas y uno de compra/venta de cripto. La información proviene de los sitios y publicaciones indicados al pie y puede cambiar."));
c.push(tabla([13, 17, 40, 30], ["Referencia", "Tipos de clientes", "Funcionalidades", "Propuesta de valor"], [
  ["**Kambista** (casa de cambio online)", "Personas (app y web).", ["Cotización en tiempo real y ahorro acumulado.", "Tasas preferenciales por montos altos.", "Validación de identidad biométrica.", "Cambio desde y hacia cualquier banco."], "Cambiar soles y dólares sin colas ni salir de casa, con dinero acreditado en pocos minutos (menos de 20 min en operaciones inmediatas, según su ficha de la app)."],
  ["**TuCambista** (casa de cambio online)", "Personas y empresas.", ["Registro con DNI y cotizador.", "Transferencia bancaria y carga de foto del comprobante.", "Tipo de cambio actualizado; app iOS/Android.", "Monto mínimo US$ 10, sin máximo."], "Tipo de cambio competitivo frente a bancos, operación 100% online y empresa registrada ante la SBS."],
  ["**Cambio Seguro** (grupo Prestamype)", "Personas naturales y empresas.", ["Web y app móvil.", "Opera con todos los bancos del Perú.", "Cuentas BCP/Interbank: ~15 min; otros bancos: hasta 1 día útil."], "Comprar y vender dólares de forma segura, con respaldo de un grupo financiero y registro en la SBS."],
  ["**Lemon** (billetera cripto)", "Personas.", ["Compra de cripto desde 1 sol.", "Pago por Yape, Plin o transferencia CCI.", "Más de 30 criptomonedas; envío/recepción en 18+ redes."], "Comprar cripto en soles sin ser experto, desde una sola app."],
], { size: 17 }));
c.push(pie("Fuentes: kambista (ficha en tienda de apps, mwm.ai/apps/kambista), tucambista.pe, rpp.pe (publirreportaje de Cambio Seguro), lemon.me (blog Perú). Consulta: septiembre de 2026."));
c.push(H3("Comparación de NexoCambio frente al benchmark"));
const Si = "Sí", No = "No obs.";
c.push(tabla([27, 13, 16, 15, 11, 18], ["Atributo", "Kambista", "TuCambista", "Cambio Seguro", "Lemon", "NexoCambio"], [
  ["Cambio de divisas (PEN/USD/EUR)", Si, Si, Si, "—", "**Sí**"],
  ["Compra/venta de cripto", "—", "—", "—", Si, "**Sí**"],
  ["Divisas y cripto en un mismo cotizador", "—", "—", "—", "—", "**Sí**"],
  ["Tasa preferencial por monto alto", Si, No, No, No, "**Sí** (desde US$ 5,000)"],
  ["Comprobante de transferencia + estados visibles", No, Si, No, No, "**Sí**"],
  ["Clientes empresa", No, Si, Si, No, "**Sí**"],
  ["App móvil nativa", Si, Si, Si, Si, "No (web responsive)"],
], { size: 17, firstColFill: true }));
c.push(pie("«No obs.» = no aparece en las fuentes revisadas; «—» = no aplica al producto. El MVP de NexoCambio no incluye app nativa."));

c.push(H2("3. Propuesta de valor"));
c.push(P("**NexoCambio ofrece una experiencia unificada para cotizar y gestionar operaciones de Casa de Cambio y Cripto desde una sola plataforma.** Comparado con el benchmark, que se especializa en divisas o en cripto, su diferenciación es:"));
c.push(...bullets([
  "**Una sola experiencia para divisas y cripto:** se alterna de modalidad en el mismo cotizador, sin redirección.",
  "**Cotizador protagonista** desde la primera pantalla, con la tasa visible y vigencia de 5 minutos.",
  "**Registro guiado por pasos** (persona natural o empresa), pensado para uso móvil.",
  "**Trazabilidad:** cada operación muestra su estado (Pendiente de validación → En proceso → Procesada / Rechazada), su historial y el comprobante asociado.",
  "**Transparencia:** el cliente conoce la tasa, el monto a recibir y si accede a tasa preferencial antes de operar.",
]));

c.push(H2("4. Tipos de usuarios"));
c.push(tabla([22, 35, 43], ["Tipo de usuario", "Descripción", "Qué puede hacer"], [
  ["**Visitante**", "Aún no inició sesión.", "Conocer el servicio, usar el cotizador, alternar Casa de Cambio/Cripto, registrarse o iniciar sesión."],
  ["**Cliente persona natural**", "Persona registrada e identificada (DNI, CE o pasaporte).", "Cotizar, iniciar sesión, registrar una operación, adjuntar comprobante y consultar operaciones, estados y detalle."],
  ["**Cliente empresa**", "Empresa registrada con RUC mediante un representante.", "Lo mismo que la persona natural, operando a nombre de la empresa."],
  ["**Operador NexoCambio** (interno)", "Valida comprobantes y avanza el estado de las operaciones.", "Sin interfaz en el MVP: se simula con un endpoint protegido (ver Parte B). Fuera de la experiencia del cliente."],
], { firstColFill: true }));

c.push(H2("5. Funcionalidades del producto"));
c.push(tabla([20, 52, 28], ["Módulo", "Funcionalidad", "Alcance"], [
  ["Página pública", "Presentar la marca, servicios, seguridad, contacto y accesos.", "MVP"],
  ["Cotizador", "Cotizar Casa de Cambio o Cripto desde la misma interfaz, con vigencia de 5 minutos.", "MVP (HU1)"],
  ["Registro / identificación", "Alta de persona natural o empresa en pasos progresivos.", "MVP (HU2)"],
  ["Login", "Acceso de clientes registrados con correo y contraseña.", "MVP (HU3)"],
  ["Operación", "Confirmar la cotización y registrar la cuenta de origen/destino.", "MVP (HU4)"],
  ["Comprobante", "Adjuntar imagen o PDF que evidencie la transferencia.", "MVP (HU5)"],
  ["Mis operaciones", "Listar las operaciones del cliente con su estado.", "MVP (HU6)"],
  ["Detalle de operación", "Datos completos, historial de estados y comprobante.", "MVP (HU7)"],
  ["Cuentas bancarias", "Guardar y reutilizar cuentas de destino.", "Post-MVP (HU8)"],
], { zebra: true }));

c.push(H2("6. Historias de usuario, criterios de aceptación y selección del MVP"));
c.push(P("**Criterio de selección.** Se prioriza un flujo completo de punta a punta que pueda demostrarse en AWS: cotizar → registrarse/iniciar sesión → registrar operación → adjuntar comprobante → consultar la operación y su estado. Se incluye el detalle de operación (HU7) porque el prototipo y el backend ya lo implementan. Las funciones de conveniencia se dejan fuera."));
const HU = [
  ["HU1", "Cotización", "visitante o cliente", "cotizar una operación de Casa de Cambio o Cripto", "conocer cuánto recibiré antes de operar", true, [[
    "GIVEN el usuario se encuentre en la página web,", "WHEN accede al cotizador", "AND selecciona la modalidad Casa de Cambio o Cripto", "AND selecciona la moneda o activo que entrega y el que desea recibir",
    "AND ingresa el monto que desea cambiar", "THEN se muestra la tasa utilizada", "AND se muestra el monto estimado que recibirá", "AND se muestra el tiempo de vigencia de la cotización", "AND se muestra la opción para operar"],
  ["GIVEN el usuario se encuentre utilizando el cotizador,", "WHEN cambia de Casa de Cambio a Cripto o viceversa,", "THEN se actualizan las monedas o activos disponibles", "AND se actualiza la identidad visual correspondiente", "AND el usuario permanece en la misma página"],
  ["GIVEN el usuario se encuentre utilizando el cotizador,", "WHEN ingresa monedas iguales o un monto menor al equivalente de US$ 10", "THEN se muestra un mensaje de error", "AND no se genera la cotización"]]],
  ["HU2", "Registro e identificación", "nuevo cliente", "registrarme y completar mis datos de identificación por pasos", "poder operar dentro de la plataforma", true, [[
    "GIVEN el usuario no tenga una cuenta registrada,", "WHEN selecciona la opción Registrarse", "AND selecciona si es persona natural o empresa", "AND completa los pasos de identificación, contacto y acceso", "AND acepta los términos y confirma el registro",
    "THEN se crea su cuenta", "AND sus datos quedan almacenados (la contraseña solo como hash)", "AND puede iniciar sesión en la plataforma"],
  ["GIVEN ya exista una cuenta con el mismo correo o número de documento,", "WHEN el usuario confirma el registro", "THEN se muestra un mensaje indicando que la cuenta ya existe", "AND no se crea una cuenta nueva"]]],
  ["HU3", "Inicio de sesión", "cliente registrado", "iniciar sesión", "acceder a mis operaciones y continuar el flujo de cambio", true, [[
    "GIVEN el cliente tenga una cuenta registrada,", "WHEN ingresa su correo y contraseña", "AND selecciona Iniciar sesión", "THEN el sistema valida sus credenciales", "AND permite el acceso a las funcionalidades del cliente", "AND muestra el acceso a Nueva operación y Mis operaciones"],
  ["GIVEN el usuario ingrese credenciales incorrectas,", "WHEN selecciona Iniciar sesión", "THEN se muestra el mensaje «Correo o contraseña incorrectos»", "AND no se inicia la sesión"]]],
  ["HU4", "Registrar operación", "cliente", "confirmar una cotización y registrar los datos de la transferencia", "solicitar una operación de cambio", true, [[
    "GIVEN el cliente haya iniciado sesión", "AND tenga una cotización vigente,", "WHEN selecciona Operar ahora", "AND confirma la cotización", "AND selecciona el banco (o red) desde el cual realizará la transferencia", "AND ingresa la cuenta (o billetera) donde desea recibir los fondos",
    "THEN se muestra un resumen de la operación", "AND se muestran los datos de NexoCambio para realizar la transferencia", "AND se habilita el paso para adjuntar el comprobante"],
  ["GIVEN el cliente tenga una cotización vencida,", "WHEN intenta registrar la operación", "THEN se muestra un mensaje indicando que la cotización expiró", "AND se ofrece actualizar la tasa"]]],
  ["HU5", "Adjuntar comprobante", "cliente", "adjuntar el comprobante de la transferencia realizada", "dejar mi operación pendiente de procesamiento", true, [[
    "GIVEN el cliente haya confirmado una operación,", "WHEN carga una imagen o PDF como comprobante", "AND selecciona Confirmar operación", "THEN la operación queda registrada", "AND se almacena el comprobante", "AND la operación queda con estado Pendiente de validación", "AND se muestra un mensaje confirmando el registro"],
  ["GIVEN el cliente esté adjuntando el comprobante,", "WHEN carga un archivo de formato no permitido o mayor a 4 MB", "THEN se muestra un mensaje de error", "AND la operación no cambia de estado"]]],
  ["HU6", "Mis operaciones", "cliente", "consultar mis operaciones y sus estados", "realizar seguimiento a cada solicitud", true, [[
    "GIVEN el cliente no tenga operaciones registradas,", "WHEN ingresa a Mis operaciones", "THEN se muestra un mensaje indicando que todavía no tiene operaciones"],
  ["GIVEN el cliente tenga operaciones registradas,", "WHEN ingresa a Mis operaciones", "THEN se muestra un listado ordenado de la más reciente a la más antigua", "AND para cada operación se muestra fecha, modalidad, monto y estado", "AND el estado puede ser Pendiente de validación, En proceso, Procesada o Rechazada"]]],
  ["HU7", "Detalle de operación", "cliente", "ver el detalle de una operación registrada", "revisar toda la información asociada", true, [[
    "GIVEN el cliente se encuentre en el listado de operaciones,", "WHEN selecciona una operación", "THEN se muestra el detalle completo: fecha, modalidad, montos, tasa, cuentas y estado", "AND se muestra el historial de estados", "AND se muestra el comprobante registrado", "AND, si fue rechazada, se muestra el motivo"]]],
  ["HU8", "Gestión de cuentas bancarias", "cliente", "registrar y reutilizar mis cuentas bancarias", "agilizar futuras operaciones", false, [[
    "GIVEN el cliente haya iniciado sesión,", "WHEN selecciona Registrar cuenta bancaria", "AND ingresa banco, moneda, tipo y número de cuenta", "AND presiona Guardar", "THEN la cuenta queda asociada al cliente", "AND puede reutilizarla en futuras operaciones"]]],
];
HU.forEach(([id, t, como, quiero, para, mvp, escenarios]) => {
  c.push(spacer(140));
  c.push(new Paragraph({ keepNext: true, spacing: { after: 60 }, children: [new TextRun({ text: `Historia de Usuario ${id.slice(2)}: `, bold: true, font: FONT, size: 22 }), new TextRun({ text: t, font: FONT, size: 22 })] }));
  c.push(historia(id, t, como, quiero, para, mvp));
  c.push(new Paragraph({ keepNext: true, spacing: { before: 100, after: 60 }, children: [new TextRun({ text: "Criterios de Aceptación:", bold: true, font: FONT, size: 20 })] }));
  escenarios.forEach((e, i) => { c.push(gherkin(e)); c.push(spacer(60)); });
});
c.push(pie("Lenguaje Gherkin de Desarrollo Guiado por Comportamiento (BDD)"));

c.push(H2("7. Resumen del MVP"));
c.push(tabla([9, 27, 18, 46], ["ID", "Historia", "Clasificación", "Cómo se comprueba"], [
  ["HU1", "Cotización", "**MVP**", "POST /cotizar"], ["HU2", "Registro e identificación", "**MVP**", "POST /registro"], ["HU3", "Inicio de sesión", "**MVP**", "POST /login (JWT)"],
  ["HU4", "Registrar operación", "**MVP**", "POST /operaciones"], ["HU5", "Adjuntar comprobante", "**MVP**", "POST /operaciones/{id}/comprobante → S3"],
  ["HU6", "Mis operaciones", "**MVP**", "GET /operaciones"], ["HU7", "Detalle de operación", "**MVP**", "GET /operaciones/{id}"], ["HU8", "Cuentas bancarias", "Post-MVP", "—"],
], { zebra: true }));
c.push(P("**Flujo que debe funcionar al término del MVP:** el usuario ingresa a la web, cotiza, se registra o inicia sesión, confirma una operación, adjunta un comprobante y luego consulta la operación con su estado.", { before: 140 }));
c.push(P("**Persistencia mínima:** identidad básica del cliente, datos de la operación, su estado con historial y el comprobante."));
c.push(P("**Fuera del MVP:** panel administrativo, score/semáforo de riesgo, integraciones con exchanges (Binance/OKX/Bybit), automatización regulatoria, procesamiento real de fondos, gestión de cuentas bancarias (HU8), app móvil nativa y notificaciones por correo."));

// ================================================================ PARTE B
c.push(H1("PARTE B — DISEÑO DEL MVP (CÓMO)"));
c.push(H2("1. Diseño de FrontEnd (prototipo)"));
c.push(P("El prototipo web responsive fue construido con herramientas de IA a partir de las historias de usuario y criterios de aceptación. Está publicado en **https://claude.ai/artifact/AR38oPWroLtipBBGz6fXRP** y su código fuente está en la carpeta `frontend/` del repositorio. Por defecto funciona en «modo demo» (datos simulados en el navegador); al configurar las URL de la API pasa a consumir los microservicios de AWS (ver C.4)."));
c.push(H3("Prompt utilizado"));
c.push(caja([
  P("Crea una web responsive para **NexoCambio**, una plataforma digital de Casa de Cambio y operaciones Cripto, con estas funcionalidades:", { after: 80, run: { size: 18 } }),
  P("- **Bienvenida:** marca, descripción de servicios, seguridad y confianza, contacto y accesos a registro e inicio de sesión.", { after: 60, run: { size: 18 } }),
  P("- **Cotizador principal** visible desde la primera pantalla, con modalidades Casa de Cambio (identidad azul) y Cripto (identidad verde/oscura), sin redirigir de página. Moneda que entrega y recibe, monto, tasa y monto estimado a recibir.", { after: 60, run: { size: 18 } }),
  P("- **Login y Sign-Up** con correo y contraseña.", { after: 60, run: { size: 18 } }),
  P("- **Registro e identificación** en pasos: persona natural o empresa (datos básicos y del representante), amigable en móvil.", { after: 60, run: { size: 18 } }),
  P("- **Registrar operación:** Operar ahora, confirmar cotización, banco de origen, cuenta de destino, resumen y datos bancarios para transferir.", { after: 60, run: { size: 18 } }),
  P("- **Adjuntar comprobante** (imagen o PDF); la operación queda Pendiente de validación.", { after: 60, run: { size: 18 } }),
  P("- **Mis operaciones** con fecha, modalidad, monto y estado (Pendiente de validación, En proceso, Procesada, Rechazada) y **detalle** de cada una. Mensaje si no hay operaciones.", { after: 60, run: { size: 18 } }),
  P("- Diseño moderno, minimalista y tecnológico; microinteracciones; coherencia entre modalidades diferenciadas por color; adaptable a desktop, tablet y móvil.", { after: 0, run: { size: 18 } }),
], "E3F7E8"));
c.push(H3("Pantallas del prototipo"));
c.push(tabla([22, 12, 66], ["Pantalla", "HU", "Descripción"], [
  ["Inicio + cotizador", "HU1", "Cotizador en el hero con alternancia Casa de Cambio / Cripto, tasa, monto estimado y cuenta regresiva de vigencia."],
  ["Registro", "HU2", "Selección persona/empresa y formulario de 3–4 pasos con validaciones (DNI, RUC, celular, mayoría de edad)."],
  ["Login", "HU3", "Correo y contraseña, con mensaje de error genérico."],
  ["Nueva operación", "HU4, HU5", "3 pasos: datos y cuentas → transferencia (datos de NexoCambio) → carga del comprobante."],
  ["Mis operaciones", "HU6", "Resumen, filtros por estado y listado."],
  ["Detalle de operación", "HU7", "Montos, tasa, cuentas, línea de tiempo de estados y comprobante."],
], { zebra: true }));
c.push(spacer(120));
c.push(img(SH + "01_home_casa.png", 560, 350)); c.push(pie("Figura B.1 — Inicio con cotizador, modalidad Casa de Cambio (identidad azul)."));
c.push(img(SH + "02_home_cripto.png", 560, 350)); c.push(pie("Figura B.2 — Mismo cotizador en modalidad Cripto (identidad verde/oscura), sin cambiar de página."));
c.push(img(SH + "07_operar_paso1.png", 560, 394)); c.push(pie("Figura B.3 — Nueva operación: confirmación de la cotización con tasa vigente."));
c.push(img(SH + "05_mis_operaciones.png", 560, 333)); c.push(pie("Figura B.4 — Mis operaciones con los cuatro estados."));
c.push(img(SH + "06_detalle.png", 560, 306)); c.push(pie("Figura B.5 — Detalle de operación con línea de tiempo de estados."));
c.push(new Table({ width: { size: CW, type: WidthType.DXA }, columnWidths: [CW / 2, CW / 2], rows: [new TableRow({ children: [
  new TableCell({ width: { size: CW / 2, type: WidthType.DXA }, borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } }, children: [img(SH + "08_movil_home.png", 190, 411)] }),
  new TableCell({ width: { size: CW / 2, type: WidthType.DXA }, borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } }, children: [img(SH + "09_movil_registro.png", 190, 411)] })] })] }));
c.push(pie("Figura B.6 — Versión móvil: inicio y registro por pasos."));

c.push(H2("2. Diseño de BackEnd (microservicios)"));
c.push(P("El backend se compone de **tres microservicios independientes** en Python 3.12 sobre AWS Lambda, expuestos mediante un único Amazon API Gateway (HTTP API). **Cada microservicio tiene su propia base de datos**; ninguno accede a las tablas de otro. Las utilidades transversales (JWT, hash de contraseñas, respuestas HTTP) se comparten mediante una Lambda Layer."));
c.push(tabla([22, 28, 50], ["Microservicio", "Implementación", "Base de datos propia"], [
  ["**Cotizaciones**", "AWS Lambda · Python 3.12 (256 MB)", "DynamoDB: `nexo-tasas` y `nexo-cotizaciones`"],
  ["**Clientes / Auth**", "AWS Lambda · Python 3.12 (512 MB)", "DynamoDB: `nexo-clientes`"],
  ["**Operaciones**", "AWS Lambda · Python 3.12 (512 MB)", "DynamoDB: `nexo-operaciones` + S3 (comprobantes)"],
], { firstColFill: true }));

c.push(H3("Microservicio 1 — Cotizaciones"));
c.push(P("Calcula y registra la cotización de una operación (Casa de Cambio o Cripto) con vigencia de 5 minutos. Obtiene tasas de referencia de fuentes públicas y las guarda en caché en DynamoDB; si la fuente no responde usa la última tasa guardada o valores referenciales, por lo que el servicio no se cae. Aplica un margen (0.45 % divisas, 1.2 % cripto) que baja 40 % desde US$ 5,000 (tasa preferencial)."));
c.push(tabla([10, 22, 12, 56], ["Método", "Endpoint", "Acceso", "Descripción"], [
  ["POST", "/cotizar", "Público", "Recibe modalidad, moneda origen y destino y monto; devuelve tasa, monto estimado y fecha de expiración."],
  ["Invoke", "acción `obtener`", "Interno", "Lambda→Lambda: entrega una cotización a Operaciones para validarla (no se expone en internet)."],
]));
c.push(H3("Microservicio 2 — Clientes y autenticación"));
c.push(P("Registra clientes (persona natural o empresa con representante), valida credenciales y emite un JWT HS256 de 2 horas. Las contraseñas se guardan con PBKDF2-HMAC-SHA256 (200,000 iteraciones y sal aleatoria), nunca en texto plano. El registro garantiza correo y documento únicos con una transacción de DynamoDB."));
c.push(tabla([10, 28, 14, 48], ["Método", "Endpoint", "Acceso", "Descripción"], [
  ["POST", "/registro", "Público", "Crea el cliente (validaciones de DNI/CE/pasaporte/RUC, celular, edad y contraseña)."],
  ["POST", "/login", "Público", "Valida credenciales y devuelve token y perfil. Mismo mensaje de error si el correo no existe."],
  ["GET", "/clientes/{id_cliente}", "JWT", "Perfil básico; solo el propio cliente puede consultarlo."],
]));
c.push(H3("Microservicio 3 — Operaciones"));
c.push(P("Registra la operación a partir de una cotización vigente, guarda el comprobante en S3, mantiene el estado con su historial y lista/consulta las operaciones del cliente autenticado. **No confía en la tasa ni en los montos que envía el navegador:** consulta la cotización a Cotizaciones y usa esos valores; además, una cotización solo puede usarse una vez."));
c.push(tabla([10, 34, 12, 44], ["Método", "Endpoint", "Acceso", "Descripción"], [
  ["POST", "/operaciones", "JWT", "Registra la operación (estado interno «Pendiente de comprobante»)."],
  ["POST", "/operaciones/{id}/comprobante", "JWT", "Adjunta imagen/PDF (máx. 4 MB); pasa a «Pendiente de validación»."],
  ["GET", "/operaciones", "JWT", "Lista las operaciones del cliente, de la más reciente a la más antigua."],
  ["GET", "/operaciones/{id}", "JWT", "Detalle con historial y URL temporal (15 min) del comprobante."],
  ["PATCH", "/operaciones/{id}/estado", "x-admin-key", "Back-office simulado: En proceso → Procesada / Rechazada (con motivo)."],
]));
c.push(P("**Estados:** [Pendiente de comprobante, interno] → Pendiente de validación → En proceso → Procesada | Rechazada. Las transiciones se validan en el servidor.", { before: 100 }));

c.push(H3("Diseño de las bases de datos (NoSQL — Amazon DynamoDB, modo bajo demanda)"));
c.push(tabla([19, 22, 59], ["Tabla", "Clave", "Atributos y observaciones"], [
  ["`nexo-tasas`", "PK `moneda` (S)", "`usd` (precio de 1 unidad en USD), `fuente`, `actualizado` (epoch). Un ítem `_meta` evita reintentar la fuente externa en cada request."],
  ["`nexo-cotizaciones`", "PK `id_cotizacion` (S)", "`modalidad`, `moneda_origen/destino`, `monto_origen/destino`, `tasa`, `tasa_preferencial`, `fuente_tasas`, `fecha_cotizacion`, `fecha_expiracion`. **TTL** (`ttl`): DynamoDB elimina la cotización 1 h después de vencer."],
  ["`nexo-clientes`", "PK `pk` (S)", "`CLI#<id>`: perfil (tipo, nombre, documento, correo, teléfono, `password_hash`, representante, fecha). `EMAIL#<correo>` y `DOC#<tipo>#<número>`: ítems de unicidad que apuntan al `id_cliente`; se escriben con el perfil en **una transacción** con `attribute_not_exists`."],
  ["`nexo-operaciones`", ["PK `id_operacion` (S)", "GSI `cliente-fecha-index`: `id_cliente` + `fecha_operacion`"], "`id_cliente`, `id_cotizacion`, `modalidad`, monedas, montos, `tasa`, `estado`, `historial` [{estado, fecha}], `origen`, `destino`, `ruta_comprobante`, `comprobante_nombre/tipo/tamano`, `numero_transferencia`, `motivo_rechazo`. El `id_operacion` deriva del `id_cotizacion` (una cotización = una operación)."],
  ["S3 `comprobantes`", "clave `comprobantes/<id_cliente>/<id_operacion>/<archivo>`", "Bucket privado, cifrado AES-256, solo HTTPS; acceso mediante URL firmada temporal."],
], { firstColFill: true, size: 17 }));
c.push(H3("Patrones de acceso"));
c.push(tabla([40, 60], ["Caso de uso", "Operación en DynamoDB"], [
  ["Login por correo", "GetItem `EMAIL#correo` → GetItem `CLI#id`"],
  ["Registro con unicidad", "TransactWriteItems (3 Put con `attribute_not_exists`)"],
  ["Mis operaciones", "Query al GSI `cliente-fecha-index` (orden descendente, excluye borradores)"],
  ["Detalle de operación", "GetItem por `id_operacion` + verificación de propietario (404 si no es suyo)"],
  ["Validar cotización", "GetItem por `id_cotizacion` (vía Lambda Invoke desde Operaciones)"],
], { zebra: true }));
c.push(H3("Decisiones de seguridad y diseño"));
c.push(...bullets([
  "**Autenticación propia con JWT** (HS256, secreto por variable de entorno) porque Cognito puede no estar disponible en el Learner Lab. Para producción se recomienda Cognito y guardar secretos en Secrets Manager.",
  "**Aislamiento entre clientes:** el `id_cliente` sale del token, nunca del cuerpo de la petición; consultar la operación de otro cliente devuelve 404.",
  "**Comprobantes:** se valida el tipo real del archivo (firma JPG/PNG/WEBP/PDF), el tamaño y se sanea el nombre; el bucket nunca es público.",
  "**Robustez:** errores 4xx con mensaje claro en español y código; los errores inesperados devuelven 500 sin detalles internos; el API Gateway limita la tasa de solicitudes.",
  "**Monitoreo:** logs estructurados en CloudWatch (sin datos sensibles), alarmas de errores por Lambda y de 5xx de la API, con aviso por SNS.",
]));

// ============ sección 2 (horizontal): diagrama
const d = [];
d.push(H1s("3. Diagrama de Arquitectura de Solución en AWS"));
d.push(img("docs/arquitectura_nexocambio.png", 900, 551));
d.push(pie("Figura B.7 — Arquitectura serverless de NexoCambio (AWS Academy · us-east-1)."));

// ============ sección 3
const e = [];
e.push(P("**Flujo de una operación:**", { after: 60 }));
e.push(...numbered([
  "El cliente abre el sitio: el navegador descarga el frontend estático desde **S3**.",
  "El frontend llama a **API Gateway** por HTTPS (JSON; el JWT viaja en la cabecera `Authorization`).",
  "API Gateway enruta cada ruta a su **Lambda**.",
  "**Cotizaciones** lee/actualiza tasas y guarda la cotización en DynamoDB (vigencia 5 min).",
  "**Clientes** registra/valida al cliente y emite el JWT.",
  "**Operaciones** valida la cotización con Cotizaciones (Lambda Invoke), registra la operación y guarda el comprobante en S3.",
  "**CloudWatch** recibe logs y métricas de todo el flujo; SNS avisa cuando una alarma se activa.",
]));
e.push(H2("4. Región de AWS"));
e.push(P("Se elige **us-east-1 (N. Virginia)**. En AWS Academy solo están habilitadas us-east-1 y us-west-2; us-east-1 es la región con más servicios disponibles y la que usan por defecto las guías y plantillas del laboratorio. Para una operación real en Perú convendría evaluar **sa-east-1 (São Paulo)** por menor latencia, y revisar con asesoría legal los requisitos de protección de datos personales para el almacenamiento fuera del país."));

e.push(H2("5. Costos mensuales en AWS"));
e.push(P("Estimación para us-east-1 **sin considerar la capa gratuita** (escenario conservador). Los supuestos y precios de referencia están en `docs/costos.py`; **deben validarse en la calculadora oficial (https://calculator.aws)** antes de entregar."));
const esc = costos.escenarios, nombres = Object.keys(esc), serv = Object.keys(esc[nombres[0]].detalle);
e.push(tabla([34, 22, 22, 22], ["Servicio", ...nombres.map((n) => `${n} (${(esc[n].requests / 1000).toLocaleString("en-US")} mil req/mes)`)],
  [...serv.map((s) => [s, ...nombres.map((n) => usd(esc[n].detalle[s]))]), ["**Total mensual**", ...nombres.map((n) => `**${usd(esc[n].total)}**`)]], { firstColFill: true }));
e.push(spacer(80));
e.push(P("**Supuestos:** mezcla de tráfico por cada 100 llamadas: 70 cotizaciones, 4 inicios de sesión, 1 registro, 5 operaciones nuevas, 5 comprobantes (400 KB c/u), 10 listados y 5 detalles. Lambda: 256–512 MB y 120–500 ms según la función. DynamoDB bajo demanda. Región us-east-1."));
const m = esc[nombres[1]].metricas;
e.push(P(`**Datos para replicar el escenario «Piloto» en la calculadora:** API Gateway HTTP = 300,000 solicitudes; Lambda = ${Math.round(m.lambda_req).toLocaleString("en-US")} invocaciones y ${Math.round(m.gbs).toLocaleString("en-US")} GB-s; DynamoDB = ${Math.round(m.wru).toLocaleString("en-US")} unidades de escritura y ${Math.round(m.rru).toLocaleString("en-US")} de lectura; S3 = ${m.s3_gb.toFixed(2)} GB de comprobantes; CloudWatch = ${m.logs_gb.toFixed(3)} GB de logs y 4 alarmas.`));
e.push(P("**Comparación:** la misma solución con contenedores 24×7 (ECS Fargate con 6 tareas pequeñas, Application Load Balancer y RDS PostgreSQL db.t3.micro) costaría del orden de **" + usd(costos.alternativa_total) + " al mes** aun sin tráfico. La opción serverless paga solo por uso, escala automáticamente y encaja con el presupuesto limitado del Learner Lab."));
e.push(nota("Enlace de la estimación en AWS Pricing Calculator: [pegar enlace]     ·     [Insertar captura de la calculadora]"));

// ================================================================ PARTE C
e.push(H1("PARTE C — IMPLEMENTACIÓN DEL MVP EN AWS"));
e.push(H2("1. Catálogo de APIs"));
e.push(P("**URL base:** `https://<api-id>.execute-api.us-east-1.amazonaws.com/v1` (salida `ApiUrl` del despliegue). Formato JSON. Rutas protegidas: cabecera `Authorization: Bearer <token>`. Los errores devuelven `{\"mensaje\": \"...\", \"codigo\": \"...\"}`."));
e.push(tabla([9, 26, 16, 14, 35], ["Método", "Ruta", "Servicio", "Acceso", "Códigos de respuesta"], [
  ["POST", "/cotizar", "Cotizaciones", "Público", "201 · 400 · 422"],
  ["POST", "/registro", "Clientes", "Público", "201 · 400 · 409 (correo/documento duplicado) · 422"],
  ["POST", "/login", "Clientes", "Público", "200 · 400 · 401"],
  ["GET", "/clientes/{id_cliente}", "Clientes", "JWT", "200 · 401 · 403 · 404"],
  ["POST", "/operaciones", "Operaciones", "JWT", "201 · 400 · 401 · 404 · 409 (vencida/usada) · 422 · 502"],
  ["POST", "/operaciones/{id}/comprobante", "Operaciones", "JWT", "200 · 400 · 401 · 404 · 409 · 413 · 422"],
  ["GET", "/operaciones", "Operaciones", "JWT", "200 · 401"],
  ["GET", "/operaciones/{id}", "Operaciones", "JWT", "200 · 401 · 404"],
  ["PATCH", "/operaciones/{id}/estado", "Operaciones", "x-admin-key", "200 · 400 · 403 · 404 · 409"],
], { size: 17, zebra: true }));
e.push(H3("POST /cotizar"));
e.push(codigo(["// Solicitud", "{ \"modalidad\": \"casa\", \"moneda_origen\": \"PEN\", \"moneda_destino\": \"USD\", \"monto_origen\": 1000 }", "// Respuesta 201", "{ \"id_cotizacion\": \"COT-SXC7PXG3\", \"modalidad\": \"casa\", \"moneda_origen\": \"PEN\",", "  \"moneda_destino\": \"USD\", \"monto_origen\": 1000, \"tasa\": 0.2940707, \"tasa_preferencial\": false,", "  \"monto_destino\": 294.07, \"fuente_tasas\": \"en_vivo\",", "  \"fecha_cotizacion\": \"2026-09-20T17:55:20.990Z\", \"fecha_expiracion\": \"2026-09-20T18:00:20.000Z\" }"]));
e.push(H3("POST /registro  ·  POST /login"));
e.push(codigo(["// Registro (persona natural)", "{ \"tipo_cliente\": \"persona\", \"nombres\": \"Lucía\", \"apellidos\": \"Ramírez Torres\", \"tipo_documento\": \"DNI\",", "  \"numero_documento\": \"45879632\", \"fecha_nacimiento\": \"1994-05-10\", \"telefono\": \"987654321\",", "  \"ocupacion\": \"Dependiente\", \"pep\": false, \"correo\": \"lucia@correo.com\", \"password\": \"Clave1234\" }", "// Respuesta 201:  { \"id_cliente\": \"CLI-2VAZFB\", \"mensaje\": \"Cliente registrado\" }", "", "// Login   { \"correo\": \"lucia@correo.com\", \"password\": \"Clave1234\" }", "// Respuesta 200:  { \"token\": \"<jwt>\", \"expira_en\": 7200, \"cliente\": { \"id_cliente\": \"CLI-2VAZFB\", \"nombre\": \"Lucía Ramírez Torres\", ... } }"]));
e.push(P("Para empresas: `tipo_cliente: \"empresa\"`, `razon_social`, `tipo_documento: \"RUC\"`, `actividad` y `representante {nombre, tipo_documento, numero_documento, cargo}`.", { before: 80 }));
e.push(H3("POST /operaciones  ·  POST /operaciones/{id}/comprobante"));
e.push(codigo(["// Registrar operación (el servidor toma tasa y montos de la cotización)", "{ \"id_cotizacion\": \"COT-SXC7PXG3\",", "  \"origen\":  { \"tipo\": \"banco\", \"banco\": \"BCP\" },", "  \"destino\": { \"tipo\": \"banco\", \"banco\": \"Interbank\", \"tipo_cuenta\": \"Ahorros\",", "              \"numero\": \"8983141592653\", \"titular\": \"Lucía Ramírez Torres\" } }", "// Respuesta 201:  { \"id_operacion\": \"NX-SXC7PXG3\", \"estado\": \"Pendiente de comprobante\", ... }", "", "// Adjuntar comprobante", "{ \"nombre_archivo\": \"transferencia.png\", \"content_type\": \"image/png\",", "  \"contenido_base64\": \"iVBORw0KGgo...\", \"numero_transferencia\": \"778899\" }", "// Respuesta 200:  { \"id_operacion\": \"NX-SXC7PXG3\", \"estado\": \"Pendiente de validación\",", "//                  \"ruta_comprobante\": \"s3://nexo-dev-comprobantes-<cuenta>-us-east-1/comprobantes/...\" }"]));
e.push(H3("GET /operaciones  ·  GET /operaciones/{id}  ·  PATCH /operaciones/{id}/estado"));
e.push(codigo(["// GET /operaciones → 200", "{ \"operaciones\": [ { \"id_operacion\": \"NX-SXC7PXG3\", \"fecha_operacion\": \"...\", \"modalidad\": \"casa\",", "    \"monto_origen\": 1000, \"monto_destino\": 294.07, \"estado\": \"Pendiente de validación\" } ], \"total\": 1 }", "", "// GET /operaciones/{id} → 200  (agrega historial y URL temporal)", "{ ..., \"historial\": [ { \"estado\": \"Pendiente de validación\", \"fecha\": \"...\" } ],", "  \"comprobante_url\": \"https://<bucket>.s3.amazonaws.com/...&X-Amz-Signature=...\" }", "", "// PATCH (cabecera x-admin-key)   { \"estado\": \"En proceso\" }   |   { \"estado\": \"Rechazada\", \"motivo_rechazo\": \"...\" }"]));

e.push(H2("2. Implementación y despliegue"));
e.push(P("Todo el código está en un único repositorio: **[https://github.com/<organización>/nexocambio]**."));
e.push(codigo(["nexocambio/", "├─ template.yaml            CloudFormation: tablas, buckets, Lambdas, API, alarmas", "├─ services/", "│   ├─ cotizaciones/app.py  Microservicio 1", "│   ├─ clientes/app.py      Microservicio 2", "│   └─ operaciones/app.py   Microservicio 3", "├─ layer/python/nexo_common.py   Capa compartida (JWT, hash, respuestas)", "├─ frontend/index.html      Prototipo conectable a la API (CONFIG.API)", "├─ tests/                   54 pruebas automáticas (pytest + moto)", "├─ postman/                 Colección con 20 requests y 27 verificaciones", "├─ scripts/                 deploy.sh · destroy.sh · servidor_local.py · configurar_front.py", "└─ docs/                    arquitectura, costos y diagrama"]));
e.push(H3("Despliegue en AWS Academy (AWS CloudShell)"));
e.push(...numbered([
  "Inicie el Learner Lab y abra **AWS CloudShell** en la región us-east-1.",
  "Clone el repositorio: `git clone https://github.com/<organización>/nexocambio && cd nexocambio`.",
  "Ejecute `ALERT_EMAIL=<su correo> ./scripts/deploy.sh`. El script empaqueta las funciones, crea el stack de CloudFormation (con el rol `LabRole`), publica el frontend en S3 y muestra la **URL de la API** y del **sitio web**.",
  "Confirme la suscripción SNS que llega al correo para recibir alertas.",
  "Al terminar: `./scripts/destroy.sh` elimina todo y evita consumir el presupuesto del laboratorio.",
]));
e.push(H3("Verificación realizada durante el desarrollo"));
e.push(...bullets([
  "**54 pruebas automáticas** (pytest + moto) sobre los tres microservicios: validaciones, seguridad, aislamiento entre clientes, unicidad, expiración de cotizaciones y flujo completo.",
  "**Colección de Postman** ejecutada con Newman contra el servidor local: 20 requests, 27 verificaciones, 0 fallidas.",
  "**Prototipo real** conectado al backend local: registro, login, cotización, operación, comprobante, listado y detalle.",
  "La plantilla CloudFormation pasa `cfn-lint`. **Falta ejecutar el despliegue en la cuenta del Learner Lab del equipo** y registrar las evidencias de la sección C.3.",
]));
e.push(P("**Servidor local para ensayar sin AWS:** `pip install -r requirements-dev.txt && python scripts/servidor_local.py` levanta la API en `http://localhost:8787` con un cliente demo (`demo@nexocambio.pe` / `Demo1234`).", { before: 80 }));

e.push(H2("3. Evidencias de uso (Postman y AWS)"));
e.push(P("Importe `postman/NexoCambio.postman_collection.json`, cambie la variable `baseUrl` por la `ApiUrl` del despliegue y `adminKey` por la clave que imprime `deploy.sh`, y ejecute la colección completa (Runner). Pegue aquí las capturas:"));
e.push(tabla([6, 46, 48], ["#", "Evidencia", "Captura"], [
  ["1", "Postman — POST /cotizar (201) para Casa de Cambio y Cripto", "[Insertar captura]"],
  ["2", "Postman — POST /registro y POST /login (JWT)", "[Insertar captura]"],
  ["3", "Postman — POST /operaciones, /comprobante, GET /operaciones y detalle", "[Insertar captura]"],
  ["4", "Postman — Runner con todas las verificaciones en verde", "[Insertar captura]"],
  ["5", "Consola AWS — Lambda (3 funciones) y API Gateway (rutas)", "[Insertar captura]"],
  ["6", "Consola AWS — DynamoDB (ítems en las 4 tablas) y S3 (comprobante subido)", "[Insertar captura]"],
  ["7", "Consola AWS — CloudWatch (logs y alarmas)", "[Insertar captura]"],
  ["8", "Frontend en S3 consumiendo la API (insignia «API conectada»)", "[Insertar captura]"],
], { zebra: true }));

e.push(H2("4. FrontEnd conectado a la API (opcional — puntaje adicional)"));
e.push(P("El prototipo consume **los tres microservicios**: el cotizador usa `POST /cotizar`; registro y login usan `/registro` y `/login`; y el flujo de operación usa `/operaciones`, `/comprobante`, el listado y el detalle. `deploy.sh` inyecta la URL de la API en `CONFIG.API` del `index.html` y lo publica en el bucket S3 de sitio web. Cuando la API responde, el cotizador muestra la insignia «API conectada»."));
e.push(nota("Importante: la versión publicada como artifact no puede llamar a la API de AWS por restricciones de seguridad de esa plataforma; para la demostración se debe usar el sitio alojado en S3 (URL «Sitio web» del despliegue) o el servidor local."));

e.push(H1("GUÍA PARA LA EXPOSICIÓN (miércoles 07-Oct, 19:00 h)"));
e.push(tabla([12, 46, 12, 30], ["Tiempo", "Contenido", "Parte", "Responsable"], [
  ["2 min", "Problema, NexoCambio y benchmark (qué nos diferencia)", "A", "[Integrante]"],
  ["1 min", "Historias de usuario y selección del MVP", "A", "[Integrante]"],
  ["2 min", "Arquitectura, región y decisiones (microservicios, una BD por servicio, seguridad)", "B", "[Integrante]"],
  ["3 min", "**Demo en vivo:** sitio en S3 → cotizar → registrarse → operar → comprobante → estado; luego Postman y consola de AWS", "C", "[Integrante]"],
  ["1 min", "Costos: escenarios y comparación con contenedores", "B", "[Integrante]"],
  ["1 min", "Aprendizajes, limitaciones y siguientes pasos", "—", "[Integrante]"],
], { zebra: true }));
e.push(P("**Sugerencia:** antes de exponer, deje el stack desplegado, ejecute la colección de Postman una vez para verificar y tenga a mano una cuenta ya registrada con operaciones en distintos estados (use `PATCH …/estado` para simularlo).", { before: 120 }));
e.push(H3("Limitaciones que conviene mencionar"));
e.push(...bullets([
  "No se procesan fondos reales; las cuentas y direcciones de NexoCambio son ficticias.",
  "La autenticación es propia (JWT); en producción se usaría Cognito y Secrets Manager.",
  "El sitio en S3 se sirve por HTTP; con CloudFront (si el laboratorio lo permite) se obtiene HTTPS y caché.",
  "No hay panel de back-office: los estados se cambian con un endpoint protegido.",
]));

// ================================================================ documento
const header = new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "BFC7D5", space: 4 } },
  children: [new TextRun({ text: "NexoCambio · Proyecto Parcial · Cloud Computing (CDIA V5) · UTEC Posgrado", font: FONT, size: 16, color: "777777" })] })] });
const footer = new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Página ", font: FONT, size: 16, color: "777777" }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: "777777" })] })] });
const A4 = { width: 11906, height: 16838 };
const doc = new Document({
  creator: "Equipo NexoCambio", title: "NexoCambio — Proyecto Parcial de Cloud Computing",
  styles: { default: { document: { run: { font: FONT, size: 21 } } }, paragraphStyles: [
    { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 34, bold: true, font: FONT, color: NAVY }, paragraph: { spacing: { before: 120, after: 200 }, outlineLevel: 0,
      border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: "FF8C00", space: 6 } } } },
    { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 26, bold: true, font: FONT, color: BLUE }, paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 1 } },
    { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 22, bold: true, font: FONT, color: NAVY }, paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 2 } } ] },
  numbering: { config: [
    { reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
    { reference: "num", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 360 } } } }] } ] },
  sections: [
    { properties: { titlePage: true, page: { size: A4, margin: { top: 1440, right: 1440, bottom: 1300, left: 1440 } } }, headers: { default: header, first: new Header({ children: [new Paragraph({ children: [] })] }) }, footers: { default: footer, first: new Footer({ children: [new Paragraph({ children: [] })] }) }, children: c },
    { properties: { page: { size: { ...A4, orientation: PageOrientation.LANDSCAPE }, margin: { top: 1000, right: 720, bottom: 700, left: 720 } } }, headers: { default: header }, footers: { default: footer }, children: d },
    { properties: { page: { size: A4, margin: { top: 1440, right: 1440, bottom: 1300, left: 1440 } } }, headers: { default: header }, footers: { default: footer }, children: e },
  ],
});
Packer.toBuffer(doc).then((b) => { fs.writeFileSync("docs/NexoCambio_ProyectoParcial_Final.docx", b); console.log("docx ok", b.length); });
