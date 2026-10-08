# -*- coding: utf-8 -*-
"""
apex/pago.py - verificacion REAL de pagos x402 con la libreria oficial.
Ya no es stub: decodifica la cabecera X-PAYMENT, verifica contra el facilitator
on-chain y liquida (settle) antes de que la puerta entregue el dato.
  base-sepolia (testnet, facilitator GRATIS) por defecto; base (mainnet) con CDP key.
"""
import os, json, base64
from x402.http import HTTPFacilitatorClientSync, FacilitatorConfig, DEFAULT_FACILITATOR_URL
from x402.server import PaymentPayload, PaymentRequirements

NET = os.environ.get("APEX_NET", "base-sepolia")
USDC = {
    "base-sepolia": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
    "base":         "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
}
def usdc_asset(): return USDC.get(NET, USDC["base-sepolia"])

def _facilitator():
    url = os.environ.get("APEX_FACILITATOR", DEFAULT_FACILITATOR_URL)
    # mainnet (base) exige auth CDP; testnet es gratis
    return HTTPFacilitatorClientSync(FacilitatorConfig(url=url))

def requisitos(resource, price_usdc, pay_to):
    atomic = str(int(round(float(price_usdc) * 1_000_000)))   # USDC 6 decimales
    return PaymentRequirements(scheme="exact", network=NET, asset=usdc_asset(),
                               amount=atomic, pay_to=pay_to, max_timeout_seconds=120, extra=None)

def verificar(header_xpayment, resource, price_usdc, pay_to):
    """Devuelve (ok:bool, info:dict). ok=True solo si el facilitator valida Y liquida."""
    try:
        raw = base64.b64decode(header_xpayment)
        payload = PaymentPayload.model_validate_json(raw)
    except Exception as e:
        return False, {"motivo": "cabecera X-PAYMENT ilegible", "detalle": str(e)[:120]}
    reqs = requisitos(resource, price_usdc, pay_to)
    fac = _facilitator()
    try:
        vr = fac.verify(payload, reqs)
    except Exception as e:
        return False, {"motivo": "facilitator no respondio", "detalle": str(e)[:160]}
    if not getattr(vr, "is_valid", False):
        return False, {"motivo": "pago invalido", "razon": getattr(vr,"invalid_reason",None),
                        "mensaje": getattr(vr,"invalid_message",None)}
    # pago valido -> liquidar on-chain (mueve el USDC a tu wallet)
    try:
        sr = fac.settle(payload, reqs)
    except Exception as e:
        return False, {"motivo": "settle fallo", "detalle": str(e)[:160]}
    if not getattr(sr, "success", False):
        return False, {"motivo": "settle rechazado", "razon": getattr(sr,"error_reason",None)}
    return True, {"tx": getattr(sr,"transaction",None), "payer": getattr(sr,"payer",None),
                  "amount": getattr(sr,"amount",None), "network": getattr(sr,"network",None)}
