using DummyERC20A as token

methods {
    // harnessed
    depositAssetToken(address account, int256 assetAmountExternal, bool forceTransfer) returns (int256, int256) envfree
    depositUnderlyingToken(
        address account,
        int256 underlyingAmountExternal
    ) returns (int256) envfree

    // getters
    token.balanceOf(address) returns (uint) envfree

    getCurrencyId() returns (uint256) envfree
    getStoredCashBalance() returns (int256) envfree
    getStoredNTokenBalance() returns (int256) envfree
    getNetCashChange() returns (int256) envfree
    getNetAssetTransferInternalPrecision() returns (int256) envfree
    getNetNTokenTransfer() returns (int256) envfree
    getNetNTokenSupplyChange() returns (int256) envfree
    getLastClaimTime() returns (uint256) envfree
    getLastClaimSupply() returns (uint256) envfree

    // dispatchers
    transfer(address,uint) => DISPATCHER(true)
    balanceOf(address) => DISPATCHER(true)
    transferFrom(address,address,uint) => DISPATCHER(true)
}

rule integrity_depositAssetToken(address account, int256 assetAmountExternal, bool forceTransfer) {
    require account != currentContract;
    uint _balance = token.balanceOf(account);

    depositAssetToken(account, assetAmountExternal, forceTransfer);

    uint balance_ = token.balanceOf(account);

    assert balance_ == _balance + to_mathint(assetAmountExternal);
}

// exploratory
function invokeArbitrary(method f) {
    env e;
    calldataarg arg;
    f(e, arg);
}

rule checkCurrencyIdChange(method f) {
    uint pre = getCurrencyId();
    invokeArbitrary(f);
    uint post = getCurrencyId();
    assert pre == post;
}

rule checkStoredCashBalance(method f) {
    int pre = getStoredCashBalance();
    invokeArbitrary(f);
    int post = getStoredCashBalance();
    assert pre == post;
}

rule checkStoredNTokenBalance(method f) {
    int pre = getStoredNTokenBalance();
    invokeArbitrary(f);
    int post = getStoredNTokenBalance();
    assert pre == post;
}

rule checkNetCashChange(method f) {
    int pre = getNetCashChange();
    invokeArbitrary(f);
    int post = getNetCashChange();
    assert pre == post;
}

rule checkNetAssetTransferInternalPrecision(method f) {
    int pre = getNetAssetTransferInternalPrecision();
    invokeArbitrary(f);
    int post = getNetAssetTransferInternalPrecision();
    assert pre == post;
}

rule checkNetNTokenTransfer(method f) {
    int pre = getNetNTokenTransfer();
    invokeArbitrary(f);
    int post = getNetNTokenTransfer();
    assert pre == post;
}

rule checkNetNTokenSupplyChange(method f) {
    int pre = getNetNTokenSupplyChange();
    invokeArbitrary(f);
    int post = getNetNTokenSupplyChange();
    assert pre == post;
}

rule checkLastClaimTime(method f) {
    uint pre = getLastClaimTime();
    invokeArbitrary(f);
    uint post = getLastClaimTime();
    assert pre == post;
}

rule checkLastClaimSupply(method f) {
    uint pre = getLastClaimSupply();
    invokeArbitrary(f);
    uint post = getLastClaimSupply();
    assert pre == post;
}

// sanity
rule sanity(method f) {
    invokeArbitrary(f);
    assert false;
}