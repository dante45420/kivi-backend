"""
Script simple para verificar las URLs de imágenes en productos de ofertas
"""
from app.wsgi import app
from app.db import db

with app.app_context():
    # SQL directo para evitar problemas con columnas que pueden no existir
    query = """
    SELECT 
        wo.id as offer_id,
        wo.type as offer_type,
        wo.price,
        wo.reference_price,
        p.id as product_id,
        p.name as product_name,
        p.quality_photo_url
    FROM weekly_offers wo
    LEFT JOIN products p ON wo.product_id = p.id
    WHERE wo.type IN ('fruta', 'verdura', 'especial')
    ORDER BY wo.type;
    """
    
    results = db.session.execute(db.text(query)).fetchall()
    
    print("=" * 80)
    print("🔍 DIAGNÓSTICO: URLs de Imágenes en Ofertas Semanales")
    print("=" * 80)
    
    if not results:
        print("\n❌ ERROR: No se encontraron ofertas semanales")
        print("   Necesitas crear ofertas para fruta, verdura y especial")
        print("\n" + "=" * 80)
        exit(1)
    
    for row in results:
        print(f"\n{'─' * 80}")
        print(f"📦 Oferta: {row.offer_type.upper()}")
        print(f"{'─' * 80}")
        print(f"  ID Oferta: {row.offer_id}")
        print(f"  Precio: {row.price}")
        print(f"  Precio Ref: {row.reference_price}")
        
        if not row.product_id:
            print(f"  ❌ ERROR: No hay producto asociado")
            continue
        
        print(f"\n  Producto:")
        print(f"    ID: {row.product_id}")
        print(f"    Nombre: {row.product_name}")
        
        print(f"\n  Imagen:")
        if row.quality_photo_url:
            url = row.quality_photo_url
            print(f"    ✅ URL: {url[:70]}{'...' if len(url) > 70 else ''}")
            
            if url.startswith('http://') or url.startswith('https://'):
                print(f"    ✅ Válida (HTTP/HTTPS)")
            else:
                print(f"    ⚠️  No empieza con HTTP - puede fallar")
        else:
            print(f"    ❌ quality_photo_url está VACÍO")
            print(f"    ⚠️  ESTE ES EL PROBLEMA - La imagen no aparecerá")
    
    # Resumen
    print(f"\n{'=' * 80}")
    print("📊 RESUMEN")
    print('=' * 80)
    
    total = len(results)
    con_imagen = sum(1 for r in results if r.quality_photo_url)
    sin_imagen = total - con_imagen
    
    print(f"\n  Total ofertas: {total}")
    print(f"  Con imagen: {con_imagen} ✅")
    print(f"  Sin imagen: {sin_imagen} ❌")
    
    if sin_imagen > 0:
        print(f"\n{'=' * 80}")
        print("🔧 SOLUCIÓN: Ejecuta este SQL en tu base de datos")
        print('=' * 80)
        print()
        
        for row in results:
            if not row.quality_photo_url:
                print(f"-- {row.offer_type}: {row.product_name}")
                print(f"UPDATE products")
                print(f"SET quality_photo_url = 'https://tu-servidor.com/imagen-{row.product_name.lower().replace(' ', '-')}.jpg'")
                print(f"WHERE id = {row.product_id};")
                print()
        
        print("\n💡 TIP: Usa las mismas URLs que ya funcionan en el catálogo")
        print("   Revisa en la página de Productos cuáles URLs ya tienes configuradas")
    else:
        print(f"\n  ✅ PERFECTO: Todas las ofertas tienen imagen configurada")
        print(f"\n  Si aún así no aparecen, revisa:")
        print(f"    1. Que las URLs sean accesibles públicamente")
        print(f"    2. Los logs del backend cuando generas el carrusel")
        print(f"    3. Que el directorio generated_images/ exista en el servidor")
    
    print("\n" + "=" * 80)

