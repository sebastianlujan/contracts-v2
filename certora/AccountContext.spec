/**
 * Ensures that all portfolio assets in the portfolio arrays are tracked properly on the account
 * context object (including on both the bitmap and asset array portfolios)
 */
methods {
    getNextSettleTime(address account) returns (uint40) envfree
    getHasDebt(address account) returns (uint8) envfree
    getAssetArrayLength(address account) returns (uint8) envfree
    getBitmapCurrency(address account) returns (uint16) envfree
    getActiveCurrencies(address account) returns (uint144) envfree
    getAssetsBitmap(address account) returns (bytes32) envfree
    getSettlementDate(uint256 assetType, uint256 maturity) returns (uint256) envfree
    getMaturityAtBitNum(address account, uint256 bitNum) returns (uint256) envfree
}

// Tracks the bytes stored at every asset array index
// (address account, uint256 index)
ghost assetBytesAtIndex(address, uint256) returns bytes32;
// Tracks if a currency is active in the portfolio array
// (address account, uint256 currencyId)
ghost isCurrencyActive(address, uint256) returns bool;
// Tracks the minimum settlement time on an account's arrays
// (address account)
ghost minSettlementTime(address) returns uint256;
// Tracks if an account has a negative balance on any asset
// (address account)
ghost hasPortfolioDebt(address) returns bool;
// Tracks all ifCash assets set on an account
// (address account, uint256 currencyId, uint256 maturity)
ghost ifCashAsset(address, uint256, uint256) returns int256;

// Tracking storage slots for account asset arrays
hook Sstore (slot 1000013)
    [KEY address account]
    [INDEX uint256 index]
    bytes32 v STORAGE {
    // Update the asset bytes at the index
    havoc assetBytesAtIndex assuming assetBytesAtIndex@new(account, index) == v &&
        forall address a.
        forall uint256 i.
        a != account && i != index => assetBytesAtIndex@new(a, i) == assetBytesAtIndex@old(a, i);
    
    uint256 currencyId = unpackAssetCurrencyId(v);
    // Set to true if the asset is set, false otherwise
    havoc isCurrencyActive assuming isCurrencyActive@new(account, currencyId) == isAssetSet(v) &&
        forall address a.
        forall uint256 c.
        a != account && c != currencyId => isCurrencyActive@new(a, c) == isCurrencyActive@old(a, c);

    uint256 assetType = unpackAssetType(v);
    uint256 maturity = unpackAssetMaturity(v);
    uint256 settlementTime = getSettlementDate(assetType, maturity);
    havoc minSettlementTime assuming minSettlementTime@new(account) == min(settlementTime, minSettlementTime@old(account))
        forall address a.
        a != account => minSettlementTime@new(a) == minSettlementTime@old(a);

    int256 assetNotional = unpackAssetNotional(v);
    havoc hasPortfolioDebt assuming hasPortfolioDebt@new(account) == assetNotional < 0
        forall address a.
        a != account => hasPortfolioDebt@new(a) == hasPortfolioDebt@old(a);
}

// ifCash asset storage offset
hook Sstore (slot 1000012)
    [KEY address account]
    [KEY address currencyId]
    [KEY address maturity]
    int256 v STORAGE {

    // Set new ifcash asset ghost
    havoc ifCashAsset assuming ifCashAsset@new(account, currencyId, maturity) ==
        forall address a.
        forall uint256 c.
        forall uint256 m.
        a != account && c != currencyId && m != maturity => ifCashAsset@new(a, c, m) == ifCashAsset@old(a, c, m);

    // Set new portfolio debt ghost
    havoc hasPortfolioDebt assuming hasPortfolioDebt@new(account) == v < 0
        forall address a.
        a != account => hasPortfolioDebt@new(a) == hasPortfolioDebt@old(a);
}

// Unpacking asset array storage
definition unpackAssetCurrencyId(bytes32 b) returns uint256 =
    b & 0x000000000000000000000000000000000000000000000000000000000000ffff;
definition unpackAssetMaturity(bytes32 b) returns uint256 =
    (b & 0x00000000000000000000000000000000000000000000000000ffffffffff0000) >> 16;
definition unpackAssetType(bytes32 b) returns uint256 =
    (b & 0x000000000000000000000000000000000000000000000000ff00000000000000) >> 56;
definition unpackAssetNotional(bytes32 b) returns int256 =
    // TODO: this needs to convert to two's complement...
    (b & 0x00000000000000000000000000ffffffffffffffffffffff0000000000000000) >> 64;

// Helpers for portfolio hooks
definition isAssetSet(bytes32 v) returns bool =
    v != 0x0000000000000000000000000000000000000000000000000000000000000000
definition min(uint256 a, uint256 b) returns uint256 = a < b ? a : b;
definition isAssetBitSet(address account, uint256 bitNum) returns bool =
    (getAssetsBitmap(account) << (bitNum - 1)) & 0x8000000000000000000000000000000000000000000000000000000000000000 ==
        0x8000000000000000000000000000000000000000000000000000000000000000

/* Helper methods for active currencies */
definition getActiveMasked(address account, uint144 index) returns uint144 =
    (getActiveCurrencies(account) >> (128 - index * 16)) & 0x00000000000000000000000000000000ffff;
definition getActiveUnmasked(address account, uint144 index) returns uint144 =
    (getActiveCurrencies(account) >> (128 - index * 16)) & 0x000000000000000000000000000000003fff;
definition hasCurrencyMask(address account, uint144 index) returns bool =
    (getActiveMasked(account, index) & 0x000000000000000000000000000000004000 == 0x000000000000000000000000000000004000);
definition hasPortfolioMask(address account, uint144 index) returns bool =
    (getActiveMasked(account, index) & 0x000000000000000000000000000000008000 == 0x000000000000000000000000000000008000);
definition hasValidMask(address account, uint144 index) returns bool =
    (getActiveMasked(account, index) & 0x000000000000000000000000000000008000 == 0x000000000000000000000000000000008000) ||
    (getActiveMasked(account, index) & 0x000000000000000000000000000000004000 == 0x000000000000000000000000000000004000) ||
    (getActiveMasked(account, index) & 0x00000000000000000000000000000000c000 == 0x00000000000000000000000000000000c000);

definition MAX_CURRENCIES() returns uint256 = 0x3fff;
definition MAX_TIMESTAMP() returns uint256 = 2^32 - 1;
// Cannot have timestamps less than 90 days
definition MIN_TIMESTAMP() returns uint256 = 7776000;

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
    (0 <= i && j == i + 1 && j < 9) =>
        (
            // If the current slot is zero then the next slot must also be zero
            getActiveMasked(account, i) == 0 ? getActiveMasked(account, j) == 0 :
                hasValidMask(account, i) && (
                    // The next slot may terminate
                    getActiveMasked(account, j) == 0 ||
                    // Or it may have a value which must be greater than the current value
                    (hasValidMask(account, j) && getActiveUnmasked(account, i) < getActiveUnmasked(account, j))
                )
        )

/**
 * If a bitmap currency is set then it cannot also be in active currencies or it will be considered a duplicate
 */
invariant bitmapCurrencyIsNotDuplicatedInActiveCurrencies(address account, uint144 i)
    0 <= i && i < 9 && getBitmapCurrency(account) != 0 &&
        (
            // When a bitmap is enable it can only have currency masks in the active currencies bytes
            (hasCurrencyMask(account, i) && getActiveUnmasked(account, i) == 0) || 
                getActiveMasked(account, i) == 0
        ) => getActiveUnmasked(account, i) != getBitmapCurrency(account)

/* Asset array length in the portfolio context must always match how the storage array is set */
invariant assetArrayLengthAlwaysMatchesActual(address account, uint256 index)
    index >= (
        getAssetArrayLength(account) ?
            // If the index is past the end of the asset array length then it must be set to zero
            assetBytesAtIndex(account, index) == 0x0000000000000000000000000000000000000000000000000000000000000000 :
            // Otherwise it must not be set to zero (it must have a value)
            assetBytesAtIndex(account, index) != 0x0000000000000000000000000000000000000000000000000000000000000000
    )

/* Active currencies that are set to active in the portfolio must match */
invariant activeCurrencyAssetFlagsMatchActual(address account, uint256 i)
    (0 <= i && i < 9) => (
        hasPortfolioMask(account, i) ?
            isCurrencyActive(account, getActiveUnmasked(account, i)) == true :
            isCurrencyActive(account, getActiveUnmasked(account, i)) == false
    )

/* Minimum settlement time on the account context must match what is stored on the asset array */
invariant minSettlementTimeMatchesActualForAssetArray(address account)
    getBitmapCurrencyId(account) == 0 => getNextSettleTime(account) == minSettlementTime(account)

/* Portfolio debt set on the account context must be set to true */
invariant hasPortfolioDebtMatchesActual(address account)
    (getHasDebt(account) & 0x01 == 0x01) == hasPortfolioDebt(account)

/* Checks if a bit is set in the bitmap then the fcash asset must match */
invariant allBitmapBitsAreValid(address account, uint256 currencyId, uint256 bitNum)
    (1 <= bitNum && bitNum <= 256) => (
        isAssetBitSet(account, bitNum) ?
            getifCashAsset(account, currencyId, getMaturityAtBitNum(account, bitNum)) ==
                ifCashAsset(account, currencyId, getMaturityAtBitNum(account, bitNum)) :
            getifCashAsset(account, currencyId, getMaturityAtBitNum(account, bitNum)) == 0
    )