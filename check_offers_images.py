"""
Script de diagnóstico para verificar las URLs de imágenes en ofertas semanales
Ejecutar: python check_offers_images.py
"""
from app.wsgi import app
from app.db import db
from app.models.weekly_offer import WeeklyOffer
from app.models.product import Product

with app.app_context():
    print("=" * 70)
    print("🔍 DIAGNÓSTICO: URLs de Imágenes en Ofertas Semanales")
    print("=" * 70)
    
    # Obtener las 3 ofertas
    fruta = WeeklyOffer.query.filter_by(type='fruta').order_by(WeeklyOffer.updated_at.desc()).first()
    verdura = WeeklyOffer.query.filter_by(type='verdura').order_by(WeeklyOffer.updated_at.desc()).first()
    especial = WeeklyOffer.query.filter_by(type='especial').order_by(WeeklyOffer.updated_at.desc()).first()
    
    ofertas = [
        ('Fruta', fruta),
        ('Verdura', verdura),
        ('Especial', especial)
    ]
    
    for tipo, oferta in ofertas:
        print(f"\n{'=' * 70}")
        print(f"📦 OFERTA: {tipo}")
        print('=' * 70)
        
        if not oferta:
            print(f"❌ ERROR: No existe oferta de tipo '{tipo}'")
            continue
        
        print(f"  ID de oferta: {oferta.id}")
        print(f"  Precio: {oferta.price}")
        print(f"  Precio referencia: {oferta.reference_price}")
        print(f"  Product ID: {oferta.product_id}")
        
        if not oferta.product:
            print(f"  ❌ ERROR: No hay producto asociado (product_id={oferta.product_id})")
            continue
        
        print(f"\n  📝 Producto asociado:")
        print(f"    - ID: {oferta.product.id}")
        print(f"    - Nombre: {oferta.product.name}")
        print(f"    - Categoría: {oferta.product.category}")
        
        print(f"\n  🖼️  URL de imagen:")
        if oferta.product.quality_photo_url:
            url = oferta.product.quality_photo_url
            print(f"    ✅ SÍ tiene URL: {url[:80]}{'...' if len(url) > 80 else ''}")
            
            # Verificar si es una URL válida
            if url.startswith('http://') or url.startswith('https://'):
                print(f"    ✅ URL válida (HTTP/HTTPS)")
            else:
                print(f"    ⚠️  ADVERTENCIA: URL no empieza con http:// o https://")
                print(f"    Esto puede causar problemas al descargar la imagen")
        else:
            print(f"    ❌ NO tiene URL (quality_photo_url está vacío)")
            print(f"    ⚠️  ESTE ES EL PROBLEMA: Esta imagen no aparecerá")
    
    # Resumen final
    print(f"\n{'=' * 70}")
    print("📊 RESUMEN")
    print('=' * 70)
    
    total_ofertas = sum(1 for _, o in ofertas if o is not None)
    ofertas_con_imagen = sum(
        1 for _, o in ofertas 
        if o is not None and o.product and o.product.quality_photo_url
    )
    
    print(f"  Total ofertas: {total_ofertas}/3")
    print(f"  Ofertas con imagen: {ofertas_con_imagen}/3")
    
    if ofertas_con_imagen == 3:
        print(f"\n  ✅ PERFECTO: Todas las ofertas tienen imagen")
        print(f"  Si las imágenes no aparecen, el problema es en otro lado.")
    elif ofertas_con_imagen > 0:
        print(f"\n  ⚠️  PROBLEMA PARCIAL: {3 - ofertas_con_imagen} ofertas sin imagen")
        print(f"  Necesitas configurar quality_photo_url para esas ofertas")
    else:
        print(f"\n  ❌ ERROR: NINGUNA oferta tiene imagen configurada")
        print(f"  Todas las ofertas necesitan quality_photo_url en sus productos")
    
    print(f"\n{'=' * 70}")
    print("🔧 SOLUCIÓN (si hay ofertas sin imagen):")
    print('=' * 70)
    print("\nEjecuta este SQL para configurar las URLs:")
    print()
    
    for tipo, oferta in ofertas:
        if oferta and oferta.product and not oferta.product.quality_photo_url:
            print(f"-- {tipo}: {oferta.product.name}")
            print(f"UPDATE products ")
            print(f"SET quality_photo_url = 'https://tu-url-aqui.jpg'")
            print(f"WHERE id = {oferta.product.id};")
            print()
    
    print("\nO si ya tienen foto en otro campo, puedes copiar:")
    print()
    for tipo, oferta in ofertas:
        if oferta and oferta.product and not oferta.product.quality_photo_url:
            print(f"-- Si el producto {oferta.product.name} ya tiene otra URL de foto")
            print(f"-- Revisa: SELECT * FROM products WHERE id = {oferta.product.id};")
            print(f"-- Y actualiza quality_photo_url con esa URL")
            print()
    
    print('=' * 70)

