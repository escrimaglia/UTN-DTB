// Pruebas del contrato e-CanjeProtegido: un caso por cada camino del DTE (Figura 3)
// y por cada regla de negocio. Montos = escenario de ejemplo de 02_contrato.md §8.
const { expect } = require("chai");
const { ethers } = require("hardhat");
const { loadFixture, time } = require("@nomicfoundation/hardhat-network-helpers");

const DIA = 24n * 60n * 60n;
const E = { Solicitado: 0, Aprobado: 1, Asegurado: 2, Vigente: 3, Siniestrado: 4, Indemnizado: 5,
            EnCosecha: 6, Saldado: 7, Rechazado: 8, EnMora: 9 };

// Valores ilustrativos (centavos de peso tokenizado)
const PRECIO_CANJE = 40_000_000n;        // $ 400.000 por tonelada
const SUMA_ASEGURADA = 12_000_000_000n;  // $ 120 millones
const INSUMOS_KG = 210_000n;
const PRIMA_KG = 12_000n;
const h = (s) => ethers.id(s);           // hash de un documento

async function desplegar() {
  const [admin, banco, productor, agronomia, aseguradora, acopio, conae, smn, otro] = await ethers.getSigners();

  const token = await ethers.deployContract("PesoToken", [banco.address]);
  const canje = await ethers.deployContract("ECanjeProtegido", [await token.getAddress(), admin.address]);

  await canje.grantRole(await canje.PRODUCTOR_ROLE(), productor.address);
  await canje.grantRole(await canje.AGRONOMIA_ROLE(), agronomia.address);
  await canje.grantRole(await canje.ASEGURADORA_ROLE(), aseguradora.address);
  await canje.grantRole(await canje.ACOPIO_ROLE(), acopio.address);
  await canje.grantRole(await canje.ORACULO_ROLE(), conae.address);
  await canje.grantRole(await canje.ORACULO_ROLE(), smn.address);

  await token.connect(banco).emitir(aseguradora.address, 20_000_000_000n);
  await token.connect(aseguradora).approve(await canje.getAddress(), ethers.MaxUint256);

  return { canje, token, admin, productor, agronomia, aseguradora, acopio, conae, smn, otro };
}

// Lleva un canje hasta el estado Vigente y devuelve las fechas del período crítico
async function canjeVigente(f) {
  const { canje, productor, agronomia, aseguradora, acopio, conae, smn } = f;
  const ahora = BigInt(await time.latest());
  const inicio = ahora + 30n * DIA;
  const fin = inicio + 50n * DIA;
  const limiteEntrega = fin + 120n * DIA;

  await canje.connect(productor).crearSolicitud(agronomia.address, h("Lote 14, Rio Primero"), "soja", 2026, INSUMOS_KG);
  await canje.connect(agronomia).aprobarCanje(1, aseguradora.address, acopio.address, PRECIO_CANJE, limiteEntrega);
  await canje.connect(aseguradora).emitirPoliza(1, {
    idPoliza: h("PSQ-2026-000123"), proveedorPrimario: conae.address, proveedorAlternativo: smn.address,
    inicioPeriodo: inicio, finPeriodo: fin, umbrales: [600, 800], porcentajes: [5000, 10000],
    sumaAsegurada: SUMA_ASEGURADA, primaKg: PRIMA_KG, condiciones: h("condiciones y riesgo de base"),
  });
  await canje.connect(agronomia).entregarInsumos(1, h("remito 0001-00004521"));
  return { inicio, fin, limiteEntrega };
}

// Reporta un valor del índice dentro del período y cierra el período crítico
async function cerrarConIndice(f, fechas, valor) {
  await time.increaseTo(fechas.inicio + 40n * DIA);
  await f.canje.connect(f.conae).reportarIndice(1, fechas.inicio + 39n * DIA, valor);
  await time.increaseTo(fechas.fin + 1n);
  await f.canje.cerrarPeriodoCritico(1);
}

const estado = async (canje) => Number((await canje.verCanje(1)).estado);

describe("e-CanjeProtegido", function () {
  describe("Caminos del DTE", function () {
    it("año normal: Vigente → EnCosecha → entregas parciales → Saldado", async function () {
      const f = await loadFixture(desplegar);
      const fechas = await canjeVigente(f);
      expect((await f.canje.verCanje(1)).deudaKg).to.equal(INSUMOS_KG + PRIMA_KG); // la prima se suma a la deuda

      await cerrarConIndice(f, fechas, 300);
      expect(await estado(f.canje)).to.equal(E.EnCosecha);

      await f.canje.connect(f.acopio).entregarGranos(1, 100_000n, h("CPE 1"));
      expect(await estado(f.canje)).to.equal(E.EnCosecha);
      await expect(f.canje.connect(f.acopio).entregarGranos(1, 122_000n, h("CPE 2")))
        .to.emit(f.canje, "EstadoCambiado").withArgs(1, E.EnCosecha, E.Saldado);
    });

    it("sequía severa (índice 850): la indemnización cancela la deuda y el saldo es del productor", async function () {
      const f = await loadFixture(desplegar);
      const fechas = await canjeVigente(f);
      await cerrarConIndice(f, fechas, 850);
      expect(await estado(f.canje)).to.equal(E.Siniestrado);
      expect((await f.canje.verLiquidacion(1)).montoIndemnizacion).to.equal(SUMA_ASEGURADA);

      await expect(f.canje.connect(f.aseguradora).pagarIndemnizacion(1))
        .to.emit(f.canje, "IndemnizacionPagada").withArgs(1, SUMA_ASEGURADA, true);
      await f.canje.liquidarCanje(1);
      expect(await estado(f.canje)).to.equal(E.Saldado);

      // 222 t × $ 400.000 = $ 88,8 millones a la agronomía; $ 31,2 millones al productor
      expect(await f.canje.fondosPendientes(f.agronomia.address)).to.equal(8_880_000_000n);
      expect(await f.canje.fondosPendientes(f.productor.address)).to.equal(3_120_000_000n);

      await f.canje.connect(f.agronomia).retirarFondos();
      await f.canje.connect(f.productor).retirarFondos();
      expect(await f.token.balanceOf(f.agronomia.address)).to.equal(8_880_000_000n);
      expect(await f.token.balanceOf(f.productor.address)).to.equal(3_120_000_000n);
    });

    it("sequía moderada (índice 680): cubre 150 t y quedan 72 t para entregar con la cosecha", async function () {
      const f = await loadFixture(desplegar);
      const fechas = await canjeVigente(f);
      await cerrarConIndice(f, fechas, 680);
      expect((await f.canje.verLiquidacion(1)).montoIndemnizacion).to.equal(6_000_000_000n); // 50 %

      await f.canje.connect(f.aseguradora).pagarIndemnizacion(1);
      await f.canje.liquidarCanje(1);
      expect(await estado(f.canje)).to.equal(E.EnCosecha);
      expect((await f.canje.verCanje(1)).deudaKg).to.equal(72_000n);
      expect(await f.canje.fondosPendientes(f.productor.address)).to.equal(0n);

      await f.canje.connect(f.acopio).entregarGranos(1, 72_000n, h("CPE 1"));
      expect(await estado(f.canje)).to.equal(E.Saldado);
    });

    it("rechazo: Solicitado → Rechazado y no admite más eventos", async function () {
      const f = await loadFixture(desplegar);
      await f.canje.connect(f.productor).crearSolicitud(f.agronomia.address, h("Lote 7"), "maiz", 2026, 50_000n);
      await f.canje.connect(f.agronomia).rechazarCanje(1, "sin calificacion crediticia");
      expect(await estado(f.canje)).to.equal(E.Rechazado);
      await expect(f.canje.connect(f.agronomia).aprobarCanje(1, f.aseguradora.address, f.acopio.address, PRECIO_CANJE, 9_999_999_999n))
        .to.be.revertedWithCustomError(f.canje, "EstadoInvalido");
    });

    it("mora: solo después de la fecha límite y con deuda pendiente", async function () {
      const f = await loadFixture(desplegar);
      const fechas = await canjeVigente(f);
      await cerrarConIndice(f, fechas, 300);
      await expect(f.canje.connect(f.agronomia).declararMora(1)).to.be.revertedWithCustomError(f.canje, "FueraDePlazo");
      await time.increaseTo(fechas.limiteEntrega + 1n);
      await f.canje.connect(f.agronomia).declararMora(1);
      expect(await estado(f.canje)).to.equal(E.EnMora);
    });
  });

  describe("Reglas de negocio", function () {
    it("restricción de acceso: cada evento solo lo dispara su rol", async function () {
      const f = await loadFixture(desplegar);
      await expect(f.canje.connect(f.otro).crearSolicitud(f.agronomia.address, h("L"), "soja", 2026, 1n))
        .to.be.revertedWithCustomError(f.canje, "AccessControlUnauthorizedAccount");
      const fechas = await canjeVigente(f);
      await time.increaseTo(fechas.inicio + 1n * DIA);
      await expect(f.canje.connect(f.aseguradora).reportarIndice(1, fechas.inicio, 900))
        .to.be.revertedWithCustomError(f.canje, "OraculoNoHabilitado"); // la aseguradora no puede informar el índice
    });

    it("oráculo alternativo: solo informa si el primario no reportó en 5 días", async function () {
      const f = await loadFixture(desplegar);
      const fechas = await canjeVigente(f);
      await time.increaseTo(fechas.inicio + 3n * DIA);
      await expect(f.canje.connect(f.smn).reportarIndice(1, fechas.inicio + 2n * DIA, 500))
        .to.be.revertedWithCustomError(f.canje, "OraculoNoHabilitado");
      await time.increaseTo(fechas.inicio + 6n * DIA);
      await f.canje.connect(f.smn).reportarIndice(1, fechas.inicio + 5n * DIA, 500);
      expect((await f.canje.verLiquidacion(1)).fuenteIndice).to.equal(f.smn.address);
    });

    it("plazo de 15 días: el pago tardío y la falta de pago quedan registrados", async function () {
      const f = await loadFixture(desplegar);
      const fechas = await canjeVigente(f);
      await cerrarConIndice(f, fechas, 850);
      await expect(f.canje.notificarPlazoIncumplido(1)).to.be.revertedWithCustomError(f.canje, "FueraDePlazo");
      await time.increase(16n * DIA);
      await expect(f.canje.notificarPlazoIncumplido(1)).to.emit(f.canje, "PlazoIncumplido");
      await expect(f.canje.connect(f.aseguradora).pagarIndemnizacion(1))
        .to.emit(f.canje, "IndemnizacionPagada").withArgs(1, SUMA_ASEGURADA, false);
    });

    it("el período crítico no se puede cerrar antes de tiempo ni sin dato del índice", async function () {
      const f = await loadFixture(desplegar);
      const fechas = await canjeVigente(f);
      await expect(f.canje.cerrarPeriodoCritico(1)).to.be.revertedWithCustomError(f.canje, "FueraDePlazo");
      await time.increaseTo(fechas.fin + 1n);
      await expect(f.canje.cerrarPeriodoCritico(1)).to.be.revertedWithCustomError(f.canje, "SinDatoDelIndice");
    });

    it("la póliza exige tramos crecientes y dos proveedores distintos", async function () {
      const f = await loadFixture(desplegar);
      const ahora = BigInt(await time.latest());
      await f.canje.connect(f.productor).crearSolicitud(f.agronomia.address, h("L"), "soja", 2026, 1000n);
      await f.canje.connect(f.agronomia).aprobarCanje(1, f.aseguradora.address, f.acopio.address, PRECIO_CANJE, ahora + 300n * DIA);
      const base = { idPoliza: h("P"), proveedorPrimario: f.conae.address, proveedorAlternativo: f.smn.address,
        inicioPeriodo: ahora + 10n * DIA, finPeriodo: ahora + 60n * DIA, umbrales: [800, 600], porcentajes: [5000, 10000],
        sumaAsegurada: 1n, primaKg: 0n, condiciones: h("C") };
      await expect(f.canje.connect(f.aseguradora).emitirPoliza(1, base)).to.be.revertedWithCustomError(f.canje, "ParametroInvalido");
      await expect(f.canje.connect(f.aseguradora).emitirPoliza(1, { ...base, umbrales: [600, 800], proveedorAlternativo: f.conae.address }))
        .to.be.revertedWithCustomError(f.canje, "ParametroInvalido");
    });

    it("parada de emergencia: bloquea eventos pero no los retiros", async function () {
      const f = await loadFixture(desplegar);
      const fechas = await canjeVigente(f);
      await cerrarConIndice(f, fechas, 850);
      await f.canje.connect(f.aseguradora).pagarIndemnizacion(1);
      await f.canje.liquidarCanje(1);
      await f.canje.pausar();
      await expect(f.canje.connect(f.productor).crearSolicitud(f.agronomia.address, h("L"), "soja", 2026, 1n))
        .to.be.revertedWithCustomError(f.canje, "EnforcedPause");
      await f.canje.connect(f.productor).retirarFondos();
      expect(await f.token.balanceOf(f.productor.address)).to.equal(3_120_000_000n);
    });
  });
});
