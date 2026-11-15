// Partes 2 y 3 de la demostración: una campaña completa de un canje.
// Las dos campañas ejecutan EXACTAMENTE los mismos pasos; solo cambia el índice de sequía que
// informa el oráculo. Al cerrar el período crítico, el CONTRATO decide el camino:
//   índice < 600  → EnCosecha (la póliza no paga; la deuda se cancela con granos)
//   índice ≥ 600  → Siniestrado (la póliza paga; la indemnización cancela primero la deuda)
const { time } = require("@nomicfoundation/hardhat-network-helpers");
const { DIA, h, pesos, t, parte, titulo, info, paso, verificar, estado, debeFallar } = require("./comun");

// Datos del escenario de la Actividad 4
const INSUMOS_KG = 210_000n, PRIMA_KG = 12_000n, PRECIO = 40_000_000n;    // centavos por tonelada
const SUMA = 12_000_000_000n, UMBRALES = [600, 800], PORCENTAJES = [5000, 10000];

async function campania({ token, canje, s }, indice, nombre) {
  const e = (id) => estado(canje, id);
  const recorrido = [];
  const anotar = async (id) => { const x = await e(id); if (recorrido[recorrido.length - 1] !== x) recorrido.push(x); };

  // Lo que la regla de la póliza debería decidir con este índice (para comparar con lo que hace el contrato)
  const pct = indice >= UMBRALES[1] ? PORCENTAJES[1] : indice >= UMBRALES[0] ? PORCENTAJES[0] : 0;
  const indemnEsperada = (SUMA * BigInt(pct)) / 10_000n;
  const deudaPesos = ((INSUMOS_KG + PRIMA_KG) * PRECIO) / 1000n;

  parte(`CAMPAÑA: ${nombre}`);
  info("Índice que va a informar:", `${indice} (el oráculo lo informa en el caso 7)`);
  info("Regla de la póliza:", `índice ≥ ${UMBRALES[0]} → 50 % · índice ≥ ${UMBRALES[1]} → 100 % de ${pesos(SUMA)}`);
  info("Quién decide:", "el contrato, al cerrar el período crítico (caso 8)");

  // ------------------------------------------------------------------
  await titulo(1, "Creación del activo: el productor solicita el canje");
  paso("crearSolicitud(agronomía, lote, \"soja\", 2026, 210.000 kg)", "productor", "canje nuevo en Solicitado; evento CanjeSolicitado");
  await (await canje.connect(s.productor).crearSolicitud(s.agronomia.address, h(`lote campaña ${nombre}`), "soja", 2026, INSUMOS_KG)).wait();
  const id = await canje.cantidadCanjes();
  await anotar(id);
  info("Obtenido:", `canje n.º ${id} · estado ${await e(id)} · deuda ${t((await canje.verCanje(id)).deudaKg)}`);
  verificar(`el canje ${id} existe y está en Solicitado`, (await e(id)) === "Solicitado");

  // ------------------------------------------------------------------
  await titulo(2, "Rechazo por falta de permisos");
  paso("A) crearSolicitud(...) desde una cuenta sin PRODUCTOR_ROLE", "intruso", "AccessControlUnauthorizedAccount");
  await debeFallar(canje, () => canje.connect(s.intruso).crearSolicitud(s.agronomia.address, h("x"), "soja", 2026, 1n),
                   "AccessControlUnauthorizedAccount");
  paso(`B) aprobarCanje(${id}, …) por alguien que no es la agronomía del canje`, "productor", "NoEsLaParte");
  await debeFallar(canje, () => canje.connect(s.productor).aprobarCanje(id, s.aseguradora.address, s.acopio.address, 1n, 9_999_999_999n),
                   "NoEsLaParte");
  verificar("el canje sigue en Solicitado (nada cambió)", (await e(id)) === "Solicitado");

  // ------------------------------------------------------------------
  await titulo(3, "Recorrido válido: la agronomía aprueba el canje");
  const ahora = BigInt(await time.latest());
  const inicio = ahora + 30n * DIA, fin = inicio + 50n * DIA, limite = fin + 120n * DIA;
  paso(`aprobarCanje(${id}, aseguradora, acopio, $ 400.000/t, fecha límite)`, "agronomía", "Solicitado → Aprobado");
  await (await canje.connect(s.agronomia).aprobarCanje(id, s.aseguradora.address, s.acopio.address, PRECIO, limite)).wait();
  await anotar(id);
  info("Obtenido:", `estado ${await e(id)}`);
  verificar("Solicitado → Aprobado", (await e(id)) === "Aprobado");

  // ------------------------------------------------------------------
  await titulo(4, "Rechazo de una transición inválida");
  paso(`entregarInsumos(${id}, remito) sin póliza emitida`, "agronomía", "EstadoInvalido (está en 1 Aprobado; hace falta 2 Asegurado)");
  await debeFallar(canje, () => canje.connect(s.agronomia).entregarInsumos(id, h("remito")), "EstadoInvalido");
  verificar("el canje sigue en Aprobado", (await e(id)) === "Aprobado");

  // ------------------------------------------------------------------
  await titulo(5, "Recorrido válido: póliza e insumos");
  if ((await token.balanceOf(s.aseguradora.address)) < SUMA) {   // solo si se repiten campañas con siniestro
    await (await token.connect(s.banco).emitir(s.aseguradora.address, SUMA)).wait();
    info("Fondos:", `el banco emite ${pesos(SUMA)} más para la aseguradora`);
  }
  paso(`emitirPoliza(${id}, $ 120 M, tramos [600 → 50 %, 800 → 100 %], prima 12 t)`, "aseguradora",
       "Aprobado → Asegurado; la prima se suma a la deuda (222 t)");
  await (await canje.connect(s.aseguradora).emitirPoliza(id, {
    idPoliza: h(`póliza canje ${id}`), proveedorPrimario: s.conae.address, proveedorAlternativo: s.smn.address,
    inicioPeriodo: inicio, finPeriodo: fin, umbrales: UMBRALES, porcentajes: PORCENTAJES,
    sumaAsegurada: SUMA, primaKg: PRIMA_KG, condiciones: h("condiciones y riesgo de base"),
  })).wait();
  await anotar(id);
  info("Obtenido:", `estado ${await e(id)} · deuda ${t((await canje.verCanje(id)).deudaKg)}`);
  verificar("Aprobado → Asegurado; deuda 222 t", (await e(id)) === "Asegurado" && (await canje.verCanje(id)).deudaKg === INSUMOS_KG + PRIMA_KG);
  paso(`entregarInsumos(${id}, remito)`, "agronomía", "Asegurado → Vigente");
  await (await canje.connect(s.agronomia).entregarInsumos(id, h(`remito canje ${id}`))).wait();
  await anotar(id);
  info("Obtenido:", `estado ${await e(id)}`);
  verificar("Asegurado → Vigente", (await e(id)) === "Vigente");

  // ------------------------------------------------------------------
  await titulo(6, "Consulta de datos y estado del activo (funciones view, sin gas)");
  paso(`verCanje(${id}), verPoliza(${id}), calcularIndemnizacion(${id}, ${indice})`, "cualquiera (consulta)", "datos del canje y de la póliza");
  const c = await canje.verCanje(id), p = await canje.verPoliza(id);
  info("Productor:", c.productor);
  info("Agronomía:", c.agronomia);
  info("Cultivo / campaña:", `${c.cultivo} ${c.campania}`);
  info("Deuda:", `${t(c.deudaKg)} = ${pesos((c.deudaKg * c.precioCanje) / 1000n)}`);
  info("Estado:", await e(id));
  info("Suma asegurada:", pesos(p.sumaAsegurada));
  const [tramo, monto] = await canje.calcularIndemnizacion(id, indice);
  info(`Si el índice es ${indice}:`, `tramo ${tramo} · indemnización ${pesos(monto)}`);
  verificar(`con índice ${indice} la póliza pagaría ${pesos(indemnEsperada)}`, monto === indemnEsperada);

  // ------------------------------------------------------------------
  await titulo(7, `El oráculo informa el índice de sequía: ${indice}`);
  await time.increaseTo(inicio + 40n * DIA);  // avanza el reloj de la red: día 40 del período crítico
  info("Reloj:", "adelantado al día 40 del período crítico");
  paso(`reportarIndice(${id}, fecha, ${indice})`, "oráculo primario", `índice ${indice} registrado`);
  await (await canje.connect(s.conae).reportarIndice(id, inicio + 39n * DIA, indice)).wait();
  info("Obtenido:", `índice registrado ${(await canje.verLiquidacion(id)).valorIndice}`);
  verificar(`el oráculo primario registró ${indice}`, Number((await canje.verLiquidacion(id)).valorIndice) === indice);
  paso(`reportarIndice(${id}, fecha, 100) mientras el primario está informando`, "oráculo alternativo", "OraculoNoHabilitado");
  await debeFallar(canje, () => canje.connect(s.smn).reportarIndice(id, inicio + 39n * DIA, 100), "OraculoNoHabilitado");

  // ------------------------------------------------------------------
  await titulo(8, "Cierre del período crítico: el contrato decide");
  await time.increaseTo(fin + 1n);
  info("Reloj:", "adelantado al fin del período crítico");
  const hayPago = indemnEsperada > 0n;
  paso(`cerrarPeriodoCritico(${id})`, "cualquiera (el contrato controla la fecha)",
       hayPago ? `Vigente → Siniestrado; indemnización ${pesos(indemnEsperada)}` : "Vigente → EnCosecha; indemnización $ 0");
  await (await canje.connect(s.intruso).cerrarPeriodoCritico(id)).wait();
  await anotar(id);
  const l0 = await canje.verLiquidacion(id);
  info("Obtenido:", `estado ${await e(id)} · indemnización ${pesos(l0.montoIndemnizacion)}`);
  info("Decisión del contrato:", hayPago
    ? `índice ${indice} ≥ ${indice >= UMBRALES[1] ? UMBRALES[1] : UMBRALES[0]}: HAY SINIESTRO, la póliza paga ${pct / 100} % = ${pesos(l0.montoIndemnizacion)}`
    : `índice ${indice} < ${UMBRALES[0]}: NO HAY SINIESTRO, la póliza no paga`);
  verificar(hayPago ? "Vigente → Siniestrado con la indemnización de la póliza" : "Vigente → EnCosecha sin indemnización",
            (await e(id)) === (hayPago ? "Siniestrado" : "EnCosecha") && l0.montoIndemnizacion === indemnEsperada);

  // ------------------------------------------------------------------
  const saldoAseg0 = await token.balanceOf(s.aseguradora.address);
  const agro0 = await token.balanceOf(s.agronomia.address), prod0 = await token.balanceOf(s.productor.address);
  let granosKg = 0n;

  if (hayPago) {
    await titulo(9, "Se ejecuta la póliza: pago, liquidación (primero la deuda) y cobro");
    paso(`pagarIndemnizacion(${id})`, "aseguradora", `Siniestrado → Indemnizado; el contrato recibe ${pesos(indemnEsperada)}`);
    await (await canje.connect(s.aseguradora).pagarIndemnizacion(id)).wait();
    await anotar(id);
    info("Obtenido:", `estado ${await e(id)} · saldo de la aseguradora ${pesos(await token.balanceOf(s.aseguradora.address))}`);
    verificar("Siniestrado → Indemnizado", (await e(id)) === "Indemnizado");

    const aplicado = indemnEsperada < deudaPesos ? indemnEsperada : deudaPesos;
    paso(`liquidarCanje(${id})`, "cualquiera", `${pesos(aplicado)} a la agronomía y ${pesos(indemnEsperada - aplicado)} al productor`);
    await (await canje.liquidarCanje(id)).wait();
    await anotar(id);
    const l = await canje.verLiquidacion(id);
    info("Obtenido:", `estado ${await e(id)}`);
    info("  a la agronomía (deuda):", pesos(l.montoAplicadoDeuda));
    info("  al productor (saldo):", pesos(l.saldoProductor));
    info("  deuda restante:", t((await canje.verCanje(id)).deudaKg));
    verificar("la indemnización cancela primero la deuda y el resto es del productor",
              l.montoAplicadoDeuda === aplicado && l.saldoProductor === indemnEsperada - aplicado);
  } else {
    await titulo(9, "La póliza no se ejecuta: la deuda se paga con la cosecha");
    paso(`pagarIndemnizacion(${id})`, "aseguradora", "EstadoInvalido (está en 6 EnCosecha; haría falta 4 Siniestrado)");
    await debeFallar(canje, () => canje.connect(s.aseguradora).pagarIndemnizacion(id), "EstadoInvalido");
  }

  // Si queda deuda (año normal o sequía moderada), el acopio registra la entrega de granos
  if ((await e(id)) === "EnCosecha") {
    const deuda = (await canje.verCanje(id)).deudaKg;
    const primera = deuda > 100_000n ? 100_000n : deuda;
    for (const kg of primera < deuda ? [primera, deuda - primera] : [deuda]) {
      paso(`entregarGranos(${id}, ${t(kg)}, carta de porte)`, "acopio", kg === (await canje.verCanje(id)).deudaKg ? "EnCosecha → Saldado" : "entrega parcial: sigue EnCosecha");
      await (await canje.connect(s.acopio).entregarGranos(id, kg, h(`CPE ${id}-${kg}`))).wait();
      granosKg += kg;
      await anotar(id);
      info("Obtenido:", `estado ${await e(id)} · deuda ${t((await canje.verCanje(id)).deudaKg)}`);
    }
    verificar("la deuda en granos quedó cancelada: Saldado", (await e(id)) === "Saldado");
  }

  if (hayPago) {
    paso("retirarFondos()", "agronomía y productor", "cada uno recibe lo que le asignó la liquidación");
    for (const c of [s.agronomia, s.productor])
      if ((await canje.fondosPendientes(c.address)) > 0n) await (await canje.connect(c).retirarFondos()).wait();
    const cobroAgro = (await token.balanceOf(s.agronomia.address)) - agro0, cobroProd = (await token.balanceOf(s.productor.address)) - prod0;
    info("Obtenido:", `agronomía cobró ${pesos(cobroAgro)} · productor cobró ${pesos(cobroProd)}`);
    const l = await canje.verLiquidacion(id);
    verificar("lo cobrado coincide con la liquidación", cobroAgro === l.montoAplicadoDeuda && cobroProd === l.saldoProductor);
    paso("retirarFondos() por segunda vez", "agronomía", "NadaParaRetirar");
    await debeFallar(canje, () => canje.connect(s.agronomia).retirarFondos(), "NadaParaRetirar");
  }

  // ------------------------------------------------------------------
  await titulo(10, "Resumen de la campaña");
  const pagoAseg = saldoAseg0 - (await token.balanceOf(s.aseguradora.address));
  info("Índice informado:", `${indice}`);
  info("Decisión del contrato:", hayPago ? "hubo siniestro: la póliza se ejecutó" : "no hubo siniestro: la póliza no se ejecutó");
  info("Pagó la aseguradora:", pesos(pagoAseg));
  info("Granos entregados:", t(granosKg));
  info("Estado final:", `canje n.º ${id} en ${await e(id)}`);
  info("Recorrido:", recorrido.slice(0, 4).join(" → ") + " →");
  info("", recorrido.slice(4).join(" → "));
  verificar("el canje terminó Saldado", (await e(id)) === "Saldado");
}

module.exports = { campania };
