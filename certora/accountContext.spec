methods {
    getAccountContextSlot(address account) returns (uint256) envfree
    getNextSettleTime(address account) returns (uint40) envfree
    getHasDebt(address account) returns (uint8) envfree
    getAssetArrayLength(address account) returns (uint8) envfree
    getBitmapCurrency(address account) returns (uint16) envfree
    getActiveCurrencies(address account) returns (uint144) envfree
    getAssetsBitmap(address account) returns (bytes32) envfree
}

/* Unpack account context */
// definition unpackAccountNextSettleTime(bytes32 b) returns uint40 = 
//     b & 0x00000000000000000000000000000000000000000000ffffffffffffffffffff;
// definition unpackAccountHasDebt(bytes32 b) returns bytes1 =
//     (b & 0x000000000000000000000000000000000000000000ff00000000000000000000) << 208;
// definition unpackAccountArrayLength(bytes32 b) returns uint8 = 
//     (b & 0x0000000000000000000000000000000000000000ff0000000000000000000000) >> 48;
// definition unpackAccountBitmapId(bytes32 b) returns uint16 =
//     (b & 0x000000000000000000000000000000000000ffff000000000000000000000000) >> 56;
// definition unpackActiveCurrencies(bytes32 b) returns bytes18 = 
//     (b & 0xffffffffffffffffffffffffffffffffffff0000000000000000000000000000) << 40;

// definition currencyActiveInPortfolio(uint16 c) returns bool = (c & 0x8000) == 0x8000;
// definition currencyActiveInBalances(uint16 c) returns bool = (c & 0x4000) == 0x4000;

/* Helper methods for active currencies */
definition unmaskCurrency(uint16 c) returns uint16 = (c & 0x3FFF);
definition getActive(address account, uint144 index) returns uint144 =
    (getActiveCurrencies(account) >> (128 - index * 16)) & 0x00000000000000000000000000000000ffff;

definition MAX_CURRENCIES() returns uint256 = 0x3fff;
definition MAX_TIMESTAMP() returns uint256 = 2^32 - 1;
// Cannot have timestamps less than 90 days
definition MIN_TIMESTAMP() returns uint256 = 7776000;

rule getAndSetAccountContext(
    address account,
    uint40 nextSettleTime,
    uint8 hasDebt,
    uint8 assetArrayLength,
    uint16 bitmapCurrencyId,
    uint144 activeCurrencies
) {
    env e;
    setAccountContext(e, account, nextSettleTime, hasDebt, assetArrayLength, bitmapCurrencyId, activeCurrencies);
    assert getNextSettleTime(account) == nextSettleTime;
    assert getHasDebt(account) == hasDebt;
    assert getAssetArrayLength(account) == assetArrayLength;
    assert getBitmapCurrency(account) == bitmapCurrencyId;
    assert getActiveCurrencies(account) == activeCurrencies;
}

/**
 * If an account enables a bitmap portfolio it cannot strand assets behind such that the system
 * becomes blind to them.
 */
rule enablingBitmapCannotLeaveBehindAssets(address account, uint256 currencyId) {
    env e;
    require currencyId <= MAX_CURRENCIES();
    require e.block.timestamp >= MIN_TIMESTAMP();
    require e.block.timestamp <= MAX_TIMESTAMP();
    uint16 bitmapCurrencyId = getBitmapCurrency(account);
    uint8 assetArrayLength = getAssetArrayLength(account);
    bytes32 assetsBitmap = getAssetsBitmap(account);
    require bitmapCurrencyId != 0 => assetArrayLength == 0;
    // Cannot set bitmap currency to 0 if it is already 0, will revert
    require bitmapCurrencyId == 0 => currencyId > 0;
    // Prevents invalid starting state
    require bitmapCurrencyId == 0 => assetsBitmap == 0x0000000000000000000000000000000000000000000000000000000000000000;

    enableBitmapForAccount@withrevert(e, account, currencyId, e.block.timestamp);
    // In these cases the account has active assets or cash debts
    assert (
        assetArrayLength != 0 ||
        assetsBitmap != 0x0000000000000000000000000000000000000000000000000000000000000000
    ) => lastReverted;
}

/**
 * When a bitmap portfolio is active, it cannot ever have any assets in its array. If this occurs then
 * there will be assets that are not accounted for during the free collateral check.
 */
invariant bitmapPortfoliosCannotHaveAssetArray(address account)
    getBitmapCurrency(account) != 0 => getAssetArrayLength(account) == 0

/**
 * Active currency flags are always sorted and cannot be double counted, if this occurs then there
 * will be currencies that are double counted during the free collateral check.
 *
 * This check ensures that any two indexes of the active currencies byte vector are not duplicated
 * and sorted properly.
 */
invariant activeCurrenciesAreNotDuplicatedAndSorted(address account, uint144 i, uint144 j)
    0 <= i && i < j && j < 9 =>
        getActive(account, i) == 0 ? getActive(account, j) == 0 : getActive(account, i) < getActive(account, j)

/**
 * If a bitmap currency is set then it cannot also be in active currencies or it will be considered a duplicate
 */
invariant bitmapCurrencyIsNotDuplicatedInActiveCurrencies(address account, uint144 i)
    0 <= i && i < 9 && getBitmapCurrency(account) != 0 =>
        getActive(account, i) != getBitmapCurrency(account)

// Requires portfolio integration....
// rule activeCurrencyAssetFlagsMatchesActual { }
// rule activeCurrencyBalanceFlagsMatchesActual { }
// rule assetArrayLengthAlwaysMatchesActual { }
// rule nextSettleTimeAlwaysReferencesMinMaturity { }
// rule hasAssetDebtFlagsAreAlwaysCorrect { }