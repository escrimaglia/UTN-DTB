# TP5 — Implementación del contrato e-CanjeProtegido (UTN FRC, DTB 5K3, 2026)

| Carpeta / archivo | Qué tiene |
|---|---|
| `consigna.txt` | Consigna del TP5 |
| `prototipo/` | Código del contrato (copiado de `../TP4/prototipo`), pruebas, scripts de la demostración (`scripts/`) y configuración |
| `docs/` | Fuente Markdown y PDF de: documento del desarrollo (entregable), documento técnico (estudio) y guía de demostración (guion de la clase). Estos dos últimos son internos y no van en el ZIP |
| `build/` | `generar.sh` regenera los tres PDF con la estética del TP4; `armar_zip.sh` arma el ZIP. Autónomo: no depende de otras carpetas |
| `ia/registro_uso_ia.md` | Registro de uso de IA |
| `entrega/TP5_Entrega.zip` | ZIP a entregar: `TP5_Desarrollo.pdf` + `prototipo/` sin `node_modules` |

## Cómo correrlo

Los comandos son los mismos en macOS y Windows: todo se ejecuta con scripts de npm.

### 1. Requisitos (una sola vez)

| | macOS | Windows |
|---|---|---|
| Git | `xcode-select --install` o `brew install git` | https://git-scm.com/download/win |
| Node.js 18 o superior (incluye npm) | https://nodejs.org (versión LTS) o `brew install node` | https://nodejs.org (versión LTS, instalador .msi) |

Verificar en una terminal: `node --version` (18 o más) y `npm --version`.

### 2. Clonar e instalar

```bash
git clone <url-del-repo>
cd <carpeta-del-repo>/prototipo
npm ci
```

`npm ci` instala las dependencias exactas de `package-lock.json` en `node_modules/`. La primera vez necesita internet (también para descargar el compilador de Solidity).

### 3. Comandos (dentro de `prototipo/`)

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

### 4. Demo como en clase (dos terminales, ambas en `prototipo/`)

```bash
npm run node               # terminal 1 (queda ocupada con el nodo)
npm run inicializar        # terminal 2: parte 1
npm run campania:normal    # terminal 2: parte 2
npm run campania:sequia    # terminal 2: parte 3
```

El paso a paso de la presentación está en `docs/TP5_Guia_Demostracion.pdf`.

### 5. Antes de entregar: regenerar PDF y ZIP (una sola persona, macOS con Microsoft Word)

El generador toma las fuentes Calibri de Microsoft Word para Mac y los scripts usan `rsync` y `zip`, por eso este paso es solo en macOS. Requiere uv (`brew install uv`). Desde la raíz del repo:

```bash
uv sync                # crea .venv con reportlab (versiones fijadas en uv.lock)
./build/generar.sh     # regenera los tres PDF desde docs/*.md
./build/armar_zip.sh   # arma entrega/TP5_Entrega.zip (el entregable)
```

No se suben `node_modules/` ni `.venv/`: cada uno los crea con `npm ci` y `uv sync`.
