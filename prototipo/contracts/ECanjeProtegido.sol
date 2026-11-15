// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/**
 * @title e-CanjeProtegido
 * @notice Canje de insumos por granos con cobertura paramétrica de sequía embebida.
 *         Si el índice de sequía alcanza un tramo de la póliza, la indemnización cancela
 *         primero la deuda del canje con la agronomía y el saldo queda para el productor.
 * @dev Prototipo del TP4 (Desarrollo con Tecnologías Blockchain, UTN FRC, 2026).
 *      Implementa el DTE del modelo: cada función es un evento y solo se acepta en el
 *      estado y con el rol indicados. Patrones aplicados:
 *      1. Máquina de estados: enum Estado + modificador enEstado
 *      2. Restricción de acceso: roles de AccessControl + control de la parte de cada canje
 *      3. Oráculo con proveedor alternativo (Res. SSN 315/2026): el alternativo solo informa
 *         si el primario no reportó en DIAS_SIN_DATO_PRIMARIO
 *      4. Pago por retiro: liquidarCanje asigna saldos y cada parte los retira con retirarFondos
 *      5. Checks-effects-interactions + ReentrancyGuard en todo movimiento de fondos
 *      6. Parada de emergencia: Pausable (los retiros siguen habilitados)
 *      Unidades: toneladas en kg; dinero en centavos del token de pesos; índice de 0 a 1000;
 *      porcentajes en puntos básicos (10000 = 100 %).
 */
contract ECanjeProtegido is AccessControl, Pausable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // ============================================================
    //  Roles
    // ============================================================

    bytes32 public constant PRODUCTOR_ROLE = keccak256("PRODUCTOR_ROLE");
    bytes32 public constant AGRONOMIA_ROLE = keccak256("AGRONOMIA_ROLE");
    bytes32 public constant ASEGURADORA_ROLE = keccak256("ASEGURADORA_ROLE");
    bytes32 public constant ACOPIO_ROLE = keccak256("ACOPIO_ROLE");
    bytes32 public constant ORACULO_ROLE = keccak256("ORACULO_ROLE");

    // ============================================================
    //  Parámetros
    // ============================================================

    /// @notice Plazo máximo de pago de la indemnización (Res. SSN 315/2026, Anexo, punto 3)
    uint64 public constant PLAZO_PAGO = 15 days;
    /// @notice Días sin dato del proveedor primario para habilitar al alternativo
    uint64 public constant DIAS_SIN_DATO_PRIMARIO = 5 days;
    uint16 public constant INDICE_MAX = 1000;
    uint16 public constant BPS = 10000;

    // ============================================================
    //  Tipos
    // ============================================================

    enum Estado {
        Solicitado,
        Aprobado,
        Asegurado,
        Vigente,
        Siniestrado,
        Indemnizado,
        EnCosecha,
        Saldado,
        Rechazado,
        EnMora
    }

    /// @notice Datos del canje (activo lógico: crédito de la agronomía sobre un lote y una campaña)
    struct Canje {
        address productor;
        address agronomia;
        address aseguradora;
        address acopio;
        bytes32 lote;            // hash del polígono georreferenciado del lote
        string cultivo;
        uint16 campania;
        bytes32 insumos;         // hash del detalle de insumos y del remito
        uint256 deudaKg;         // toneladas adeudadas en kg (incluye la prima)
        uint256 precioCanje;     // centavos por tonelada pactados en el canje
        uint64 fechaLimiteEntrega;
        Estado estado;
    }

    /// @notice Condiciones de la póliza paramétrica (Res. SSN 315/2026, Anexo, puntos 2 y 4)
    struct Poliza {
        bytes32 idPoliza;
        address proveedorPrimario;
        address proveedorAlternativo;
        uint64 inicioPeriodo;
        uint64 finPeriodo;
        uint16[] umbrales;       // valor del índice que activa cada tramo (creciente)
        uint16[] porcentajes;    // % de la suma asegurada por tramo, en puntos básicos
        uint256 sumaAsegurada;   // centavos
        uint256 primaKg;
        bytes32 condiciones;     // hash de condiciones, riesgo de base y frecuencia histórica
    }

    /// @notice Datos del índice y de la liquidación (a disposición del asegurado y de la SSN)
    struct Liquidacion {
        uint16 valorIndice;
        address fuenteIndice;
        uint64 fechaIndice;
        uint64 ultimoReportePrimario;
        uint64 fechaSiniestro;
        uint256 montoIndemnizacion;
        uint256 montoAplicadoDeuda;
        uint256 saldoProductor;
        bool plazoIncumplidoNotificado;
    }

    // ============================================================
    //  Estado del contrato
    // ============================================================

    IERC20 public immutable pesoToken;
    uint256 public cantidadCanjes;

    mapping(uint256 => Canje) private _canjes;
    mapping(uint256 => Poliza) private _polizas;
    mapping(uint256 => Liquidacion) private _liquidaciones;

    /// @notice Fondos asignados a cada cuenta, pendientes de retiro (pago por retiro)
    mapping(address => uint256) public fondosPendientes;

    // ============================================================
    //  Errores
    // ============================================================

    error CanjeInexistente(uint256 idCanje);
    error EstadoInvalido(uint256 idCanje, Estado actual, Estado esperado);
    error NoEsLaParte(uint256 idCanje, address esperada, address recibida);
    error RolFaltante(address cuenta, bytes32 rol);
    error ParametroInvalido(string detalle);
    error FueraDePlazo(string detalle);
    error OraculoNoHabilitado(address cuenta);
    error SinDatoDelIndice(uint256 idCanje);
    error NadaParaRetirar();

    // ============================================================
    //  Eventos
    // ============================================================

    event EstadoCambiado(uint256 indexed idCanje, Estado desde, Estado hacia);
    event CanjeSolicitado(uint256 indexed idCanje, address indexed productor, address indexed agronomia, uint256 deudaKg);
    event CanjeAprobado(uint256 indexed idCanje, address aseguradora, address acopio, uint256 precioCanje);
    event CanjeRechazado(uint256 indexed idCanje, string motivo);
    event PolizaEmitida(uint256 indexed idCanje, bytes32 idPoliza, uint256 sumaAsegurada, uint256 primaKg);
    event InsumosEntregados(uint256 indexed idCanje, bytes32 remito);
    event IndiceReportado(uint256 indexed idCanje, uint64 fecha, uint16 valor, address fuente);
    event PeriodoCerrado(uint256 indexed idCanje, uint16 valorIndice, uint256 montoIndemnizacion);
    event IndemnizacionPagada(uint256 indexed idCanje, uint256 monto, bool enPlazo);
    event PlazoIncumplido(uint256 indexed idCanje, uint64 fechaSiniestro, uint64 fechaConstatacion);
    event CanjeLiquidado(uint256 indexed idCanje, uint256 aplicadoDeuda, uint256 saldoProductor, uint256 deudaKgRestante);
    event GranosEntregados(uint256 indexed idCanje, uint256 kg, bytes32 cartaPorte, uint256 deudaKgRestante);
    event MoraDeclarada(uint256 indexed idCanje, uint256 deudaKg);
    event FondosRetirados(address indexed cuenta, uint256 monto);

    // ============================================================
    //  Modificadores
    // ============================================================

    modifier existe(uint256 idCanje) {
        if (_canjes[idCanje].productor == address(0)) revert CanjeInexistente(idCanje);
        _;
    }

    modifier enEstado(uint256 idCanje, Estado esperado) {
        Estado actual = _canjes[idCanje].estado;
        if (actual != esperado) revert EstadoInvalido(idCanje, actual, esperado);
        _;
    }

    modifier soloParte(uint256 idCanje, address esperada) {
        if (msg.sender != esperada) revert NoEsLaParte(idCanje, esperada, msg.sender);
        _;
    }

    // ============================================================
    //  Constructor y administración del consorcio
    // ============================================================

    /**
     * @param _pesoToken Token ERC-20 de pesos tokenizados (emitido por el banco miembro)
     * @param admin Cuenta del consorcio que registra participantes y puede pausar
     */
    constructor(IERC20 _pesoToken, address admin) {
        pesoToken = _pesoToken;
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
    }

    /// @notice Parada de emergencia (por ejemplo, ante una falla de los dos oráculos)
    function pausar() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _pause();
    }

    function reanudar() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }

    // ============================================================
    //  Eventos del DTE
    // ============================================================

    /**
     * @notice Evento crearSolicitud: el productor pide el canje con cobertura (● → Solicitado)
     * @return idCanje Identificador asignado
     */
    function crearSolicitud(
        address agronomia,
        bytes32 lote,
        string calldata cultivo,
        uint16 campania,
        uint256 deudaKg
    ) external whenNotPaused onlyRole(PRODUCTOR_ROLE) returns (uint256 idCanje) {
        _exigirRol(agronomia, AGRONOMIA_ROLE);
        if (deudaKg == 0) revert ParametroInvalido("deudaKg");
        if (lote == bytes32(0)) revert ParametroInvalido("lote");

        idCanje = ++cantidadCanjes;
        Canje storage c = _canjes[idCanje];
        c.productor = msg.sender;
        c.agronomia = agronomia;
        c.lote = lote;
        c.cultivo = cultivo;
        c.campania = campania;
        c.deudaKg = deudaKg;
        c.estado = Estado.Solicitado;

        emit CanjeSolicitado(idCanje, msg.sender, agronomia, deudaKg);
    }

    /// @notice Evento aprobarCanje: la agronomía acepta el crédito (Solicitado → Aprobado)
    function aprobarCanje(
        uint256 idCanje,
        address aseguradora,
        address acopio,
        uint256 precioCanje,
        uint64 fechaLimiteEntrega
    )
        external
        whenNotPaused
        existe(idCanje)
        enEstado(idCanje, Estado.Solicitado)
        soloParte(idCanje, _canjes[idCanje].agronomia)
    {
        _exigirRol(aseguradora, ASEGURADORA_ROLE);
        _exigirRol(acopio, ACOPIO_ROLE);
        if (precioCanje == 0) revert ParametroInvalido("precioCanje");
        if (fechaLimiteEntrega <= block.timestamp) revert ParametroInvalido("fechaLimiteEntrega");

        Canje storage c = _canjes[idCanje];
        c.aseguradora = aseguradora;
        c.acopio = acopio;
        c.precioCanje = precioCanje;
        c.fechaLimiteEntrega = fechaLimiteEntrega;
        _cambiarEstado(idCanje, Estado.Aprobado);

        emit CanjeAprobado(idCanje, aseguradora, acopio, precioCanje);
    }

    /// @notice Evento rechazarCanje: la agronomía no aprueba el crédito (Solicitado → Rechazado)
    function rechazarCanje(uint256 idCanje, string calldata motivo)
        external
        whenNotPaused
        existe(idCanje)
        enEstado(idCanje, Estado.Solicitado)
        soloParte(idCanje, _canjes[idCanje].agronomia)
    {
        _cambiarEstado(idCanje, Estado.Rechazado);
        emit CanjeRechazado(idCanje, motivo);
    }

    /**
     * @notice Evento emitirPoliza: la aseguradora emite la póliza paramétrica (Aprobado → Asegurado).
     *         La prima se financia dentro del canje: se suma a la deuda en kg.
     */
    function emitirPoliza(uint256 idCanje, Poliza calldata condiciones)
        external
        whenNotPaused
        existe(idCanje)
        enEstado(idCanje, Estado.Aprobado)
        soloParte(idCanje, _canjes[idCanje].aseguradora)
    {
        Canje storage c = _canjes[idCanje];
        _validarPoliza(condiciones, c.fechaLimiteEntrega);

        _polizas[idCanje] = condiciones;
        c.deudaKg += condiciones.primaKg;
        _cambiarEstado(idCanje, Estado.Asegurado);

        emit PolizaEmitida(idCanje, condiciones.idPoliza, condiciones.sumaAsegurada, condiciones.primaKg);
    }

    /// @notice Evento entregarInsumos: la agronomía entrega los insumos (Asegurado → Vigente)
    function entregarInsumos(uint256 idCanje, bytes32 remito)
        external
        whenNotPaused
        existe(idCanje)
        enEstado(idCanje, Estado.Asegurado)
        soloParte(idCanje, _canjes[idCanje].agronomia)
    {
        if (block.timestamp >= _polizas[idCanje].inicioPeriodo) revert FueraDePlazo("periodo critico iniciado");
        if (remito == bytes32(0)) revert ParametroInvalido("remito");

        _canjes[idCanje].insumos = remito;
        _cambiarEstado(idCanje, Estado.Vigente);

        emit InsumosEntregados(idCanje, remito);
    }

    /**
     * @notice Evento reportarIndice: el oráculo informa el índice del lote (Vigente → Vigente).
     *         El proveedor alternativo solo es aceptado si el primario no informó en
     *         DIAS_SIN_DATO_PRIMARIO. Se conserva el último valor informado (índice acumulado).
     */
    function reportarIndice(uint256 idCanje, uint64 fecha, uint16 valor)
        external
        whenNotPaused
        existe(idCanje)
        enEstado(idCanje, Estado.Vigente)
    {
        Poliza storage p = _polizas[idCanje];
        Liquidacion storage l = _liquidaciones[idCanje];

        if (msg.sender == p.proveedorPrimario) {
            l.ultimoReportePrimario = uint64(block.timestamp);
        } else if (msg.sender == p.proveedorAlternativo) {
            uint64 desde = l.ultimoReportePrimario > p.inicioPeriodo ? l.ultimoReportePrimario : p.inicioPeriodo;
            if (block.timestamp < desde + DIAS_SIN_DATO_PRIMARIO) revert OraculoNoHabilitado(msg.sender);
        } else {
            revert OraculoNoHabilitado(msg.sender);
        }

        if (fecha < p.inicioPeriodo || fecha > p.finPeriodo) revert FueraDePlazo("fecha fuera del periodo critico");
        if (fecha > block.timestamp) revert ParametroInvalido("fecha futura");
        if (fecha <= l.fechaIndice) revert ParametroInvalido("fecha no posterior al ultimo reporte");
        if (valor > INDICE_MAX) revert ParametroInvalido("valor");

        l.valorIndice = valor;
        l.fuenteIndice = msg.sender;
        l.fechaIndice = fecha;

        emit IndiceReportado(idCanje, fecha, valor, msg.sender);
    }

    /**
     * @notice Evento cerrarPeriodoCritico: al terminar el período, el contrato decide
     *         (Vigente → Siniestrado si el índice alcanzó un tramo; Vigente → EnCosecha si no).
     *         Lo puede invocar cualquiera: el contrato verifica la fecha por sí mismo.
     */
    function cerrarPeriodoCritico(uint256 idCanje)
        external
        whenNotPaused
        existe(idCanje)
        enEstado(idCanje, Estado.Vigente)
    {
        if (block.timestamp <= _polizas[idCanje].finPeriodo) revert FueraDePlazo("periodo critico no terminado");
        Liquidacion storage l = _liquidaciones[idCanje];
        if (l.fechaIndice == 0) revert SinDatoDelIndice(idCanje);

        (, uint256 monto) = calcularIndemnizacion(idCanje, l.valorIndice);
        l.montoIndemnizacion = monto;

        if (monto > 0) {
            l.fechaSiniestro = uint64(block.timestamp);
            _cambiarEstado(idCanje, Estado.Siniestrado);
        } else {
            _cambiarEstado(idCanje, Estado.EnCosecha);
        }

        emit PeriodoCerrado(idCanje, l.valorIndice, monto);
    }

    /**
     * @notice Evento pagarIndemnizacion: la aseguradora deposita la indemnización
     *         (Siniestrado → Indemnizado). Requiere approve previo del token de pesos.
     *         Si pasaron más de PLAZO_PAGO desde el siniestro, queda registrado el incumplimiento.
     */
    function pagarIndemnizacion(uint256 idCanje)
        external
        whenNotPaused
        nonReentrant
        existe(idCanje)
        enEstado(idCanje, Estado.Siniestrado)
        soloParte(idCanje, _canjes[idCanje].aseguradora)
    {
        Liquidacion storage l = _liquidaciones[idCanje];
        uint256 monto = l.montoIndemnizacion;
        bool enPlazo = block.timestamp <= l.fechaSiniestro + PLAZO_PAGO;

        // Efectos
        _cambiarEstado(idCanje, Estado.Indemnizado);
        if (!enPlazo) _notificarIncumplimiento(idCanje);
        emit IndemnizacionPagada(idCanje, monto, enPlazo);

        // Interacción
        pesoToken.safeTransferFrom(msg.sender, address(this), monto);
    }

    /**
     * @notice Deja registrado que venció el plazo de pago sin depósito (no cambia el estado).
     *         Lo puede invocar cualquiera, por ejemplo la SSN.
     */
    function notificarPlazoIncumplido(uint256 idCanje)
        external
        existe(idCanje)
        enEstado(idCanje, Estado.Siniestrado)
    {
        Liquidacion storage l = _liquidaciones[idCanje];
        if (block.timestamp <= l.fechaSiniestro + PLAZO_PAGO) revert FueraDePlazo("plazo de pago vigente");
        if (l.plazoIncumplidoNotificado) revert ParametroInvalido("ya notificado");
        _notificarIncumplimiento(idCanje);
    }

    /**
     * @notice Evento liquidarCanje: aplica la indemnización a la deuda (Indemnizado → Saldado
     *         si la cancela; Indemnizado → EnCosecha si queda deuda). Primero cobra la agronomía,
     *         el saldo es del productor. Solo asigna fondos: cada parte los retira después.
     */
    function liquidarCanje(uint256 idCanje)
        external
        whenNotPaused
        existe(idCanje)
        enEstado(idCanje, Estado.Indemnizado)
    {
        Canje storage c = _canjes[idCanje];
        Liquidacion storage l = _liquidaciones[idCanje];

        uint256 deudaPesos = (c.deudaKg * c.precioCanje) / 1000;
        uint256 aplicado = l.montoIndemnizacion < deudaPesos ? l.montoIndemnizacion : deudaPesos;
        uint256 saldo = l.montoIndemnizacion - aplicado;

        if (aplicado == deudaPesos) {
            c.deudaKg = 0;
        } else {
            c.deudaKg -= (aplicado * 1000) / c.precioCanje;
        }

        l.montoAplicadoDeuda = aplicado;
        l.saldoProductor = saldo;
        fondosPendientes[c.agronomia] += aplicado;
        fondosPendientes[c.productor] += saldo;

        _cambiarEstado(idCanje, c.deudaKg == 0 ? Estado.Saldado : Estado.EnCosecha);
        emit CanjeLiquidado(idCanje, aplicado, saldo, c.deudaKg);
    }

    /**
     * @notice Evento entregarGranos: el acopio registra una entrega (EnCosecha → EnCosecha si es
     *         parcial; EnCosecha → Saldado si cubre la deuda).
     */
    function entregarGranos(uint256 idCanje, uint256 kg, bytes32 cartaPorte)
        external
        whenNotPaused
        existe(idCanje)
        enEstado(idCanje, Estado.EnCosecha)
        soloParte(idCanje, _canjes[idCanje].acopio)
    {
        if (kg == 0) revert ParametroInvalido("kg");
        if (cartaPorte == bytes32(0)) revert ParametroInvalido("cartaPorte");

        Canje storage c = _canjes[idCanje];
        c.deudaKg = kg >= c.deudaKg ? 0 : c.deudaKg - kg;

        emit GranosEntregados(idCanje, kg, cartaPorte, c.deudaKg);
        if (c.deudaKg == 0) _cambiarEstado(idCanje, Estado.Saldado);
    }

    /// @notice Evento declararMora: venció la fecha de entrega con deuda (EnCosecha → EnMora)
    function declararMora(uint256 idCanje)
        external
        whenNotPaused
        existe(idCanje)
        enEstado(idCanje, Estado.EnCosecha)
        soloParte(idCanje, _canjes[idCanje].agronomia)
    {
        if (block.timestamp <= _canjes[idCanje].fechaLimiteEntrega) revert FueraDePlazo("fecha de entrega vigente");
        _cambiarEstado(idCanje, Estado.EnMora);
        emit MoraDeclarada(idCanje, _canjes[idCanje].deudaKg);
    }

    /// @notice Pago por retiro: cada parte retira los fondos que le asignó liquidarCanje.
    /// @dev No se bloquea con la pausa, para que nadie quede con fondos retenidos.
    function retirarFondos() external nonReentrant {
        uint256 monto = fondosPendientes[msg.sender];
        if (monto == 0) revert NadaParaRetirar();

        fondosPendientes[msg.sender] = 0;
        emit FondosRetirados(msg.sender, monto);

        pesoToken.safeTransfer(msg.sender, monto);
    }

    // ============================================================
    //  Consultas (dato y cálculo a disposición del asegurado y de la SSN)
    // ============================================================

    function verCanje(uint256 idCanje) external view existe(idCanje) returns (Canje memory) {
        return _canjes[idCanje];
    }

    function verPoliza(uint256 idCanje) external view existe(idCanje) returns (Poliza memory) {
        return _polizas[idCanje];
    }

    function verLiquidacion(uint256 idCanje) external view existe(idCanje) returns (Liquidacion memory) {
        return _liquidaciones[idCanje];
    }

    /**
     * @notice Calcula qué tramo alcanza un valor del índice y cuánto se pagaría.
     * @return tramo Cantidad de tramos alcanzados (0 = sin siniestro)
     * @return monto Indemnización en centavos
     */
    function calcularIndemnizacion(uint256 idCanje, uint16 valor)
        public
        view
        existe(idCanje)
        returns (uint256 tramo, uint256 monto)
    {
        Poliza storage p = _polizas[idCanje];
        for (uint256 i = 0; i < p.umbrales.length; i++) {
            if (valor >= p.umbrales[i]) tramo = i + 1;
        }
        if (tramo > 0) monto = (p.sumaAsegurada * p.porcentajes[tramo - 1]) / BPS;
    }

    // ============================================================
    //  Funciones internas
    // ============================================================

    function _cambiarEstado(uint256 idCanje, Estado hacia) private {
        Estado desde = _canjes[idCanje].estado;
        _canjes[idCanje].estado = hacia;
        emit EstadoCambiado(idCanje, desde, hacia);
    }

    function _notificarIncumplimiento(uint256 idCanje) private {
        Liquidacion storage l = _liquidaciones[idCanje];
        l.plazoIncumplidoNotificado = true;
        emit PlazoIncumplido(idCanje, l.fechaSiniestro, uint64(block.timestamp));
    }

    function _exigirRol(address cuenta, bytes32 rol) private view {
        if (!hasRole(rol, cuenta)) revert RolFaltante(cuenta, rol);
    }

    /// @dev Reglas de la Res. SSN 315/2026: proveedor primario y alternativo, tramos fijos.
    function _validarPoliza(Poliza calldata p, uint64 fechaLimiteEntrega) private view {
        _exigirRol(p.proveedorPrimario, ORACULO_ROLE);
        _exigirRol(p.proveedorAlternativo, ORACULO_ROLE);
        if (p.proveedorPrimario == p.proveedorAlternativo) revert ParametroInvalido("proveedores iguales");
        if (p.inicioPeriodo <= block.timestamp) revert ParametroInvalido("inicioPeriodo");
        if (p.finPeriodo <= p.inicioPeriodo) revert ParametroInvalido("finPeriodo");
        if (p.finPeriodo >= fechaLimiteEntrega) revert ParametroInvalido("finPeriodo posterior a la entrega");
        if (p.sumaAsegurada == 0) revert ParametroInvalido("sumaAsegurada");

        uint256 n = p.umbrales.length;
        if (n == 0 || n != p.porcentajes.length) revert ParametroInvalido("tramos");
        for (uint256 i = 0; i < n; i++) {
            if (p.umbrales[i] > INDICE_MAX) revert ParametroInvalido("umbral");
            if (p.porcentajes[i] == 0 || p.porcentajes[i] > BPS) revert ParametroInvalido("porcentaje");
            if (i > 0 && p.umbrales[i] <= p.umbrales[i - 1]) revert ParametroInvalido("umbrales no crecientes");
            if (i > 0 && p.porcentajes[i] < p.porcentajes[i - 1]) revert ParametroInvalido("porcentajes decrecientes");
        }
    }
}
