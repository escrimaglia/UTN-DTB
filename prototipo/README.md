# Prototipo e-CanjeProtegido

Contrato inteligente modelado en el TP4 e implementado en el TP5 (Desarrollo con Tecnologías Blockchain, UTN FRC, 2026).
Proceso, tecnología, casos de prueba y limitaciones: `TP5_Desarrollo.pdf`.

Requisitos: Node.js 18 o superior y npm. No hace falta billetera ni claves: Hardhat crea cuentas de prueba.

## Demostración de la clase (TP5)

Todos los comandos se corren dentro de esta carpeta (`prototipo/`) y son iguales en macOS y Windows.

| Comando | Qué hace |
|---|---|
| `npm ci` | Instala las dependencias exactas de `package-lock.json` (la primera vez necesita internet) |
| `npm test` | Corre las 11 pruebas automatizadas del contrato. Esperado: **11 passing** |
| `npm run node` | Levanta la red local de Hardhat (chainId 31337, 20 cuentas de prueba). Queda abierta en esa terminal; se apaga con Ctrl+C |
| `npm run inicializar` | **Parte 1.** Despliega los contratos, asigna los roles y el banco emite $ 200 M para la aseguradora. Guarda las direcciones en `despliegue.json` |
| `npm run campania:normal` | **Parte 2.** Campaña completa de un canje con índice de sequía **300**: el contrato no activa la póliza y la deuda se paga con granos |
| `npm run campania:sequia` | **Parte 3.** La misma campaña con índice **850**: el contrato ejecuta la póliza, cancela primero la deuda y el saldo es del productor |
| `npm run demo` | Ensayo: las tres partes seguidas en una red en memoria (no hace falta el nodo). Esperado: **37 verificaciones correctas, 0 fallidas** |

Las dos campañas ejecutan los mismos pasos; solo cambia el índice que informa el oráculo, y el contrato decide el camino al cerrar el período crítico. Se pueden repetir y correr en cualquier orden (cada una crea un canje nuevo), pero primero hay que inicializar. Si se reinicia el nodo, hay que volver a correr `npm run inicializar`. Cada comando se detiene al final de cada caso hasta que se aprieta Enter.

```bash
npm ci
npm run node               # terminal 1 (queda ocupada con el nodo)
npm run inicializar        # terminal 2: parte 1
npm run campania:normal    # terminal 2: parte 2
npm run campania:sequia    # terminal 2: parte 3
```

## Opción 1: pruebas automatizadas (Hardhat)

```bash
npm ci
npm test                # 11 pruebas, una por camino del DTE y por regla de negocio
npx hardhat coverage    # cobertura (opcional)
```

## Opción 2: demo manual en Remix (alternativa sin instalación)

1. Abrir https://remix.ethereum.org y crear `PesoToken.sol` y `ECanjeProtegido.sol` con el contenido de `contracts/`. Remix descarga solo las librerías de OpenZeppelin.
2. Compilar con Solidity **0.8.24** o superior (Advanced: EVM `cancun`).
3. En *Deploy & Run* (entorno *Remix VM*), elegir una cuenta para cada rol: admin, banco, productor, agronomía, aseguradora, acopio, oráculo primario, oráculo alternativo.
4. Desplegar `PesoToken(banco)` y `ECanjeProtegido(direcciónDelToken, admin)`.
5. Con la cuenta admin, `grantRole` para cada rol. Los identificadores de los roles se leen con los botones `PRODUCTOR_ROLE`, `AGRONOMIA_ROLE`, etc.
6. Con la cuenta del banco, `emitir(aseguradora, 20000000000)`. Con la cuenta de la aseguradora, `approve(direcciónDelContrato, 20000000000)` en el token.
7. Recorrer el DTE con la cuenta de cada participante:
   - **productor:** `crearSolicitud(agronomia, 0x…lote, "soja", 2026, 210000)`;
   - **agronomía:** `aprobarCanje(1, aseguradora, acopio, 40000000, <ahora + 1 hora>)`;
   - **aseguradora:** `emitirPoliza(1, [idPoliza, primario, alternativo, <ahora + 2 min>, <ahora + 5 min>, [600,800], [5000,10000], 12000000000, 12000, 0x…])`;
   - **agronomía:** `entregarInsumos(1, 0x…remito)`;
   - **oráculo primario**, cuando ya empezó el período: `reportarIndice(1, <fecha>, 850)`;
   - **cualquiera**, cuando terminó el período: `cerrarPeriodoCritico(1)`. Después, la **aseguradora** `pagarIndemnizacion(1)`, **cualquiera** `liquidarCanje(1)`, y la **agronomía** y el **productor** `retirarFondos()`.
8. En cada paso, `verCanje(1)` y `verLiquidacion(1)` muestran el estado y el cálculo.

**Tiempos.** En Remix VM el reloj es la hora real, así que para la demo conviene usar un período crítico de pocos minutos. Las fechas son *timestamps* Unix en segundos: se obtienen en https://www.epochconverter.com o con `Math.floor(Date.now()/1000)` en la consola del navegador. Los `bytes32` (lote, remito, idPoliza, condiciones) pueden ser cualquier valor distinto de cero, por ejemplo `0x` seguido de 64 caracteres hexadecimales.
