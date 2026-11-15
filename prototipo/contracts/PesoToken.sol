// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title PesoToken
 * @notice Peso tokenizado de prueba: representa pesos depositados 1 a 1 en el banco miembro
 *         del consorcio. Solo el banco (owner) puede emitir.
 * @dev Solo para el prototipo. Usa 2 decimales: 1 unidad = 1 centavo.
 */
contract PesoToken is ERC20, Ownable {
    constructor(address banco) ERC20("Peso tokenizado", "ARSt") Ownable(banco) {}

    function decimals() public pure override returns (uint8) {
        return 2;
    }

    /// @notice El banco emite pesos tokenizados contra un depósito en pesos
    function emitir(address cuenta, uint256 monto) external onlyOwner {
        _mint(cuenta, monto);
    }
}
