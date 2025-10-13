from flask import Blueprint, jsonify, request

from ..db import db
from ..models.payment import Payment, PaymentApplication
from ..models.charge import Charge
from .auth import require_token


payments_bp = Blueprint("payments", __name__)


@payments_bp.get("/payments")
def list_payments():
    customer_id = request.args.get("customer_id", type=int)
    q = Payment.query
    if customer_id:
        q = q.filter(Payment.customer_id == customer_id)
    rows = q.order_by(Payment.date.desc()).limit(500).all()
    return jsonify([p.to_dict() for p in rows])


@payments_bp.post("/payments")
@require_token
def create_payment():
    data = request.get_json(silent=True) or {}
    # order_id obligatorio para asociar el pago a un pedido específico
    try:
        order_id = int(data.get("order_id"))
    except Exception:
        order_id = None
    if not order_id:
        return jsonify({"error": "order_id es obligatorio"}), 400
    p = Payment(
        customer_id=int(data.get("customer_id")),
        amount=float(data.get("amount") or 0),
        method=(data.get("method") or None),
        reference=(data.get("reference") or None),
    )
    db.session.add(p)
    db.session.flush()
    # Aplicar a charges: si vienen apps explícitas, usarlas; si no, distribuir proporcional
    apps = data.get("applications") or []
    if apps:
        for app in apps:
            ch = Charge.query.get(int(app.get("charge_id")))
            if not ch:
                continue
            amt = float(app.get("amount") or 0)
            if amt <= 0:
                continue
            db.session.add(PaymentApplication(payment_id=p.id, charge_id=ch.id, amount=amt))
            if amt >= max(0.0, (ch.total or 0.0) - (ch.discount_amount or 0.0)):
                ch.status = "paid"
    else:
        # Distribución automática: por cliente y, si se especifica, por pedido
        q = Charge.query.filter(Charge.customer_id == p.customer_id, Charge.status == "pending", Charge.order_id == order_id)
        charges = q.all()
        # calcular deuda de cada charge
        due_by_charge = {}
        total_due = 0.0
        for ch in charges:
            due = max(0.0, (ch.total or 0.0) - (ch.discount_amount or 0.0))
            # restar pagos previos
            prev_apps = PaymentApplication.query.filter(PaymentApplication.charge_id == ch.id).all()
            paid_prev = sum(a.amount or 0.0 for a in prev_apps)
            due = max(0.0, due - paid_prev)
            if due > 0:
                due_by_charge[ch.id] = due
                total_due += due
        remaining = int(round(float(p.amount or 0.0)))
        if total_due > 0 and remaining > 0:
            # proporcional entero: primero parte entera por piso, luego repartir remanente por mayor residuo
            shares = []  # (charge_id, share_int, remainder)
            distributed = 0
            for ch in charges:
                due = due_by_charge.get(ch.id, 0.0)
                if due <= 0:
                    continue
                raw = (remaining * (due / total_due))
                share_int = int(raw // 1)
                remainder = float(raw - share_int)
                shares.append((ch.id, share_int, remainder))
                distributed += share_int
            leftover = max(0, remaining - distributed)
            shares.sort(key=lambda t: t[2], reverse=True)
            idx = 0
            while leftover > 0 and idx < len(shares):
                cid, s_int, rem = shares[idx]
                # no exceder la deuda
                max_add = int(max(0.0, due_by_charge.get(cid, 0.0) - s_int))
                if max_add > 0:
                    add = 1
                    shares[idx] = (cid, s_int + add, rem)
                    leftover -= add
                idx = (idx + 1) if idx + 1 < len(shares) else 0
                # evitar bucles infinitos si no hay espacio
                if all(due_by_charge.get(cid,0.0) <= s for cid, s, _ in shares):
                    break
            # persistir aplicaciones
            for cid, s_int, _ in shares:
                if s_int <= 0:
                    continue
                amt = min(float(due_by_charge.get(cid, 0.0)), float(s_int))
                if amt <= 0:
                    continue
                db.session.add(PaymentApplication(payment_id=p.id, charge_id=cid, amount=amt))
        # actualizar estados pagados
        for ch in charges:
            # recomputar saldo
            due = max(0.0, (ch.total or 0.0) - (ch.discount_amount or 0.0))
            apps_now = PaymentApplication.query.filter(PaymentApplication.charge_id == ch.id).all()
            paid = sum(a.amount or 0.0 for a in apps_now)
            if paid >= due and due > 0:
                ch.status = "paid"
    db.session.commit()
    return jsonify(p.to_dict()), 201


