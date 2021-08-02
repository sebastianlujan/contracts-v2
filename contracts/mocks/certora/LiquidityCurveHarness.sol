// SPDX-License-Identifier: GPL-3.0-only
pragma solidity >0.7.0;
pragma experimental ABIEncoderV2;

import "../../internal/markets/CashGroup.sol";
import "../../internal/markets/Market.sol";
// import "../../math/ABDKMath64x64.sol";

contract LiquidityCurveHarness {
    using CashGroup for CashGroupParameters;
    using Market for MarketParameters;

    CashGroupParameters symbolicCashGroup;
    MarketParameters symbolicMarket;

    uint256 private constant MARKET_INDEX = 1;
    uint256 private constant CURRENCY_ID = 1;
    uint256 public constant MATURITY = 86400 * 360 * 30;

    function getRateScalar(uint256 timeToMaturity) external view returns (int256) {
        // CashGroupParameters memory cashGroup = CashGroup.buildCashGroupView(CURRENCY_ID);
        // CashGroupParameters memory cashGroup = symbolicCashGroup; //CashGroup.buildCashGroupView(CURRENCY_ID);
        return symbolicCashGroup.getRateScalar(MARKET_INDEX, timeToMaturity);
        // return cashGroup.getRateScalar(MARKET_INDEX, timeToMaturity);
    }

    // function _loadMarket() internal view returns (MarketParameters memory) {
    //     //CashGroupParameters memory cashGroup = CashGroup.buildCashGroupView(CURRENCY_ID);
    //     MarketParameters memory market;
    //     market.loadMarket(
    //         CURRENCY_ID,
    //         MATURITY,
    //         block.timestamp,
    //         true,
    //         symbolicCashGroup.getRateOracleTimeWindow()
    //     );

    //     return market;
    // }

    function _loadMarket() internal {
        symbolicMarket.loadMarket(
            CURRENCY_ID,
            MATURITY,
            block.timestamp,
            true,
            symbolicCashGroup.getRateOracleTimeWindow()
        );
    }

    function getRateOracleTimeWindow() external view returns (uint256) {
        // CashGroupParameters memory cashGroup = CashGroup.buildCashGroupView(CURRENCY_ID);
        //CashGroupParameters memory cashGroup = symbolicCashGroup;
        // return cashGroup.getRateOracleTimeWindow();
        return symbolicCashGroup.getRateOracleTimeWindow();
    }

    function getStoredOracleRate() external view returns (uint256) {
        uint256 settlementDate = DateTime.getReferenceTime(block.timestamp) + Constants.QUARTER;
        bytes32 slot = Market.getSlot(CURRENCY_ID, settlementDate, MATURITY);
        bytes32 data;

        assembly {
            data := sload(slot)
        }

        uint256 oracleRate = uint256(uint32(uint256(data >> 192)));

        return oracleRate;
    }

    function getLastImpliedRate() external returns (uint256) {
        _loadMarket();
        // return _loadMarket().lastImpliedRate;
        return symbolicMarket.lastImpliedRate;
    }

    function getPreviousTradeTime() external returns (uint256) {
        _loadMarket();
        // return _loadMarket().previousTradeTime;
        return symbolicMarket.previousTradeTime;
    }

    function getMarketOracleRate() external returns (uint256) {
        _loadMarket();
        // return _loadMarket().oracleRate;
        return symbolicMarket.oracleRate;
    }

    function getMarketfCash() external returns (int256) {
        _loadMarket();
        // return _loadMarket().totalfCash;
        return symbolicMarket.totalfCash;
    }

    function getMarketAssetCash() external returns (int256) {
        _loadMarket();
        // return _loadMarket().totalAssetCash;
        return symbolicMarket.totalAssetCash;
    }

    function getMarketLiquidity() external returns (int256) {
        _loadMarket();
        // return _loadMarket().totalLiquidity;
        return symbolicMarket.totalLiquidity;
    }

    function executeTrade(uint256 timeToMaturity, int256 fCashToAccount)
        external
        returns (int256, int256)
    {
        //CashGroupParameters memory cashGroup = symbolicCashGroup; //CashGroup.buildCashGroupStateful(CURRENCY_ID);
        // CashGroupParameters memory cashGroup = CashGroup.buildCashGroupStateful(CURRENCY_ID);
        //MarketParameters memory market = symbolicMarket; //_loadMarket();
        // MarketParameters memory market = _loadMarket();
         _loadMarket();
        (int256 netAssetCash, int256 netAssetCashToReserve) =
            symbolicMarket.calculateTrade(symbolicCashGroup, fCashToAccount, timeToMaturity, MARKET_INDEX);
        // market.setMarketStorage();
        //symbolicMarket = market;
        //symbolicCashGroup = cashGroup;
        return (netAssetCash, netAssetCashToReserve);
    }

    function addLiquidity(int256 assetCash) external returns (int256, int256) {
        //MarketParameters memory market = symbolicMarket; //_loadMarket();
        // MarketParameters memory market = _loadMarket();
         _loadMarket();
        int256 marketfCashBefore = symbolicMarket.totalfCash;
        (int256 liquidityTokens, int256 fCashToAccount) = symbolicMarket.addLiquidity(assetCash);
        // market.setMarketStorage();
        // symbolicMarket = market;

        // Check the assertion in here because the prover does not handle negative integers
        // assert((market.totalfCash + fCashToAccount) == marketfCashBefore);

        return (liquidityTokens, fCashToAccount);
    }

    function removeLiquidity(int256 tokensToRemove) external returns (int256, int256) {
        // MarketParameters memory market = symbolicMarket; //_loadMarket();
        // MarketParameters memory market = _loadMarket();
         _loadMarket();
        (int256 assetCash, int256 fCash) = symbolicMarket.removeLiquidity(tokensToRemove);
        // market.setMarketStorage();
        // symbolicMarket = market;
        return (assetCash, fCash);
    }

    ///////////////////////////////
    //  general purpose functions 
    ///////////////////////////////

    function a_minus_b(int256 a, int256 b) public returns (int256) {
        return a - b;
    }
    function a_plus_b(int256 a, int256 b) public returns (int256) {
        return a + b;
    }
    function isEqual(int256 a, int256 b) public returns (bool) {
        return a == b;
    }
}
