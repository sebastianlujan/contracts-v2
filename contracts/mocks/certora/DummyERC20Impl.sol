// SPDX-License-Identifier: agpl-3.0
pragma solidity ^0.7.0;

// with mint
contract DummyERC20Impl { // Underlying token
    uint256 totalSupplys;
    mapping (address => uint256) balances;
    mapping (address => mapping (address => uint256)) allowances;

    string public name;
    string public symbol;
    uint public decimals;

    DummyERC20Impl public erc20A; // underlying token

    function myAddress() public returns (address) {
        return address(this);
    }

    function add(uint a, uint b) internal pure returns (uint256) {
        uint c = a + b;
        require (c >= a);
        return c;
    }
    function sub(uint a, uint balance) internal pure returns (uint256) {
        require (a>=balance);
        return a-balance;
    }

    function totalSupply() external view returns (uint256) {
        return totalSupplys;
    }
    function balanceOf(address account) external view returns (uint256) {
        return balances[account];
    }
    function transfer(address recipient, uint256 amount) external returns (bool) {
        balances[msg.sender] = sub(balances[msg.sender], amount);
        balances[recipient] = add(balances[recipient], amount);
        return true;
    }
    function allowance(address owner, address spender) external view returns (uint256) {
        return allowances[owner][spender];
    }
    function approve(address spender, uint256 amount) external returns (bool) {
        allowances[msg.sender][spender] = amount;
        return true;
    }

    function transferFrom(
        address sender,
        address recipient,
        uint256 amount
    ) external returns (bool) {
        balances[sender] = sub(balances[sender], amount);
        balances[recipient] = add(balances[recipient], amount);
        allowances[sender][msg.sender] = sub(allowances[sender][msg.sender], amount);
        return true;
    }

    // function mint() external payable virtual {
    //     totalSupplys = add(totalSupplys, msg.value);
    //     balances[msg.sender] = add(balances[msg.sender], msg.value);
    // }

    // function mint(uint256 amount) external returns(uint256) {
    //     totalSupplys = add(totalSupplys, amount);
    //     balances[msg.sender] = add(balances[msg.sender], amount);
    //     return 0;
    // }

    // function mint(uint256 mintAmount) external returns (uint256) {
    //     require (address(erc20A) != address(this)); // underlying != cToken by comptroller
    //     erc20A.transferFrom(msg.sender, address(this), mintAmount);
    //     balances[msg.sender] = add(balances[msg.sender], mintAmount);
    //     totalSupplys = add(totalSupplys, mintAmount);
    //     return 0;
    // }
    
    // function mint() external payable returns (uint256) {
    //     uint mintAmount = msg.value;
    //     balances[msg.sender] = add(balances[msg.sender], mintAmount);
    //     totalSupplys = add(totalSupplys, mintAmount);
    //     return 0;
    // }

}