# -*- coding: utf-8 -*-
"""Despliega ApexAttestations en Base. Necesita APEX_PRIVATE_KEY (clave de la wallet operadora).
APEX_NET=base-sepolia (testnet, gas gratis por faucet) | base (mainnet, ~$0.3 de gas)."""
import os, json
from web3 import Web3

NETS={"base-sepolia":"https://sepolia.base.org","base":"https://mainnet.base.org"}
net=os.environ.get("APEX_NET","base-sepolia"); rpc=NETS[net]
pk=os.environ.get("APEX_PRIVATE_KEY")
assert pk, "exporta APEX_PRIVATE_KEY (clave privada de la wallet operadora)"
art=json.load(open(os.path.join(os.path.dirname(__file__),"..","contracts","ApexAttestations.json")))
w3=Web3(Web3.HTTPProvider(rpc)); acct=w3.eth.account.from_key(pk)
print(f"red {net} | operador {acct.address} | balance {w3.from_wei(w3.eth.get_balance(acct.address),'ether')} ETH")
C=w3.eth.contract(abi=art["abi"], bytecode=art["bytecode"])
tx=C.constructor().build_transaction({"from":acct.address,"nonce":w3.eth.get_transaction_count(acct.address),
    "gas":600000,"maxFeePerGas":w3.to_wei(0.05,"gwei"),"maxPriorityFeePerGas":w3.to_wei(0.01,"gwei"),"chainId":w3.eth.chain_id})
signed=acct.sign_transaction(tx); h=w3.eth.send_raw_transaction(signed.raw_transaction)
print("tx enviada:", h.hex(), "- esperando recibo...")
r=w3.eth.wait_for_transaction_receipt(h, timeout=180)
print("DESPLEGADO en:", r.contractAddress, "| bloque", r.blockNumber)
print(f"verlo: https://{'sepolia.' if net=='base-sepolia' else ''}basescan.org/address/{r.contractAddress}")
