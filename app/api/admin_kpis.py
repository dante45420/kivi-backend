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
from ..models.product import Product
from .auth import require_token


admin_kpis_bp = Blueprint("admin_kpis", __name__)


def parse_date_params():
    """Helper para parsear parámetros de fecha"""
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        except:
            date_from = None
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        except:
            date_to = None
    
    return date_from, date_to


@admin_kpis_bp.get("/admin/kpis/overview")
@require_token
def get_kpis_overview():
    """KPIs principales del negocio"""
    try:
        date_from, date_to = parse_date_params()
        
        # Filtro base de órdenes
        orders_query = Order.query
        if date_from:
            orders_query = orders_query.filter(func.date(Order.created_at) >= date_from)
        if date_to:
            orders_query = orders_query.filter(func.date(Order.created_at) <= date_to)
        
        orders = orders_query.all()
        order_ids = [o.id for o in orders]
        
        # 1. TICKET PROMEDIO
        if orders:
            # Total facturado desde charges
            charges = Charge.query.filter(
                Charge.order_id.in_(order_ids),
                Charge.status != 'cancelled'
            ).all()
            
            total_billed = sum(
                (c.charged_qty or c.qty or 0) * (c.unit_price or 0)
                for c in charges
            )
            
            # Total costos desde purchases
            purchases = Purchase.query.filter(
                Purchase.order_id.in_(order_ids)
            ).all()
            
            total_costs = 0
            for p in purchases:
                if p.price_total:
                    total_costs += float(p.price_total)
                else:
                    # Calcular desde price_per_unit
                    unit = p.charged_unit or 'kg'
                    qty = float(p.qty_kg or 0) if unit == 'kg' else float(p.qty_unit or 0)
                    total_costs += float(p.price_per_unit or 0) * qty
            
            # Utilidad
            utilidad = total_billed - total_costs
            
            # Desglose por cliente
            customer_totals = {}
            for c in charges:
                if c.customer_id:
                    customer_id = c.customer_id
                    amount = (c.charged_qty or c.qty or 0) * (c.unit_price or 0)
                    
                    if customer_id not in customer_totals:
                        customer_totals[customer_id] = {
                            'customer_id': customer_id,
                            'total': 0,
                            'num_pedidos': set()
                        }
                    
                    customer_totals[customer_id]['total'] += amount
                    customer_totals[customer_id]['num_pedidos'].add(c.order_id)
            
            # Obtener nombres de clientes
            customer_breakdown = []
            for cid, data in customer_totals.items():
                customer = Customer.query.get(cid)
                customer_breakdown.append({
                    'customer_id': cid,
                    'customer_name': customer.name if customer else f'Cliente {cid}',
                    'total': round(data['total'], 2),
                    'num_pedidos': len(data['num_pedidos']),
                    'promedio_por_pedido': round(data['total'] / len(data['num_pedidos']), 2) if len(data['num_pedidos']) > 0 else 0
                })
            
            # Ordenar por total descendente
            customer_breakdown.sort(key=lambda x: x['total'], reverse=True)
            
            num_clientes = len(customer_totals)
            
            ticket_promedio = {
                'total': round(total_billed, 2),
                'utilidad': round(utilidad, 2),
                'costos': round(total_costs, 2),
                'num_pedidos': len(orders),
                'num_clientes': num_clientes,
                'promedio_por_pedido': round(total_billed / len(orders), 2) if len(orders) > 0 else 0,
                'promedio_por_cliente': round(total_billed / num_clientes, 2) if num_clientes > 0 else 0,
                'margen_utilidad_porcentaje': round((utilidad / total_billed * 100), 2) if total_billed > 0 else 0,
                'desglose_clientes': customer_breakdown
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
                'margen_utilidad_porcentaje': 0,
                'desglose_clientes': []
            }
        
        # 2. TASA DE RECOMPRA
        recompra_days = int(request.args.get('recompra_days', 15))
        
        # Clientes con sus pedidos en el periodo
        query = db.session.query(
            Charge.customer_id,
            func.count(func.distinct(Charge.order_id)).label('num_orders')
        ).join(Order, Charge.order_id == Order.id).filter(
            Charge.status != 'cancelled',
            Charge.customer_id.isnot(None)
        )
        
        if date_from:
            query = query.filter(func.date(Order.created_at) >= date_from)
        if date_to:
            query = query.filter(func.date(Order.created_at) <= date_to)
        
        customers_with_orders = query.group_by(Charge.customer_id).all()
        
        total_customers = len(customers_with_orders)
        recompra_customers = len([c for c in customers_with_orders if c.num_orders > 1])
        
        tasa_recompra = {
            'plazo_dias': recompra_days,
            'total_clientes': total_customers,
            'recompraron': recompra_customers,
            'tasa_porcentaje': round((recompra_customers / total_customers * 100), 2) if total_customers > 0 else 0
        }
        
        # 3. CLIENTES ACTIVOS
        activo_days = int(request.args.get('activo_days', 15))
        fecha_limite = datetime.now().date() - timedelta(days=activo_days)
        
        # Clientes con pedidos recientes
        clientes_activos = db.session.query(
            func.count(func.distinct(Charge.customer_id))
        ).join(Order, Charge.order_id == Order.id).filter(
            func.date(Order.created_at) >= fecha_limite,
            Charge.status != 'cancelled',
            Charge.customer_id.isnot(None)
        ).scalar() or 0
        
        # Total de clientes (alguna vez)
        total_clientes_historico = db.session.query(
            func.count(func.distinct(Charge.customer_id))
        ).filter(
            Charge.customer_id.isnot(None)
        ).scalar() or 0
        
        # Nuevos este mes
        inicio_mes = datetime.now().replace(day=1).date()
        
        # Clientes que compraron este mes
        clientes_este_mes = set(
            c.customer_id for c in Charge.query.join(Order, Charge.order_id == Order.id).filter(
                func.date(Order.created_at) >= inicio_mes,
                Charge.customer_id.isnot(None)
            ).all()
        )
        
        # Clientes que compraron antes de este mes
        clientes_antes_mes = set(
            c.customer_id for c in Charge.query.join(Order, Charge.order_id == Order.id).filter(
                func.date(Order.created_at) < inicio_mes,
                Charge.customer_id.isnot(None)
            ).all()
        )
        
        # Nuevos = compraron este mes pero NO antes
        nuevos_mes = len(clientes_este_mes - clientes_antes_mes)
        
        clientes_stats = {
            'activos': clientes_activos,
            'filtro_dias': activo_days,
            'total_historico': total_clientes_historico,
            'nuevos_mes': nuevos_mes,
            'tasa_actividad_porcentaje': round((clientes_activos / total_clientes_historico * 100), 2) if total_clientes_historico > 0 else 0
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
    
    except Exception as e:
        print(f"Error en get_kpis_overview: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@admin_kpis_bp.get("/admin/kpis/productos-top")
@require_token
def get_top_products():
    """Productos más vendidos con filtros por utilidad, unidades o monto"""
    try:
        limit = int(request.args.get('limit', 10))
        sort_by = request.args.get('sort_by', 'revenue')  # 'revenue', 'quantity', 'profit'
        date_from, date_to = parse_date_params()
        
        # Obtener datos agregados por producto
        query = db.session.query(
            Charge.product_id,
            func.sum(Charge.charged_qty).label('total_qty'),
            func.sum(Charge.charged_qty * Charge.unit_price).label('total_revenue')
        ).join(Order, Charge.order_id == Order.id).filter(
            Charge.status != 'cancelled',
            Charge.product_id.isnot(None),
            Charge.charged_qty.isnot(None),
            Charge.unit_price.isnot(None)
        )
        
        if date_from:
            query = query.filter(func.date(Order.created_at) >= date_from)
        if date_to:
            query = query.filter(func.date(Order.created_at) <= date_to)
        
        products_data = query.group_by(Charge.product_id).all()
        
        # Calcular costos por producto
        costs_query = db.session.query(
            Purchase.product_id,
            func.sum(Purchase.price_total).label('total_cost')
        ).join(Order, Purchase.order_id == Order.id).filter(
            Purchase.product_id.isnot(None)
        )
        
        if date_from:
            costs_query = costs_query.filter(func.date(Order.created_at) >= date_from)
        if date_to:
            costs_query = costs_query.filter(func.date(Order.created_at) <= date_to)
        
        costs_data = {row.product_id: float(row.total_cost or 0) for row in costs_query.group_by(Purchase.product_id).all()}
        
        # Construir resultado con utilidad
        result = []
        for product_id, qty, revenue in products_data:
            product = Product.query.get(product_id)
            if product:
                cost = costs_data.get(product_id, 0)
                profit = float(revenue or 0) - cost
                
                result.append({
                    'product_id': product_id,
                    'product_name': product.name,
                    'cantidad_vendida': round(float(qty or 0), 2),
                    'ingresos_totales': round(float(revenue or 0), 2),
                    'costos_totales': round(cost, 2),
                    'utilidad': round(profit, 2)
                })
        
        # Ordenar según el criterio solicitado
        if sort_by == 'quantity':
            result.sort(key=lambda x: x['cantidad_vendida'], reverse=True)
        elif sort_by == 'profit':
            result.sort(key=lambda x: x['utilidad'], reverse=True)
        else:  # revenue (default)
            result.sort(key=lambda x: x['ingresos_totales'], reverse=True)
        
        # Limitar resultados
        result = result[:limit]
        
        return jsonify(result)
    
    except Exception as e:
        print(f"Error en get_top_products: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
