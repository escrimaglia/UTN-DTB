// npm run inicializar — Parte 1: despliega los contratos, asigna los roles y emite los fondos.
// Guarda las direcciones en despliegue.json para que las campañas usen esos mismos contratos.
const { network } = require("hardhat");
const { resultado } = require("./lib/comun");
const { inicializar, guardar } = require("./lib/inicializacion");

async function main() {
  console.log(`Red: ${network.name}`);
  const ctx = await inicializar();
  await guardar(ctx);
  await resultado();
}
main().catch((e) => { console.error(e); process.exitCode = 1; });
