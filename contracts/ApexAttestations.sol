// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title ApexAttestations - registro verificable on-chain de señales y sus resultados
/// @notice El servicio x402 de APEX publica aquí cada señal (sellada con la hora) y, cuando
///         el horizonte vence, su resultado real. Nadie puede reescribir el pasado: el
///         historial de aciertos queda inmutable y público. Es el foso que el tiempo no deja copiar.
contract ApexAttestations {
    address public operator;

    struct Signal {
        bytes32 claimHash;   // hash de (activo, dirección, horizonte, predicción)
        uint64  createdAt;   // sellado temporal de emisión
        uint64  resolvesAt;  // cuándo se puede resolver
        uint8   predicted;   // 1 = sube/operable, 0 = baja/evitar
        uint8   outcome;     // 0 = pendiente, 1 = acertó, 2 = falló
    }

    Signal[] public signals;
    uint256 public hits;
    uint256 public resolved;

    event SignalPosted(uint256 indexed id, bytes32 claimHash, uint64 resolvesAt, uint8 predicted);
    event SignalResolved(uint256 indexed id, uint8 outcome, uint256 hits, uint256 resolved);
    event OperatorChanged(address indexed from, address indexed to);

    modifier onlyOperator() { require(msg.sender == operator, "not operator"); _; }

    constructor() { operator = msg.sender; }

    /// @notice Publica una señal nueva. Devuelve su id inmutable.
    function postSignal(bytes32 claimHash, uint64 resolvesAt, uint8 predicted)
        external onlyOperator returns (uint256 id)
    {
        require(predicted <= 1, "bad predicted");
        id = signals.length;
        signals.push(Signal(claimHash, uint64(block.timestamp), resolvesAt, predicted, 0));
        emit SignalPosted(id, claimHash, resolvesAt, predicted);
    }

    /// @notice Resuelve una señal pasada: 1 acertó, 2 falló. Solo una vez, solo tras el horizonte.
    function resolveSignal(uint256 id, uint8 outcome) external onlyOperator {
        require(id < signals.length, "no id");
        Signal storage s = signals[id];
        require(s.outcome == 0, "already resolved");
        require(outcome == 1 || outcome == 2, "bad outcome");
        require(block.timestamp >= s.resolvesAt, "too early");
        s.outcome = outcome;
        resolved += 1;
        if (outcome == 1) hits += 1;
        emit SignalResolved(id, outcome, hits, resolved);
    }

    /// @notice Tasa de acierto verificable (en basis points) y conteos. Cualquiera puede leerla.
    function accuracyBps() external view returns (uint256 bps, uint256 _hits, uint256 _resolved) {
        _hits = hits; _resolved = resolved;
        bps = resolved == 0 ? 0 : (hits * 10000) / resolved;
    }

    function total() external view returns (uint256) { return signals.length; }

    function setOperator(address next) external onlyOperator {
        require(next != address(0), "zero");
        emit OperatorChanged(operator, next);
        operator = next;
    }
}
