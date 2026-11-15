// npm run campania:normal — Parte 2: campaña completa de un canje en un AÑO NORMAL.
// El oráculo informa un índice de 300 (debajo del umbral de 600): el contrato no activa la póliza.
const { network } = require("hardhat");
const { resultado } = require("./lib/comun");
const { cargar } = require("./lib/inicializacion");
const { campania } = require("./lib/campania");

async function main() {
  console.log(`Red: ${network.name}`);
  await campania(await cargar(), 300, "AÑO NORMAL (índice 300)");
  await resultado();
}
main().catch((e) => { console.error(e); process.exitCode = 1; });
