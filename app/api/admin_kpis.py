"""
API para KPIs y Analytics (Admin)
"""
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from sqlalchemy import func, and_

from ..db import db
from ..models.order import Order
from ..models.order_item import OrderItem
from ..models.customer import Customer
from ..models.purchase import Purchase
from ..models.charge import Charge
from .auth import require_token


admin_kpis_bp = Blueprint("admin_kpis", __name__)


def parse_date_params():
    """Helper para parsear parámetros de fecha"""
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    if date_from:
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
    if date_to:
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
    
    return date_from, date_to


@admin_kpis_bp.get("/admin/kpis/overview")
@require_token
def get_kpis_overview():
    """KPIs principales del negocio"""
    date_from, date_to = parse_date_params()
    
    # Filtro base de órdenes
    orders_query = Order.query
    if date_from:
        orders_query = orders_query.filter(Order.date >= date_from)
    if date_to:
        orders_query = orders_query.filter(Order.date <= date_to)
    
    orders = orders_query.all()
    order_ids = [o.id for o in orders]
    
    # 1. TICKET PROMEDIO
    if orders:
        # Total facturado
        total_billed = sum(
            sum(
                (c.charged_qty or c.qty or 0) * (c.sale_unit_price or 0)
                for c in Charge.query.filter(
                    Charge.order_id == o.id,
                    Charge.status != 'cancelled'
                ).all()
            )
            for o in orders
        )
        
        # Total costos
        total_costs = sum(
            sum(
                (p.qty_kg or 0) * (p.price_per_unit or 0)
                for p in Purchase.query.filter_by(order_id=o.id).all()
            )
            for o in orders
        )
        
        # Utilidad
        utilidad = total_billed - total_costs
        
        # Clientes únicos
        unique_customers = len(set(
            c.customer_id 
            for o in orders 
            for c in Charge.query.filter_by(order_id=o.id).all()
        ))
        
        ticket_promedio = {
            'total': round(total_billed, 2),
            'utilidad': round(utilidad, 2),
            'costos': round(total_costs, 2),
            'num_pedidos': len(orders),
            'num_clientes': unique_customers,
            'promedio_por_pedido': round(total_billed / len(orders), 2) if orders else 0,
            'promedio_por_cliente': round(total_billed / unique_customers, 2) if unique_customers else 0,
            'margen_utilidad_porcentaje': round((utilidad / total_billed * 100), 2) if total_billed else 0
        }
    else:
        ticket_promedio = {
            'total': 0,
            'utilidad': 0,
            'costos': 0,
            'num_pedidos': 0,
            'num_clientes': 0,
            'promedio_por_pedido': 0,
            'promedio_por_cliente': 0,
            'margen_utilidad_porcentaje': 0
        }
    
    # 2. TASA DE RECOMPRA
    recompra_days = int(request.args.get('recompra_days', 15))
    
    # Clientes que compraron en el periodo
    query = db.session.query(
        Charge.customer_id,
        func.count(func.distinct(Charge.order_id)).label('num_orders')
    ).join(Order).filter(
        Charge.status != 'cancelled'
    )
    
    if date_from:
        query = query.filter(Order.date >= date_from)
    if date_to:
        query = query.filter(Order.date <= date_to)
    
    customers_with_orders = query.group_by(Charge.customer_id).all()
    
    total_customers = len(customers_with_orders)
    recompra_customers = len([c for c in customers_with_orders if c.num_orders > 1])
    
    tasa_recompra = {
        'plazo_dias': recompra_days,
        'total_clientes': total_customers,
        'recompraron': recompra_customers,
        'tasa_porcentaje': round((recompra_customers / total_customers * 100), 2) if total_customers else 0
    }
    
    # 3. CLIENTES ACTIVOS
    activo_days = int(request.args.get('activo_days', 15))
    fecha_limite = datetime.now().date() - timedelta(days=activo_days)
    
    # Clientes con pedidos recientes
    clientes_activos = db.session.query(
        func.count(func.distinct(Charge.customer_id))
    ).join(Order).filter(
        Order.date >= fecha_limite,
        Charge.status != 'cancelled'
    ).scalar() or 0
    
    # Total de clientes (alguna vez)
    total_clientes_historico = db.session.query(
        func.count(func.distinct(Charge.customer_id))
    ).scalar() or 0
    
    # Nuevos este mes
    inicio_mes = datetime.now().replace(day=1).date()
    nuevos_mes = db.session.query(
        func.count(func.distinct(Customer.id))
    ).filter(
        Customer.id.in_(
            db.session.query(Charge.customer_id).join(Order).filter(
                Order.date >= inicio_mes
            ).distinct()
        ),
        ~Customer.id.in_(
            db.session.query(Charge.customer_id).join(Order).filter(
                Order.date < inicio_mes
            ).distinct()
        )
    ).scalar() or 0
    
    clientes_stats = {
        'activos': clientes_activos,
        'filtro_dias': activo_days,
        'total_historico': total_clientes_historico,
        'nuevos_mes': nuevos_mes,
        'tasa_actividad_porcentaje': round((clientes_activos / total_clientes_historico * 100), 2) if total_clientes_historico else 0
    }
    
    return jsonify({
        'ticket_promedio': ticket_promedio,
        'tasa_recompra': tasa_recompra,
        'clientes': clientes_stats,
        'periodo': {
            'desde': date_from.isoformat() if date_from else None,
            'hasta': date_to.isoformat() if date_to else None
        }
    })


@admin_kpis_bp.get("/admin/kpis/productos-top")
@require_token
def get_top_products():
    """Productos más vendidos"""
    limit = int(request.args.get('limit', 10))
    date_from, date_to = parse_date_params()
    
    query = db.session.query(
        Charge.product_id,
        func.sum(Charge.charged_qty or Charge.qty).label('total_qty'),
        func.sum((Charge.charged_qty or Charge.qty) * Charge.sale_unit_price).label('total_revenue')
    ).join(Order).filter(
        Charge.status != 'cancelled'
    )
    
    if date_from:
        query = query.filter(Order.date >= date_from)
    if date_to:
        query = query.filter(Order.date <= date_to)
    
    top_products = query.group_by(
        Charge.product_id
    ).order_by(
        func.sum((Charge.charged_qty or Charge.qty) * Charge.sale_unit_price).desc()
    ).limit(limit).all()
    
    from ..models.product import Product
    result = []
    for product_id, qty, revenue in top_products:
        product = Product.query.get(product_id)
        result.append({
            'product_id': product_id,
            'product_name': product.name if product else 'Desconocido',
            'cantidad_vendida': round(qty, 2) if qty else 0,
            'ingresos_totales': round(revenue, 2) if revenue else 0
        })
    
    return jsonify(result)

