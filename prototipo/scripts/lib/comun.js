// Funciones comunes de los scripts de demostración: formato de la salida, verificaciones
// y lectura del error personalizado con que el contrato rechaza una operación.
const { ethers, network } = require("hardhat");
const readline = require("readline");

const DIA = 24n * 60n * 60n;
const ESTADOS = ["Solicitado", "Aprobado", "Asegurado", "Vigente", "Siniestrado", "Indemnizado",
                 "EnCosecha", "Saldado", "Rechazado", "EnMora"];
const h = (s) => ethers.id(s); // hash (bytes32) de un documento
const pesos = (c) => "$ " + (Number(c) / 100).toLocaleString("es-AR");
const t = (kg) => (Number(kg) / 1000).toLocaleString("es-AR") + " t";

const cuenta = { ok: 0, mal: 0 };

const linea = (c = "-") => console.log(c.repeat(78));
function parte(texto) { console.log(""); linea("="); console.log(texto); linea("="); }
// Pausa entre casos: solo en los comandos de la clase (nodo local) y en una terminal interactiva.
// "npm run demo" (red en memoria) corre de corrido, igual que si la salida se guarda en un archivo.
let hayCasoPrevio = false;
async function pausa() {
  if (network.name !== "localhost" || !process.stdin.isTTY || !process.stdout.isTTY) return;
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  await new Promise((r) => rl.question("\n  … Enter para continuar ", () => { rl.close(); r(); }));
}
async function titulo(n, texto) {
  if (hayCasoPrevio) await pausa();
  hayCasoPrevio = true;
  console.log(""); linea(); console.log(`CASO ${n}. ${texto}`); linea();
}
function info(etiqueta, valor) { console.log(`  ${etiqueta.padEnd(28)} ${valor}`); }
function paso(operacion, ejecuta, esperado) {
  info("Operación:", operacion);
  info("Ejecuta:", ejecuta);
  info("Esperado:", esperado);
}
function verificar(descripcion, condicion) {
  console.log(`  ${condicion ? "[OK]   " : "[FALLA]"} ${descripcion}`);
  condicion ? cuenta.ok++ : cuenta.mal++;
}
async function resultado() {
  await pausa();
  console.log("");
  linea();
  console.log(`RESULTADO: ${cuenta.ok} verificaciones correctas, ${cuenta.mal} fallidas.`);
  linea();
  if (cuenta.mal) process.exitCode = 1;
}
async function estado(canje, id) { return ESTADOS[Number((await canje.verCanje(id)).estado)]; }

// Ejecuta una operación que DEBE ser rechazada y muestra el error personalizado que devuelve el contrato
async function debeFallar(canje, operacion, errorEsperado) {
  try {
    await (await operacion()).wait();
    verificar(`se esperaba el rechazo ${errorEsperado}, pero la operación se ejecutó`, false);
  } catch (e) {
    // En la red en memoria el error llega decodificado; por JSON-RPC (nodo local) se busca el selector en el objeto del error
    let nombre = e.errorName, args = e.errorArgs;
    const visto = new Set();
    const buscar = (o) => {
      if (nombre || !o || typeof o !== "object" || visto.has(o)) return;
      visto.add(o);
      for (const v of Object.values(o)) {
        if (typeof v === "string" && /^0x[0-9a-fA-F]{8}/.test(v)) {
          try { const p = canje.interface.parseError(v); if (p) { nombre = p.name; args = p.args; return; } } catch {}
        } else buscar(v);
      }
    };
    buscar(e);
    if (!nombre) { const m = /custom error '(\w+)\(([^)]*)\)'/.exec(String(e.message)); if (m) { nombre = m[1]; args = m[2].split(", ").filter(Boolean); } }
    info("Revertida con:", `${nombre}(${args ? [...args].map(String).join(", ") : ""})`);
    verificar(`la transacción se revirtió con ${errorEsperado}`, nombre === errorEsperado);
  }
}

module.exports = { DIA, ESTADOS, h, pesos, t, linea, parte, titulo, info, paso, verificar, resultado, estado, debeFallar };
