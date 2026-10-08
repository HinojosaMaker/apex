// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice Flash loan de Balancer V2 (fee 0 en Base) -> ejecuta una ruta de swaps ->
///         exige ganancia >= minProfit o REVIERTE (nunca pierde en el trade) ->
///         barre la ganancia a `profitSink` (tu wallet principal).
///         Capital: lo presta el vault (cero tuyo). Gas: lo patrocina el Paymaster (cero tuyo).
interface IBalancerVault {
    function flashLoan(address recipient, address[] memory tokens, uint256[] memory amounts, bytes memory userData) external;
}
interface IERC20 {
    function balanceOf(address) external view returns (uint256);
    function transfer(address, uint256) external returns (bool);
    function approve(address, uint256) external returns (bool);
}

contract FlashArbExecutor {
    address public owner;
    address public profitSink;                 // a donde va la ganancia (tu wallet)
    IBalancerVault public constant VAULT = IBalancerVault(0xBA12222222228d8Ba445958a75a0704d566BF2C8); // Balancer V2 (misma dir en Base)

    event Profit(address indexed token, uint256 amount);

    modifier onlyOwner() { require(msg.sender == owner, "not owner"); _; }

    constructor(address _profitSink) { owner = msg.sender; profitSink = _profitSink; }
    function setProfitSink(address s) external onlyOwner { profitSink = s; }
    function setOwner(address o) external onlyOwner { require(o != address(0)); owner = o; }

    /// @param token    activo a pedir prestado (p.ej. WETH/USDC en Base)
    /// @param amount   cuanto pedir
    /// @param minProfit ganancia minima exigida tras repagar (si no, revierte)
    /// @param calls     rutas a ejecutar: (target, data) codificadas; cada una debe ser un swap
    function run(address token, uint256 amount, uint256 minProfit, bytes calldata calls) external onlyOwner {
        address[] memory tokens = new address[](1); tokens[0] = token;
        uint256[] memory amounts = new uint256[](1); amounts[0] = amount;
        VAULT.flashLoan(address(this), tokens, amounts, abi.encode(token, minProfit, calls));
    }

    /// Callback del vault. Ejecuta la ruta, repaga, exige ganancia, barre a profitSink.
    function receiveFlashLoan(address[] memory tokens, uint256[] memory amounts, uint256[] memory feeAmounts, bytes memory userData) external {
        require(msg.sender == address(VAULT), "only vault");
        (address token, uint256 minProfit, bytes memory calls) = abi.decode(userData, (address, uint256, bytes));
        uint256 owed = amounts[0] + feeAmounts[0];

        // ejecutar la(s) ruta(s) de swap (cada call: 32B len + target(20B) + data)
        (address[] memory targets, bytes[] memory datas) = abi.decode(calls, (address[], bytes[]));
        for (uint256 i = 0; i < targets.length; i++) {
            (bool ok, ) = targets[i].call(datas[i]);
            require(ok, "route call failed");
        }

        uint256 bal = IERC20(token).balanceOf(address(this));
        require(bal >= owed + minProfit, "no profit");     // <-- nunca pierde: revierte si no netea
        IERC20(token).transfer(address(VAULT), owed);      // repagar flash loan

        uint256 profit = IERC20(token).balanceOf(address(this));
        if (profit > 0) { IERC20(token).transfer(profitSink, profit); emit Profit(token, profit); }
    }

    // approvals para que los routers puedan mover los tokens del executor
    function approveRouter(address tokenAddr, address router, uint256 amt) external onlyOwner {
        IERC20(tokenAddr).approve(router, amt);
    }
    // rescate por si queda polvo
    function sweep(address tokenAddr) external onlyOwner {
        IERC20(tokenAddr).transfer(profitSink, IERC20(tokenAddr).balanceOf(address(this)));
    }
}
