// Parte 1 de la demostración: despliegue de los contratos, roles y fondos.
// Las direcciones se guardan en despliegue.json para que las campañas usen los mismos contratos.
const fs = require("fs");
const path = require("path");
const { ethers, network } = require("hardhat");
const { pesos, parte, titulo, info, paso, verificar } = require("./comun");

const ARCHIVO = path.join(__dirname, "..", "..", "despliegue.json");

async function cuentas() {
  const [admin, banco, productor, agronomia, aseguradora, acopio, conae, smn, intruso] = await ethers.getSigners();
  return { admin, banco, productor, agronomia, aseguradora, acopio, conae, smn, intruso };
}

async function inicializar() {
  const s = await cuentas();
  parte("PARTE 1. INICIALIZACIÓN: despliegue de los contratos, roles y fondos");

  await titulo(1, "Despliegue de los contratos");
  paso("desplegar PesoToken(banco) y ECanjeProtegido(token, admin)", "admin del consorcio",
       "dos contratos con su dirección en la red");
  const token = await ethers.deployContract("PesoToken", [s.banco.address]);
  const canje = await ethers.deployContract("ECanjeProtegido", [await token.getAddress(), s.admin.address]);
  await token.waitForDeployment(); await canje.waitForDeployment();
  info("PesoToken (ARSt):", await token.getAddress());
  info("ECanjeProtegido:", await canje.getAddress());
  verificar("los dos contratos tienen código en la red",
            (await ethers.provider.getCode(await canje.getAddress())) !== "0x" &&
            (await ethers.provider.getCode(await token.getAddress())) !== "0x");

  await titulo(2, "Asignación de roles a cada participante");
  paso("grantRole(rol, cuenta) para cada participante", "admin del consorcio", "seis cuentas con rol; el intruso sin rol");
  const roles = [["PRODUCTOR_ROLE", s.productor, "productor"], ["AGRONOMIA_ROLE", s.agronomia, "agronomía"],
                 ["ASEGURADORA_ROLE", s.aseguradora, "aseguradora"], ["ACOPIO_ROLE", s.acopio, "acopio"],
                 ["ORACULO_ROLE", s.conae, "oráculo primario"], ["ORACULO_ROLE", s.smn, "oráculo alternativo"]];
  for (const [rol, c, nombre] of roles) {
    await (await canje.connect(s.admin).grantRole(await canje[rol](), c.address)).wait();
    info(`Rol ${nombre}:`, c.address);
  }
  info("Cuenta sin rol:", `${s.intruso.address} (intruso)`);
  let todos = true;
  for (const [rol, c] of roles) todos = todos && (await canje.hasRole(await canje[rol](), c.address));
  verificar("cada participante tiene su rol", todos);

  await titulo(3, "Fondos: el banco emite pesos tokenizados para la aseguradora");
  paso("emitir(aseguradora, $ 200 M) y approve(contrato)", "banco y aseguradora",
       "aseguradora con $ 200 M; el contrato autorizado a debitar");
  await (await token.connect(s.banco).emitir(s.aseguradora.address, 20_000_000_000n)).wait();
  await (await token.connect(s.aseguradora).approve(await canje.getAddress(), ethers.MaxUint256)).wait();
  info("Obtenido:", `saldo de la aseguradora ${pesos(await token.balanceOf(s.aseguradora.address))}`);
  verificar("la aseguradora tiene $ 200 M en pesos tokenizados", (await token.balanceOf(s.aseguradora.address)) === 20_000_000_000n);

  return { token, canje, s };
}

function guardar(ctx) {
  return Promise.all([ctx.token.getAddress(), ctx.canje.getAddress(), ethers.provider.getNetwork()]).then(([tok, can, red]) => {
    fs.writeFileSync(ARCHIVO, JSON.stringify({ red: network.name, chainId: Number(red.chainId), PesoToken: tok, ECanjeProtegido: can }, null, 2) + "\n");
    console.log("");
    info("Direcciones guardadas en:", "despliegue.json (las usan las campañas)");
  });
}

// Recupera los contratos desplegados por "npm run inicializar"
async function cargar() {
  const error = (m) => { console.error(`\n  ${m}\n  Primero ejecutar: npm run inicializar\n`); process.exit(1); };
  if (!fs.existsSync(ARCHIVO)) error("No hay contratos desplegados (falta despliegue.json).");
  const d = JSON.parse(fs.readFileSync(ARCHIVO, "utf8"));
  if ((await ethers.provider.getCode(d.ECanjeProtegido)) === "0x")
    error("Los contratos de despliegue.json no están en esta red (¿se reinició el nodo?).");
  const token = await ethers.getContractAt("PesoToken", d.PesoToken);
  const canje = await ethers.getContractAt("ECanjeProtegido", d.ECanjeProtegido);
  return { token, canje, s: await cuentas() };
}

module.exports = { inicializar, guardar, cargar };
