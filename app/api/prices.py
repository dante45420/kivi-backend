from datetime import date, datetime, timedelta
from typing import Optional
from flask import Blueprint, jsonify, request

from ..db import db
from ..models.price_history import PriceHistory
from ..models.catalog_price import CatalogPrice
from ..models.competitor_price import CompetitorPrice
from .auth import require_token

prices_bp = Blueprint("prices", __name__)


def _period_cutoff(period: str) -> Optional[date]:
    today = date.today()
    if period == "7d":
        return today - timedelta(days=7)
    if period == "1m" or period == "1mes" or period == "1month":
        return today - timedelta(days=30)
    if period == "1y" or period == "1anio" or period == "1year":
        return today - timedelta(days=365)
    if period == "actual":
        return None
    if period == "historica":
        return None
    return None


@prices_bp.get("/prices")
def list_prices():
    product_id = request.args.get("product_id", type=int)
    q = PriceHistory.query
    if product_id:
        q = q.filter(PriceHistory.product_id == product_id)
    q = q.order_by(PriceHistory.date.asc())
    items = q.limit(1000).all()
    return jsonify([p.to_dict() for p in items])


@prices_bp.post("/prices")
@require_token
def create_price():
    data = request.get_json(silent=True) or {}
    ph = PriceHistory(
        product_id=int(data.get("product_id")),
        date=(date.fromisoformat(data.get("date")) if data.get("date") else date.today()),
        cost=(float(data.get("cost")) if data.get("cost") is not None else None),
        sale=(float(data.get("sale")) if data.get("sale") is not None else None),
        unit=data.get("unit") or None,
    )
    db.session.add(ph)
    db.session.commit()
    return jsonify(ph.to_dict()), 201


# Catalog prices
@prices_bp.get("/prices/catalog")
def list_catalog():
    product_id = request.args.get("product_id", type=int)
    q = CatalogPrice.query
    if product_id:
        q = q.filter(CatalogPrice.product_id == product_id)
    items = q.order_by(CatalogPrice.date.desc()).limit(200).all()
    return jsonify([c.to_dict() for c in items])


@prices_bp.post("/prices/catalog")
@require_token
def create_catalog():
    data = request.get_json(silent=True) or {}
    c = CatalogPrice(
        product_id=int(data.get("product_id")),
        date=(date.fromisoformat(data.get("date")) if data.get("date") else date.today()),
        sale_price=float(data.get("sale_price")),
        unit=data.get("unit") or None,
    )
    db.session.add(c)
    db.session.commit()
    return jsonify(c.to_dict()), 201


# Competitor prices
@prices_bp.get("/prices/competitors")
def list_competitors():
    product_id = request.args.get("product_id", type=int)
    competitor = request.args.get("competitor")
    q = CompetitorPrice.query
    if product_id:
        q = q.filter(CompetitorPrice.product_id == product_id)
    if competitor:
        q = q.filter(CompetitorPrice.competitor == competitor)
    items = q.order_by(CompetitorPrice.date.desc()).limit(300).all()
    return jsonify([c.to_dict() for c in items])


@prices_bp.post("/prices/competitors")
@require_token
def create_competitor():
    data = request.get_json(silent=True) or {}
    c = CompetitorPrice(
        product_id=int(data.get("product_id")),
        competitor=(data.get("competitor") or "").strip() or "unknown",
        date=(date.fromisoformat(data.get("date")) if data.get("date") else date.today()),
        price=float(data.get("price")),
        unit=data.get("unit") or None,
    )
    db.session.add(c)
    db.session.commit()
    return jsonify(c.to_dict()), 201


# Summaries
@prices_bp.get("/prices/cost-trend")
def cost_trend():
    product_id = request.args.get("product_id", type=int)
    period = (request.args.get("period") or "7d").lower()
    cutoff = _period_cutoff(period)
    q = PriceHistory.query.filter(PriceHistory.product_id == product_id)
    if cutoff and period != "actual":
        q = q.filter(PriceHistory.date >= cutoff)
    q = q.filter(PriceHistory.cost.isnot(None)).order_by(PriceHistory.date.asc())
    items = [p.to_dict() for p in q.all()]
    return jsonify(items)


@prices_bp.get("/prices/sale-vs-competitor")
def sale_vs_competitor():
    product = request.args.get("product_id")
    period = (request.args.get("period") or "actual").lower()
    cutoff = _period_cutoff(period)

    def latest_catalog(p_id: int):
        c = (
            CatalogPrice.query.filter(CatalogPrice.product_id == p_id)
            .order_by(CatalogPrice.date.desc())
            .first()
        )
        return c.sale_price if c else None

    def comp_avg(p_id: int):
        q = CompetitorPrice.query.filter(CompetitorPrice.product_id == p_id)
        if cutoff and period != "historica":
            q = q.filter(CompetitorPrice.date >= cutoff)
        rows = q.all()
        vals = [r.price for r in rows if r.price is not None]
        return (sum(vals) / len(vals)) if vals else None

    if product == "all" or product is None:
        products = db.session.query(CatalogPrice.product_id).distinct().all()
        pids = [pid for (pid,) in products]
        sale_vals = []
        comp_vals = []
        for pid in pids:
            s = latest_catalog(pid)
            c = comp_avg(pid)
            if s is not None:
                sale_vals.append(s)
            if c is not None:
                comp_vals.append(c)
        return jsonify({
            "scope": "all",
            "sale_avg": (sum(sale_vals) / len(sale_vals)) if sale_vals else None,
            "competitor_avg": (sum(comp_vals) / len(comp_vals)) if comp_vals else None,
        })
    else:
        pid = int(product)
        return jsonify({
            "scope": pid,
            "sale": latest_catalog(pid),
            "competitor_avg": comp_avg(pid),
        })


@prices_bp.get("/prices/profit")
def profit_summary():
    product = request.args.get("product_id")
    period = (request.args.get("period") or "actual").lower()
    cutoff = _period_cutoff(period)

    def avg_cost(p_id: int):
        q = PriceHistory.query.filter(PriceHistory.product_id == p_id, PriceHistory.cost.isnot(None))
        if cutoff and period != "historica":
            q = q.filter(PriceHistory.date >= cutoff)
        rows = q.all()
        vals = [r.cost for r in rows if r.cost is not None]
        if period == "actual" and rows:
            return rows[-1].cost
        return (sum(vals) / len(vals)) if vals else None

    def latest_sale(p_id: int):
        c = (
            CatalogPrice.query.filter(CatalogPrice.product_id == p_id)
            .order_by(CatalogPrice.date.desc())
            .first()
        )
        return c.sale_price if c else None

    if product == "all" or product is None:
        products = db.session.query(CatalogPrice.product_id).distinct().all()
        pids = [pid for (pid,) in products]
        profits = []
        for pid in pids:
            s = latest_sale(pid)
            c = avg_cost(pid)
            if s is not None and c is not None:
                profits.append(s - c)
        return jsonify({
            "scope": "all",
            "profit_avg": (sum(profits) / len(profits)) if profits else None,
        })
    else:
        pid = int(product)
        s = latest_sale(pid)
        c = avg_cost(pid)
        return jsonify({
            "scope": pid,
            "profit": (s - c) if (s is not None and c is not None) else None,
        })
