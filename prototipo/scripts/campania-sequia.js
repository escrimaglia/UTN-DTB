// npm run campania:sequia — Parte 3: campaña completa de un canje con SEQUÍA SEVERA.
// El oráculo informa un índice de 850 (supera el umbral de 800): el contrato ejecuta la póliza al 100 %.
const { network } = require("hardhat");
const { resultado } = require("./lib/comun");
const { cargar } = require("./lib/inicializacion");
const { campania } = require("./lib/campania");

async function main() {
  console.log(`Red: ${network.name}`);
  await campania(await cargar(), 850, "SEQUÍA SEVERA (índice 850)");
  await resultado();
}
main().catch((e) => { console.error(e); process.exitCode = 1; });
