// npm run demo — Ensayo completo: las tres partes seguidas, en la red en memoria (no hace falta nodo).
// En la clase se usan los tres comandos por separado, contra el nodo local:
//   npm run node               (terminal 1)
//   npm run inicializar        Parte 1: contratos, roles y fondos
//   npm run campania:normal    Parte 2: canje con índice 300 (la póliza no se ejecuta)
//   npm run campania:sequia    Parte 3: canje con índice 850 (la póliza se ejecuta)
const { network } = require("hardhat");
const { resultado } = require("./lib/comun");
const { inicializar } = require("./lib/inicializacion");
const { campania } = require("./lib/campania");

async function main() {
  console.log(`Red: ${network.name}`);
  const ctx = await inicializar();
  await campania(ctx, 300, "AÑO NORMAL (índice 300)");
  await campania(ctx, 850, "SEQUÍA SEVERA (índice 850)");
  await resultado();
}
main().catch((e) => { console.error(e); process.exitCode = 1; });
