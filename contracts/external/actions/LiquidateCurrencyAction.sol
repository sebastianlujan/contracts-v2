// SPDX-License-Identifier: GPL-3.0-only
pragma solidity ^0.8.9;
pragma abicoder v2;

import "./ActionGuards.sol";
import "../../internal/AccountContextHandler.sol";
import "../../internal/liquidation/LiquidateCurrency.sol";
import "../../internal/liquidation/LiquidationHelpers.sol";
import "../../math/SafeInt256.sol";
import "../../math/UserDefinedType.sol";

contract LiquidateCurrencyAction is ActionGuards {
    using UserDefinedType for IA;
    using UserDefinedType for NT;
    using AccountContextHandler for AccountContext;
    using BalanceHandler for BalanceState;
    using SafeInt256 for int256;

    event LiquidateLocalCurrency(
        address indexed liquidated,
        address indexed liquidator,
        uint16 localCurrencyId,
        IA localAssetCashFromLiquidator
    );

    event LiquidateCollateralCurrency(
        address indexed liquidated,
        address indexed liquidator,
        uint16 localCurrencyId,
        uint16 collateralCurrencyId,
        IA localAssetCashFromLiquidator,
        IA netCollateralTransfer,
        NT netNTokenTransfer
    );

    /// @notice Calculates the net local currency required by the liquidator. This is a stateful method
    /// because it may settle the liquidated account if required. However, it can be called using staticcall
    /// off chain to determine the net local currency required before liquidating.
    /// @param liquidateAccount account to liquidate
    /// @param localCurrency id of the local currency
    /// @param maxNTokenLiquidation maximum amount of nTokens to purchase (if any)
    /// @return currency transfer amounts:
    ///   - local currency required from liquidator (positive or negative)
    ///   - local nTokens paid to liquidator (positive)
    function calculateLocalCurrencyLiquidation(
        address liquidateAccount,
        uint16 localCurrency,
        uint96 maxNTokenLiquidation
    ) external returns (IA, NT) {
        // prettier-ignore
        (
            IA localAssetCashFromLiquidator,
            BalanceState memory localBalanceState,
            /* PortfolioState memory portfolio */,
            /* AccountContext memory accountContext */
        ) = _localCurrencyLiquidation(
            liquidateAccount,
            localCurrency,
            maxNTokenLiquidation,
            true // Is Calculation
        );

        return (
            localAssetCashFromLiquidator,
            localBalanceState.netNTokenTransfer.neg()
        );
    }

    /// @notice Liquidates an account using local currency only
    /// @param liquidateAccount account to liquidate
    /// @param localCurrency id of the local currency
    /// @param maxNTokenLiquidation maximum amount of nTokens to purchase (if any)
    /// @return currency transfer amounts:
    ///   - local currency required from liquidator (positive or negative)
    ///   - local nTokens paid to liquidator (positive)
    function liquidateLocalCurrency(
        address liquidateAccount,
        uint16 localCurrency,
        uint96 maxNTokenLiquidation
    ) external nonReentrant returns (IA, NT) {
        (
            IA localAssetCashFromLiquidator,
            BalanceState memory localBalanceState,
            PortfolioState memory portfolio,
            AccountContext memory accountContext
        ) = _localCurrencyLiquidation(
            liquidateAccount,
            localCurrency,
            maxNTokenLiquidation,
            false // is not calculation
        );

        // Transfers a positive or negative amount of local currency as well as the net nToken
        // amounts to the liquidator
        AccountContext memory liquidatorContext =
            LiquidationHelpers.finalizeLiquidatorLocal(
                msg.sender,
                localCurrency,
                localAssetCashFromLiquidator,
                localBalanceState.netNTokenTransfer.neg()
            );
        liquidatorContext.setAccountContext(msg.sender);

        LiquidateCurrency.finalizeLiquidatedCollateralAndPortfolio(
            liquidateAccount,
            localBalanceState, // In this case, local currency is the collateral
            accountContext,
            portfolio
        );

        emit LiquidateLocalCurrency(
            liquidateAccount,
            msg.sender,
            localCurrency,
            localAssetCashFromLiquidator
        );

        return (
            localAssetCashFromLiquidator,
            localBalanceState.netNTokenTransfer.neg()
        );
    }

    /// @notice Calculates local and collateral currency transfers for a liquidation. This is a stateful method
    /// because it may settle the liquidated account if required. However, it can be called using staticcall
    /// off chain to determine the net currency amounts required before liquidating.
    /// @param liquidateAccount account to liquidate
    /// @param localCurrency id of the local currency
    /// @param collateralCurrency id of the collateral currency
    /// @param maxCollateralLiquidation maximum amount of collateral (inclusive of cash and nTokens) to liquidate
    /// @param maxNTokenLiquidation maximum amount of nTokens to purchase (if any)
    /// @return currency transfer amounts:
    ///   - local currency required from liquidator (negative)
    ///   - collateral asset cash paid to liquidator (positive)
    ///   - collateral nTokens paid to liquidator (positive)
    function calculateCollateralCurrencyLiquidation(
        address liquidateAccount,
        uint16 localCurrency,
        uint16 collateralCurrency,
        uint128 maxCollateralLiquidation,
        uint96 maxNTokenLiquidation
    )
        external
        returns (
            IA,
            IA,
            NT
        )
    {
        // prettier-ignore
        (
            IA localAssetCashFromLiquidator,
            BalanceState memory collateralBalanceState,
            /* PortfolioState memory portfolio */,
            /* AccountContext memory accountContext */
        ) = _collateralCurrencyLiquidation(
                liquidateAccount,
                localCurrency,
                collateralCurrency,
                maxCollateralLiquidation,
                maxNTokenLiquidation,
                true // is calculation
            );

        return (
            localAssetCashFromLiquidator,
            _collateralAssetCashToLiquidator(collateralBalanceState),
            collateralBalanceState.netNTokenTransfer.neg()
        );
    }

    /// @notice Liquidates an account between local and collateral currency
    /// @param liquidateAccount account to liquidate
    /// @param localCurrency id of the local currency
    /// @param collateralCurrency id of the collateral currency
    /// @param maxCollateralLiquidation maximum amount of collateral (inclusive of cash and nTokens) to liquidate
    /// @param maxNTokenLiquidation maximum amount of nTokens to purchase (if any)
    /// @param withdrawCollateral if true, withdraws collateral back to msg.sender
    /// @param redeemToUnderlying if true, converts collateral from asset cash to underlying
    /// @return currency transfer amounts:
    ///   - local currency required from liquidator (negative)
    ///   - collateral asset cash paid to liquidator (positive)
    ///   - collateral nTokens paid to liquidator (positive)
    function liquidateCollateralCurrency(
        address liquidateAccount,
        uint16 localCurrency,
        uint16 collateralCurrency,
        uint128 maxCollateralLiquidation,
        uint96 maxNTokenLiquidation,
        bool withdrawCollateral,
        bool redeemToUnderlying
    )
        external
        nonReentrant
        returns (
            IA,
            IA,
            NT
        )
    {
        (
            IA localAssetCashFromLiquidator,
            BalanceState memory collateralBalanceState,
            PortfolioState memory portfolio,
            AccountContext memory accountContext
        ) =
            _collateralCurrencyLiquidation(
                liquidateAccount,
                localCurrency,
                collateralCurrency,
                maxCollateralLiquidation,
                maxNTokenLiquidation,
                false // is not calculation
            );

        _finalizeLiquidatorBalances(
            localCurrency,
            collateralCurrency,
            localAssetCashFromLiquidator,
            collateralBalanceState,
            withdrawCollateral,
            redeemToUnderlying
        );

        _emitCollateralEvent(
            liquidateAccount,
            localCurrency,
            localAssetCashFromLiquidator,
            collateralBalanceState
        );

        // Liquidated local currency balance will increase by the net paid from the liquidator
        LiquidationHelpers.finalizeLiquidatedLocalBalance(
            liquidateAccount,
            localCurrency,
            accountContext,
            localAssetCashFromLiquidator
        );

        // netAssetTransfer is cleared and set back when finalizing inside this function
        LiquidateCurrency.finalizeLiquidatedCollateralAndPortfolio(
            liquidateAccount,
            collateralBalanceState,
            accountContext,
            portfolio
        );

        return (
            localAssetCashFromLiquidator,
            _collateralAssetCashToLiquidator(collateralBalanceState),
            collateralBalanceState.netNTokenTransfer.neg()
        );
    }

    function _emitCollateralEvent(
        address liquidateAccount,
        uint16 localCurrency,
        IA localAssetCashFromLiquidator,
        BalanceState memory collateralBalanceState
    ) private {
        emit LiquidateCollateralCurrency(
            liquidateAccount,
            msg.sender,
            localCurrency,
            uint16(collateralBalanceState.currencyId),
            localAssetCashFromLiquidator,
            _collateralAssetCashToLiquidator(collateralBalanceState),
            collateralBalanceState.netNTokenTransfer.neg()
        );
    }

    function _localCurrencyLiquidation(
        address liquidateAccount,
        uint16 localCurrency,
        uint96 maxNTokenLiquidation,
        bool isCalculation
    )
        internal
        returns (
            IA,
            BalanceState memory,
            PortfolioState memory,
            AccountContext memory
        )
    {
        (
            AccountContext memory accountContext,
            LiquidationFactors memory factors,
            PortfolioState memory portfolio
        ) = LiquidationHelpers.preLiquidationActions(liquidateAccount, localCurrency, 0);
        BalanceState memory localBalanceState;
        localBalanceState.loadBalanceState(liquidateAccount, localCurrency, accountContext);
        factors.isCalculation = isCalculation;

        IA localAssetCashFromLiquidator =
            LiquidateCurrency.liquidateLocalCurrency(
                localCurrency,
                maxNTokenLiquidation,
                block.timestamp,
                localBalanceState,
                factors,
                portfolio
            );

        return (
            localAssetCashFromLiquidator,
            localBalanceState,
            portfolio,
            accountContext
        );
    }

    function _collateralCurrencyLiquidation(
        address liquidateAccount,
        uint16 localCurrency,
        uint16 collateralCurrency,
        uint128 maxCollateralLiquidation,
        uint96 maxNTokenLiquidation,
        bool isCalculation
    )
        private
        returns (
            IA,
            BalanceState memory,
            PortfolioState memory,
            AccountContext memory
        )
    {
        uint256 blockTime = block.timestamp;
        (
            AccountContext memory accountContext,
            LiquidationFactors memory factors,
            PortfolioState memory portfolio
        ) =
            LiquidationHelpers.preLiquidationActions(
                liquidateAccount,
                localCurrency,
                collateralCurrency
            );

        BalanceState memory collateralBalanceState;
        collateralBalanceState.loadBalanceState(
            liquidateAccount,
            collateralCurrency,
            accountContext
        );
        factors.isCalculation = isCalculation;

        IA localAssetCashFromLiquidator =
            LiquidateCurrency.liquidateCollateralCurrency(
                maxCollateralLiquidation,
                maxNTokenLiquidation,
                blockTime,
                collateralBalanceState,
                factors,
                portfolio
            );

        return (
            localAssetCashFromLiquidator,
            collateralBalanceState,
            portfolio,
            accountContext
        );
    }

    /// @dev Only used for collateral currency liquidation
    function _finalizeLiquidatorBalances(
        uint16 localCurrency,
        uint16 collateralCurrency,
        IA localAssetCashFromLiquidator,
        BalanceState memory collateralBalanceState,
        bool withdrawCollateral,
        bool redeemToUnderlying
    ) private {
        // Will transfer local currency from the liquidator
        AccountContext memory liquidatorContext =
            LiquidationHelpers.finalizeLiquidatorLocal(
                msg.sender,
                localCurrency,
                localAssetCashFromLiquidator,
                NT.wrap(0) // No nToken transfers
            );

        // Will transfer collateral to the liquidator
        LiquidationHelpers.finalizeLiquidatorCollateral(
            msg.sender,
            liquidatorContext,
            collateralCurrency,
            _collateralAssetCashToLiquidator(collateralBalanceState),
            collateralBalanceState.netNTokenTransfer.neg(),
            withdrawCollateral,
            redeemToUnderlying
        );

        liquidatorContext.setAccountContext(msg.sender);
    }

    function _collateralAssetCashToLiquidator(BalanceState memory collateralBalanceState)
        private
        pure
        returns (IA)
    {
        // netAssetTransferInternalPrecision is the cash claim withdrawn from collateral
        // liquidity tokens.
        return
            collateralBalanceState.netCashChange.neg().add(
                collateralBalanceState.netAssetTransferInternalPrecision
            );
    }
}
