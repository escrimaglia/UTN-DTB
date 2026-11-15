# Guía de demostración — e-CanjeProtegido (16/11/2026)

*Cómo usarla.* Es el guion de la demostración en vivo del TP5: qué se prepara antes de la clase, quién habla en cada momento y, para cada caso de prueba, **qué operación se ejecuta, con qué datos, qué resultado se espera y cómo se verifica**, como pide la consigna. Duración total: **15 minutos**, cuatro expositores. Todos deben poder explicar cualquier parte del código: el documento técnico (`TP5_Documento_Tecnico.pdf`) sirve para estudiarlo.

## Reparto y tiempos

La demostración se hace con **tres comandos**, uno por parte. Antes de cada uno, el expositor dice qué va a ejecutar:

| Parte | Comando | Qué se muestra |
|---|---|---|
| 1. Inicialización | `npm run inicializar` | Despliegue de los contratos, roles y fondos |
| 2. Año normal | `npm run campania:normal` | Un canje completo con índice de sequía **300**: el contrato no activa la póliza |
| 3. Sequía severa | `npm run campania:sequia` | El mismo canje con índice **850**: el contrato ejecuta la póliza |

Las dos campañas hacen **los mismos pasos**; solo cambia el índice. La idea que tiene que quedar: *nadie decide si se paga el seguro, decide el contrato con la regla firmada*. Cada comando **se detiene al final de cada caso** (*… Enter para continuar*): el expositor explica lo que se ve y avanza con Enter.

| Expositor | Bloque | Inicio | Duración |
|---|---|:-:|:-:|
| Expositor 1 | Recordatorio del proceso y del contrato (Actividad 4) · tecnología y lenguaje elegidos | 0:00 | 2:30 |
| Expositor 2 | Red local · **parte 1** (`inicializar`) · **parte 2**, casos 1 a 5 (creación, permisos, aprobación, transición inválida, póliza) | 2:30 | 3:30 |
| Expositor 3 | **Parte 2**, casos 6 a 10 (consulta, índice 300, el contrato decide, cosecha, resumen) | 6:00 | 3:00 |
| Expositor 4 | **Parte 3** (`campania:sequia`): casos 1 a 6 rápido, 7 a 10 en detalle · pruebas automatizadas · ajustes y limitaciones | 9:00 | 5:00 |
| Margen | — | 14:00 | 1:00 |

## Antes de la clase (entorno listo)

La consigna exige que el entorno esté **instalado, configurado y listo** al comenzar. El día anterior y otra vez antes de entrar:

1. En la notebook que se conecta al proyector, descomprimir el ZIP (o clonar el repositorio) y entrar a `prototipo/`.
2. `npm ci` (necesita internet la primera vez) y `npm run compile`. Comprobar que termine sin errores (*Compiled … Solidity files successfully* o *Nothing to compile*).
3. `npm test`: tienen que aparecer **11 passing**.
4. Ensayo completo sin nodo: `npm run demo`. Tiene que terminar con **RESULTADO: 37 verificaciones correctas, 0 fallidas**.
5. Ensayo con nodo: `npm run node` en una terminal y, en otra, los tres comandos en orden. Resultados: **3**, **16** y **18** verificaciones correctas, 0 fallidas. Cortar el nodo (Ctrl + C) al terminar: en la clase se levanta de nuevo.
6. Dejar abiertas **dos terminales** con letra grande (Cmd + en macOS o Ctrl + en Windows, varias veces), ya ubicadas en `prototipo/`, y el editor con `contracts/ECanjeProtegido.sol` abierto, para mostrar el código cuando pregunten.
7. Plan B sin internet: todo corre localmente, no hace falta conexión. Plan C: Remix (pasos en `README.md`). Material complementario: las salidas guardadas al final de esta guía (no reemplazan la ejecución en vivo).

## Expositor 1 — El proceso y la tecnología (0:00 – 2:30)

- **El proceso:** canje de insumos por granos con un seguro paramétrico de sequía embebido. Si el índice satelital alcanza el umbral, el contrato calcula la indemnización, **cancela primero la deuda con la agronomía** y el saldo es del productor.
- **El contrato:** `e-CanjeProtegido`, el activo es el canje protegido, diez estados del DTE (mostrar la Figura 3 de la Actividad 4 si hay tiempo).
- **La tecnología:** consorcio permisionado sobre **Hyperledger Besu** con **QBFT**; lenguaje **Solidity** con OpenZeppelin. Justificación en una frase por criterio: organizaciones identificadas con permisos (red permisionada y roles), datos comerciales privados (solo leen los miembros, la SSN como nodo), reglas fijas al firmar (contrato inteligente) y pago en pesos tokenizados (ERC-20).
- **Hoy lo mostramos en Hardhat:** ejecuta la misma EVM que Besu, así que es el mismo contrato; además permite adelantar el reloj para simular la campaña.
- **Qué vamos a ver:** "Tres comandos: preparar la red, una campaña sin sequía y la misma campaña con sequía. Lo único que cambia es el índice que informa el oráculo."
- **Pase:** "Vamos al entorno. [Expositor 2]."

## Expositor 2 — Parte 1 y comienzo de la parte 2 (2:30 – 6:00)

**Levantar la red.** En la terminal 1:

```bash
npm run node
```

**Qué decir:** "Es una red Ethereum local, chainId 31337, con 20 cuentas de prueba con sus claves. Cada transacción que mandemos va a aparecer acá, con su bloque y su gas." Señalar las cuentas que imprime.

### Parte 1. Inicialización

**Decir antes de ejecutar:** "Primero preparamos la red: desplegamos los contratos, damos un rol a cada participante y el banco le da fondos a la aseguradora." En la terminal 2:

```bash
npm run inicializar
```

| Caso | Operación | Ejecuta | Resultado esperado | En pantalla |
|:-:|---|---|---|---|
| 1 | Desplegar `PesoToken(banco)` y `ECanjeProtegido(token, admin)` | Administrador | Dos contratos con dirección | Las dos direcciones; **[OK] los dos contratos tienen código en la red**. En la terminal 1: *Contract deployment* |
| 2 | `grantRole` para cada participante | Administrador | Seis cuentas con rol | **Rol productor: 0x…**, etc., y la **cuenta sin rol (intruso)**; **[OK]** |
| 3 | `emitir` $ 200 M y `approve` | Banco y aseguradora | Saldo $ 200 M | **Obtenido: saldo de la aseguradora $ 200.000.000**; **[OK]** |

Al final: **Direcciones guardadas en: despliegue.json** y **RESULTADO: 3 verificaciones correctas, 0 fallidas**.

**Qué decir:** "Desplegamos una sola vez; las dos campañas van a usar estos mismos contratos. El intruso no tiene rol: lo vamos a usar para probar los permisos."

### Parte 2. Campaña en un año normal

**Decir antes de ejecutar:** "Ahora una campaña completa de un canje. El oráculo va a informar un índice de sequía de 300, que no llega al umbral de 600." En la terminal 2:

```bash
npm run campania:normal
```

Arriba de todo, la salida muestra el **índice que va a informar (300)**, la **regla de la póliza** y **quién decide: el contrato, en el caso 8**.

| Caso | Operación | Ejecuta | Resultado esperado | En pantalla |
|:-:|---|---|---|---|
| 1 | `crearSolicitud(agronomía, lote, "soja", 2026, 210000)` | Productor | Canje n.º 1 en **Solicitado**, deuda 210 t | **Obtenido: canje n.º 1 · estado Solicitado · deuda 210 t**; **[OK]** |
| 2 | A) `crearSolicitud` desde el intruso. B) `aprobarCanje` desde el productor | Intruso; productor | Rechazos `AccessControlUnauthorizedAccount` y `NoEsLaParte` | Dos líneas **Revertida con:**; **[OK] el canje sigue en Solicitado** |
| 3 | `aprobarCanje(1, aseguradora, acopio, $ 400.000/t, fecha límite)` | Agronomía | **Solicitado → Aprobado** | **Obtenido: estado Aprobado**; **[OK]** |
| 4 | `entregarInsumos` sin póliza | Agronomía | Rechazo `EstadoInvalido(1, 1, 2)` | **Revertida con: EstadoInvalido(1, 1, 2)**; **[OK] el canje sigue en Aprobado** |
| 5 | `emitirPoliza` ($ 120 M, tramos [600, 800] → [50 %, 100 %], prima 12 t); `entregarInsumos` | Aseguradora; agronomía | **Aprobado → Asegurado** (deuda 222 t) → **Vigente** | Dos **Obtenido** con el estado; dos **[OK]** |

**Qué decir:**

- Caso 2: "Hay dos controles: el rol (`onlyRole`) y la parte del canje (`soloParte`). Como la transacción se revierte entera, no queda nada a medias."
- Caso 4: "El modificador `enEstado` implementa el DTE: solo se aceptan sus transiciones. Los números son la posición en el `enum Estado`: 1 Aprobado, 2 Asegurado."

**Pase:** "El canje está vigente. Veamos qué pasa con la campaña. [Expositor 3]."

## Expositor 3 — Parte 2: el año normal (6:00 – 9:00)

Sigue la misma ejecución de `npm run campania:normal`: apretar Enter para pasar al caso 6.

| Caso | Operación | Ejecuta | Resultado esperado | En pantalla |
|:-:|---|---|---|---|
| 6 | `verCanje(1)`, `verPoliza(1)`, `calcularIndemnizacion(1, 300)` | Cualquiera (consulta) | Deuda **222 t = $ 88.800.000**; con 300 la póliza pagaría **$ 0** | Los datos del canje; **[OK] con índice 300 la póliza pagaría $ 0** |
| 7 | Reloj al día 40 del período; `reportarIndice(1, fecha, 300)`; intento del oráculo alternativo | Oráculo primario; alternativo | 300 registrado; el alternativo rechazado (`OraculoNoHabilitado`) | **Obtenido: índice registrado 300**; **Revertida con: OraculoNoHabilitado** |
| 8 | Reloj al fin del período; `cerrarPeriodoCritico(1)` | Cualquiera | **Vigente → EnCosecha**, indemnización $ 0 | **Decisión del contrato: índice 300 < 600: NO HAY SINIESTRO, la póliza no paga** |
| 9 | Intento de `pagarIndemnizacion(1)`; `entregarGranos` de 100 t y de 122 t | Aseguradora; acopio | El pago se rechaza (`EstadoInvalido(1, 6, 4)`); deuda 122 t y después **Saldado** | **Revertida con: EstadoInvalido(1, 6, 4)**; deuda 122 t → 0 t; **[OK]** |
| 10 | Resumen | — | Aseguradora pagó $ 0; 222 t en granos; canje Saldado | El recorrido *Solicitado → … → EnCosecha → Saldado*; **RESULTADO: 16 verificaciones correctas** |

**Qué decir:**

- Caso 6: "Son funciones `view`: no cuestan gas y cualquiera las consulta. El productor sabe de antemano cuánto cobraría con cada índice."
- Caso 7: "El reloj se adelanta porque no podemos esperar meses en clase; en la red real el tiempo pasa solo. El alternativo solo puede informar si el primario no reportó en 5 días."
- Caso 8: "Este es el punto clave: nadie decidió. El contrato comparó el índice con la regla y mandó el canje a cosecha."
- Caso 9: "La póliza no se puede cobrar porque no hubo siniestro. La deuda se paga como siempre: con granos."

**Pase:** "Ahora la misma campaña, pero con sequía. [Expositor 4]."

## Expositor 4 — Parte 3: la sequía severa y el cierre (9:00 – 14:00)

**Decir antes de ejecutar:** "Mismo comando, mismos pasos, mismos contratos. Lo único que cambia: el oráculo va a informar 850, que supera el umbral de 800." En la terminal 2:

```bash
npm run campania:sequia
```

Los casos 1 a 6 son iguales a la campaña anterior (ahora es el **canje n.º 2**): avanzar con Enter señalando que se repiten los mismos **[OK]** y que en el caso 6 la consulta ya anticipa **$ 120.000.000**. Detenerse en los casos 7 a 10:

| Caso | Operación | Ejecuta | Resultado esperado | En pantalla |
|:-:|---|---|---|---|
| 7 | `reportarIndice(2, fecha, 850)`; intento del alternativo | Oráculo primario; alternativo | 850 registrado; el alternativo rechazado | **Obtenido: índice registrado 850**; **Revertida con: OraculoNoHabilitado** |
| 8 | `cerrarPeriodoCritico(2)` | Cualquiera | **Vigente → Siniestrado**, indemnización $ 120 M | **Decisión del contrato: índice 850 ≥ 800: HAY SINIESTRO, la póliza paga 100 % = $ 120.000.000** |
| 9 | `pagarIndemnizacion(2)`; `liquidarCanje(2)`; `retirarFondos()`; segundo retiro | Aseguradora; cualquiera; agronomía y productor | **Indemnizado** (aseguradora: $ 200 M → $ 80 M) → **Saldado**: **$ 88.800.000** a la agronomía y **$ 31.200.000** al productor; el segundo retiro se rechaza (`NadaParaRetirar`) | El reparto de la liquidación; **agronomía cobró $ 88.800.000 · productor cobró $ 31.200.000**; **[OK]** |
| 10 | Resumen | — | Aseguradora pagó $ 120 M; 0 t en granos; canje Saldado | El recorrido *Solicitado → … → Siniestrado → Indemnizado → Saldado*; **RESULTADO: 18 verificaciones correctas** |

**Qué decir:**

- Caso 8: "Mismo contrato, otra decisión: el índice superó el umbral y el contrato declaró el siniestro solo."
- Caso 9: "Nadie denunció el siniestro ni aprobó el pago. Primero se cancela la deuda con la agronomía (222 t × $ 400.000 = $ 88,8 M) y el resto es del productor. El pago es por retiro: cada parte retira lo suyo, una sola vez."
- Cierre de la comparación: "Año normal: la aseguradora no pagó nada y la deuda se pagó con granos. Sequía: la póliza pagó $ 120 M, canceló la deuda y el productor cobró el saldo."

### Pruebas automatizadas, ajustes y limitaciones

Cortar el nodo (Ctrl + C) y correr en la terminal 2:

```bash
npm test
```

Resultado esperado: **11 passing**, una prueba por camino del DTE (año normal, sequía severa, sequía moderada, rechazo, mora) y por regla (acceso, oráculo alternativo, plazo de 15 días, cierre del período, validación de la póliza, parada de emergencia). Cubren lo que la demo no recorre: sequía moderada, rechazo del canje y mora.

- **Ajustes técnicos:** un solo contrato indexado por `idCanje`; unidades enteras (kg, centavos, puntos básicos); pago por retiro; funciones de tiempo que puede llamar cualquiera porque el contrato verifica la fecha; parada de emergencia que no bloquea retiros.
- **Limitaciones:** red local y no un consorcio Besu real; oráculo y peso tokenizado simulados; sin interfaz gráfica ni auditoría externa; el pago de la prima a la aseguradora no está modelado.
- **Cierre:** "El contrato cumple el modelo de la Actividad 4: cada estado, cada evento y cada regla, ejecutados en vivo."

## Si algo falla

| Problema | Qué hacer |
|---|---|
| `Error: connect ECONNREFUSED 127.0.0.1:8545` | No está corriendo `npm run node` en la terminal 1: levantarlo, correr `npm run inicializar` y repetir |
| *No hay contratos desplegados* o *Los contratos de despliegue.json no están en esta red* | Falta la inicialización o se reinició el nodo: correr `npm run inicializar` |
| `Cannot find module` | Falta instalar: `npm ci` dentro de `prototipo/` |
| Se quiere repetir una campaña | Volver a correr el mismo comando: crea un canje nuevo sobre los mismos contratos |
| Falla el nodo | Correr `npm run demo` (red en memoria, sin nodo): las tres partes seguidas en unos segundos |
| Falla la notebook | Plan C: Remix, siguiendo `README.md` |

## Preguntas probables

| Pregunta | Respuesta corta |
|---|---|
| ¿Por qué Hardhat y no Besu? | La consigna admite un entorno local; Hardhat ejecuta la misma EVM que Besu y permite adelantar el reloj. Para Besu solo cambia la red en `hardhat.config.js` |
| ¿Dónde están las claves? ¿Usaron MetaMask? | No hace falta billetera: Hardhat crea cuentas de prueba y firma con ellas. Son públicas y no van en el ZIP; en el consorcio cada organización firmaría con una billetera institucional |
| ¿Quién llama a `cerrarPeriodoCritico`? | Cualquiera: el contrato verifica la fecha. En producción, un servicio del consorcio |
| ¿Qué pasa si la aseguradora no paga? | Pasados 15 días, cualquiera llama a `notificarPlazoIncumplido` y queda registrado el evento `PlazoIncumplido` |
| ¿Se puede cambiar el contrato? | No a propósito: nadie cambia las reglas de un canje firmado. Las mejoras van en una versión nueva |
| ¿Cómo sabe el contrato la hora? | Por `block.timestamp`, la hora del bloque |

## Salida de referencia (material complementario)

Salidas reales de los tres comandos, ejecutados el 15/11/2026 en orden sobre un nodo recién iniciado (`npm run node`). Sirven para comparar durante la clase; no reemplazan la ejecución en vivo.

### `npm run inicializar`

```text
Red: localhost

==============================================================================
PARTE 1. INICIALIZACIÓN: despliegue de los contratos, roles y fondos
==============================================================================

------------------------------------------------------------------------------
CASO 1. Despliegue de los contratos
------------------------------------------------------------------------------
  Operación:                   desplegar PesoToken(banco) y ECanjeProtegido(token, admin)
  Ejecuta:                     admin del consorcio
  Esperado:                    dos contratos con su dirección en la red
  PesoToken (ARSt):            0x5FbDB2315678afecb367f032d93F642f64180aa3
  ECanjeProtegido:             0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512
  [OK]    los dos contratos tienen código en la red

------------------------------------------------------------------------------
CASO 2. Asignación de roles a cada participante
------------------------------------------------------------------------------
  Operación:                   grantRole(rol, cuenta) para cada participante
  Ejecuta:                     admin del consorcio
  Esperado:                    seis cuentas con rol; el intruso sin rol
  Rol productor:               0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC
  Rol agronomía:               0x90F79bf6EB2c4f870365E785982E1f101E93b906
  Rol aseguradora:             0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65
  Rol acopio:                  0x9965507D1a55bcC2695C58ba16FB37d819B0A4dc
  Rol oráculo primario:        0x976EA74026E726554dB657fA54763abd0C3a0aa9
  Rol oráculo alternativo:     0x14dC79964da2C08b23698B3D3cc7Ca32193d9955
  Cuenta sin rol:              0x23618e81E3f5cdF7f54C3d65f7FBc0aBf5B21E8f (intruso)
  [OK]    cada participante tiene su rol

------------------------------------------------------------------------------
CASO 3. Fondos: el banco emite pesos tokenizados para la aseguradora
------------------------------------------------------------------------------
  Operación:                   emitir(aseguradora, $ 200 M) y approve(contrato)
  Ejecuta:                     banco y aseguradora
  Esperado:                    aseguradora con $ 200 M; el contrato autorizado a debitar
  Obtenido:                    saldo de la aseguradora $ 200.000.000
  [OK]    la aseguradora tiene $ 200 M en pesos tokenizados

  Direcciones guardadas en:    despliegue.json (las usan las campañas)

------------------------------------------------------------------------------
RESULTADO: 3 verificaciones correctas, 0 fallidas.
------------------------------------------------------------------------------
```

### `npm run campania:normal`

```text
Red: localhost

==============================================================================
CAMPAÑA: AÑO NORMAL (índice 300)
==============================================================================
  Índice que va a informar:    300 (el oráculo lo informa en el caso 7)
  Regla de la póliza:          índice ≥ 600 → 50 % · índice ≥ 800 → 100 % de $ 120.000.000
  Quién decide:                el contrato, al cerrar el período crítico (caso 8)

------------------------------------------------------------------------------
CASO 1. Creación del activo: el productor solicita el canje
------------------------------------------------------------------------------
  Operación:                   crearSolicitud(agronomía, lote, "soja", 2026, 210.000 kg)
  Ejecuta:                     productor
  Esperado:                    canje nuevo en Solicitado; evento CanjeSolicitado
  Obtenido:                    canje n.º 1 · estado Solicitado · deuda 210 t
  [OK]    el canje 1 existe y está en Solicitado

------------------------------------------------------------------------------
CASO 2. Rechazo por falta de permisos
------------------------------------------------------------------------------
  Operación:                   A) crearSolicitud(...) desde una cuenta sin PRODUCTOR_ROLE
  Ejecuta:                     intruso
  Esperado:                    AccessControlUnauthorizedAccount
  Revertida con:               AccessControlUnauthorizedAccount(0x23618e81E3f5cdF7f54C3d65f7FBc0aBf5B21E8f, 0x0918bd1fbce554f78f0248a906c12b0d9c81164fc00cd1466d94dbac52257152)
  [OK]    la transacción se revirtió con AccessControlUnauthorizedAccount
  Operación:                   B) aprobarCanje(1, …) por alguien que no es la agronomía del canje
  Ejecuta:                     productor
  Esperado:                    NoEsLaParte
  Revertida con:               NoEsLaParte(1, 0x90F79bf6EB2c4f870365E785982E1f101E93b906, 0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC)
  [OK]    la transacción se revirtió con NoEsLaParte
  [OK]    el canje sigue en Solicitado (nada cambió)

------------------------------------------------------------------------------
CASO 3. Recorrido válido: la agronomía aprueba el canje
------------------------------------------------------------------------------
  Operación:                   aprobarCanje(1, aseguradora, acopio, $ 400.000/t, fecha límite)
  Ejecuta:                     agronomía
  Esperado:                    Solicitado → Aprobado
  Obtenido:                    estado Aprobado
  [OK]    Solicitado → Aprobado
```

```text
------------------------------------------------------------------------------
CASO 4. Rechazo de una transición inválida
------------------------------------------------------------------------------
  Operación:                   entregarInsumos(1, remito) sin póliza emitida
  Ejecuta:                     agronomía
  Esperado:                    EstadoInvalido (está en 1 Aprobado; hace falta 2 Asegurado)
  Revertida con:               EstadoInvalido(1, 1, 2)
  [OK]    la transacción se revirtió con EstadoInvalido
  [OK]    el canje sigue en Aprobado

------------------------------------------------------------------------------
CASO 5. Recorrido válido: póliza e insumos
------------------------------------------------------------------------------
  Operación:                   emitirPoliza(1, $ 120 M, tramos [600 → 50 %, 800 → 100 %], prima 12 t)
  Ejecuta:                     aseguradora
  Esperado:                    Aprobado → Asegurado; la prima se suma a la deuda (222 t)
  Obtenido:                    estado Asegurado · deuda 222 t
  [OK]    Aprobado → Asegurado; deuda 222 t
  Operación:                   entregarInsumos(1, remito)
  Ejecuta:                     agronomía
  Esperado:                    Asegurado → Vigente
  Obtenido:                    estado Vigente
  [OK]    Asegurado → Vigente

------------------------------------------------------------------------------
CASO 6. Consulta de datos y estado del activo (funciones view, sin gas)
------------------------------------------------------------------------------
  Operación:                   verCanje(1), verPoliza(1), calcularIndemnizacion(1, 300)
  Ejecuta:                     cualquiera (consulta)
  Esperado:                    datos del canje y de la póliza
  Productor:                   0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC
  Agronomía:                   0x90F79bf6EB2c4f870365E785982E1f101E93b906
  Cultivo / campaña:           soja 2026
  Deuda:                       222 t = $ 88.800.000
  Estado:                      Vigente
  Suma asegurada:              $ 120.000.000
  Si el índice es 300:         tramo 0 · indemnización $ 0
  [OK]    con índice 300 la póliza pagaría $ 0
```

```text
------------------------------------------------------------------------------
CASO 7. El oráculo informa el índice de sequía: 300
------------------------------------------------------------------------------
  Reloj:                       adelantado al día 40 del período crítico
  Operación:                   reportarIndice(1, fecha, 300)
  Ejecuta:                     oráculo primario
  Esperado:                    índice 300 registrado
  Obtenido:                    índice registrado 300
  [OK]    el oráculo primario registró 300
  Operación:                   reportarIndice(1, fecha, 100) mientras el primario está informando
  Ejecuta:                     oráculo alternativo
  Esperado:                    OraculoNoHabilitado
  Revertida con:               OraculoNoHabilitado(0x14dC79964da2C08b23698B3D3cc7Ca32193d9955)
  [OK]    la transacción se revirtió con OraculoNoHabilitado

------------------------------------------------------------------------------
CASO 8. Cierre del período crítico: el contrato decide
------------------------------------------------------------------------------
  Reloj:                       adelantado al fin del período crítico
  Operación:                   cerrarPeriodoCritico(1)
  Ejecuta:                     cualquiera (el contrato controla la fecha)
  Esperado:                    Vigente → EnCosecha; indemnización $ 0
  Obtenido:                    estado EnCosecha · indemnización $ 0
  Decisión del contrato:       índice 300 < 600: NO HAY SINIESTRO, la póliza no paga
  [OK]    Vigente → EnCosecha sin indemnización

------------------------------------------------------------------------------
CASO 9. La póliza no se ejecuta: la deuda se paga con la cosecha
------------------------------------------------------------------------------
  Operación:                   pagarIndemnizacion(1)
  Ejecuta:                     aseguradora
  Esperado:                    EstadoInvalido (está en 6 EnCosecha; haría falta 4 Siniestrado)
  Revertida con:               EstadoInvalido(1, 6, 4)
  [OK]    la transacción se revirtió con EstadoInvalido
  Operación:                   entregarGranos(1, 100 t, carta de porte)
  Ejecuta:                     acopio
  Esperado:                    entrega parcial: sigue EnCosecha
  Obtenido:                    estado EnCosecha · deuda 122 t
  Operación:                   entregarGranos(1, 122 t, carta de porte)
  Ejecuta:                     acopio
  Esperado:                    EnCosecha → Saldado
  Obtenido:                    estado Saldado · deuda 0 t
  [OK]    la deuda en granos quedó cancelada: Saldado
```

```text
------------------------------------------------------------------------------
CASO 10. Resumen de la campaña
------------------------------------------------------------------------------
  Índice informado:            300
  Decisión del contrato:       no hubo siniestro: la póliza no se ejecutó
  Pagó la aseguradora:         $ 0
  Granos entregados:           222 t
  Estado final:                canje n.º 1 en Saldado
  Recorrido:                   Solicitado → Aprobado → Asegurado → Vigente →
                               EnCosecha → Saldado
  [OK]    el canje terminó Saldado

------------------------------------------------------------------------------
RESULTADO: 16 verificaciones correctas, 0 fallidas.
------------------------------------------------------------------------------
```

### `npm run campania:sequia`

```text
Red: localhost

==============================================================================
CAMPAÑA: SEQUÍA SEVERA (índice 850)
==============================================================================
  Índice que va a informar:    850 (el oráculo lo informa en el caso 7)
  Regla de la póliza:          índice ≥ 600 → 50 % · índice ≥ 800 → 100 % de $ 120.000.000
  Quién decide:                el contrato, al cerrar el período crítico (caso 8)

------------------------------------------------------------------------------
CASO 1. Creación del activo: el productor solicita el canje
------------------------------------------------------------------------------
  Operación:                   crearSolicitud(agronomía, lote, "soja", 2026, 210.000 kg)
  Ejecuta:                     productor
  Esperado:                    canje nuevo en Solicitado; evento CanjeSolicitado
  Obtenido:                    canje n.º 2 · estado Solicitado · deuda 210 t
  [OK]    el canje 2 existe y está en Solicitado

------------------------------------------------------------------------------
CASO 2. Rechazo por falta de permisos
------------------------------------------------------------------------------
  Operación:                   A) crearSolicitud(...) desde una cuenta sin PRODUCTOR_ROLE
  Ejecuta:                     intruso
  Esperado:                    AccessControlUnauthorizedAccount
  Revertida con:               AccessControlUnauthorizedAccount(0x23618e81E3f5cdF7f54C3d65f7FBc0aBf5B21E8f, 0x0918bd1fbce554f78f0248a906c12b0d9c81164fc00cd1466d94dbac52257152)
  [OK]    la transacción se revirtió con AccessControlUnauthorizedAccount
  Operación:                   B) aprobarCanje(2, …) por alguien que no es la agronomía del canje
  Ejecuta:                     productor
  Esperado:                    NoEsLaParte
  Revertida con:               NoEsLaParte(2, 0x90F79bf6EB2c4f870365E785982E1f101E93b906, 0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC)
  [OK]    la transacción se revirtió con NoEsLaParte
  [OK]    el canje sigue en Solicitado (nada cambió)

------------------------------------------------------------------------------
CASO 3. Recorrido válido: la agronomía aprueba el canje
------------------------------------------------------------------------------
  Operación:                   aprobarCanje(2, aseguradora, acopio, $ 400.000/t, fecha límite)
  Ejecuta:                     agronomía
  Esperado:                    Solicitado → Aprobado
  Obtenido:                    estado Aprobado
  [OK]    Solicitado → Aprobado
```

```text
------------------------------------------------------------------------------
CASO 4. Rechazo de una transición inválida
------------------------------------------------------------------------------
  Operación:                   entregarInsumos(2, remito) sin póliza emitida
  Ejecuta:                     agronomía
  Esperado:                    EstadoInvalido (está en 1 Aprobado; hace falta 2 Asegurado)
  Revertida con:               EstadoInvalido(2, 1, 2)
  [OK]    la transacción se revirtió con EstadoInvalido
  [OK]    el canje sigue en Aprobado

------------------------------------------------------------------------------
CASO 5. Recorrido válido: póliza e insumos
------------------------------------------------------------------------------
  Operación:                   emitirPoliza(2, $ 120 M, tramos [600 → 50 %, 800 → 100 %], prima 12 t)
  Ejecuta:                     aseguradora
  Esperado:                    Aprobado → Asegurado; la prima se suma a la deuda (222 t)
  Obtenido:                    estado Asegurado · deuda 222 t
  [OK]    Aprobado → Asegurado; deuda 222 t
  Operación:                   entregarInsumos(2, remito)
  Ejecuta:                     agronomía
  Esperado:                    Asegurado → Vigente
  Obtenido:                    estado Vigente
  [OK]    Asegurado → Vigente

------------------------------------------------------------------------------
CASO 6. Consulta de datos y estado del activo (funciones view, sin gas)
------------------------------------------------------------------------------
  Operación:                   verCanje(2), verPoliza(2), calcularIndemnizacion(2, 850)
  Ejecuta:                     cualquiera (consulta)
  Esperado:                    datos del canje y de la póliza
  Productor:                   0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC
  Agronomía:                   0x90F79bf6EB2c4f870365E785982E1f101E93b906
  Cultivo / campaña:           soja 2026
  Deuda:                       222 t = $ 88.800.000
  Estado:                      Vigente
  Suma asegurada:              $ 120.000.000
  Si el índice es 850:         tramo 2 · indemnización $ 120.000.000
  [OK]    con índice 850 la póliza pagaría $ 120.000.000
```

```text
------------------------------------------------------------------------------
CASO 7. El oráculo informa el índice de sequía: 850
------------------------------------------------------------------------------
  Reloj:                       adelantado al día 40 del período crítico
  Operación:                   reportarIndice(2, fecha, 850)
  Ejecuta:                     oráculo primario
  Esperado:                    índice 850 registrado
  Obtenido:                    índice registrado 850
  [OK]    el oráculo primario registró 850
  Operación:                   reportarIndice(2, fecha, 100) mientras el primario está informando
  Ejecuta:                     oráculo alternativo
  Esperado:                    OraculoNoHabilitado
  Revertida con:               OraculoNoHabilitado(0x14dC79964da2C08b23698B3D3cc7Ca32193d9955)
  [OK]    la transacción se revirtió con OraculoNoHabilitado

------------------------------------------------------------------------------
CASO 8. Cierre del período crítico: el contrato decide
------------------------------------------------------------------------------
  Reloj:                       adelantado al fin del período crítico
  Operación:                   cerrarPeriodoCritico(2)
  Ejecuta:                     cualquiera (el contrato controla la fecha)
  Esperado:                    Vigente → Siniestrado; indemnización $ 120.000.000
  Obtenido:                    estado Siniestrado · indemnización $ 120.000.000
  Decisión del contrato:       índice 850 ≥ 800: HAY SINIESTRO, la póliza paga 100 % = $ 120.000.000
  [OK]    Vigente → Siniestrado con la indemnización de la póliza
```

```text
------------------------------------------------------------------------------
CASO 9. Se ejecuta la póliza: pago, liquidación (primero la deuda) y cobro
------------------------------------------------------------------------------
  Operación:                   pagarIndemnizacion(2)
  Ejecuta:                     aseguradora
  Esperado:                    Siniestrado → Indemnizado; el contrato recibe $ 120.000.000
  Obtenido:                    estado Indemnizado · saldo de la aseguradora $ 80.000.000
  [OK]    Siniestrado → Indemnizado
  Operación:                   liquidarCanje(2)
  Ejecuta:                     cualquiera
  Esperado:                    $ 88.800.000 a la agronomía y $ 31.200.000 al productor
  Obtenido:                    estado Saldado
    a la agronomía (deuda):    $ 88.800.000
    al productor (saldo):      $ 31.200.000
    deuda restante:            0 t
  [OK]    la indemnización cancela primero la deuda y el resto es del productor
  Operación:                   retirarFondos()
  Ejecuta:                     agronomía y productor
  Esperado:                    cada uno recibe lo que le asignó la liquidación
  Obtenido:                    agronomía cobró $ 88.800.000 · productor cobró $ 31.200.000
  [OK]    lo cobrado coincide con la liquidación
  Operación:                   retirarFondos() por segunda vez
  Ejecuta:                     agronomía
  Esperado:                    NadaParaRetirar
  Revertida con:               NadaParaRetirar()
  [OK]    la transacción se revirtió con NadaParaRetirar

------------------------------------------------------------------------------
CASO 10. Resumen de la campaña
------------------------------------------------------------------------------
  Índice informado:            850
  Decisión del contrato:       hubo siniestro: la póliza se ejecutó
  Pagó la aseguradora:         $ 120.000.000
  Granos entregados:           0 t
  Estado final:                canje n.º 2 en Saldado
  Recorrido:                   Solicitado → Aprobado → Asegurado → Vigente →
                               Siniestrado → Indemnizado → Saldado
  [OK]    el canje terminó Saldado

------------------------------------------------------------------------------
RESULTADO: 18 verificaciones correctas, 0 fallidas.
------------------------------------------------------------------------------
```
