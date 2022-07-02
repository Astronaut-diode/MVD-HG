pragma solidity ^0.4.18;

contract test {
    string d = "asd";
    function go() public returns(uint){
        uint a = 10;
        b();
        return a;
    }

    function b() public {
        d = "bsd";
    }
}