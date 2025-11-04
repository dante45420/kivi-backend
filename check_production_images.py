"""
Script para conectarse a la BD de producción y revisar las URLs de imágenes
"""
import os
from sqlalchemy import create_engine, text

# La URL de la BD de producción debe estar en las variables de entorno
# O puedes reemplazarla aquí directamente (temporal)
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://...')  # Reemplazar con tu URL

if 'postgresql' not in DATABASE_URL:
    print("⚠️  ADVERTENCIA: No se encontró DATABASE_URL de producción")
    print("   Por favor, reemplaza DATABASE_URL en este script con tu URL de producción")
    print("   La puedes obtener de Render Dashboard > Environment")
    exit(1)

# Crear conexión
engine = create_engine(DATABASE_URL)

print("=" * 80)
print("🔍 CONEXIÓN A BASE DE DATOS DE PRODUCCIÓN")
print("=" * 80)

with engine.connect() as conn:
    # Query para ver ofertas y sus imágenes
    query = text("""
        SELECT 
            wo.id as offer_id,
            wo.type as tipo,
            wo.price,
            wo.reference_price,
            p.id as product_id,
            p.name as producto,
            p.quality_photo_url
        FROM weekly_offers wo
        LEFT JOIN products p ON wo.product_id = p.id
        WHERE wo.type IN ('fruta', 'verdura', 'especial')
        ORDER BY wo.type;
    """)
    
    results = conn.execute(query).fetchall()
    
    if not results:
        print("\n❌ No se encontraron ofertas semanales")
        exit(1)
    
    print(f"\n✅ Encontradas {len(results)} ofertas\n")
    
    for row in results:
        print(f"{'─' * 80}")
        print(f"📦 {row.tipo.upper()}: {row.producto}")
        print(f"{'─' * 80}")
        print(f"  Precio: {row.price}")
        print(f"  Precio Ref: {row.reference_price}")
        
        if row.quality_photo_url:
            url = row.quality_photo_url
            print(f"\n  🖼️  URL Imagen:")
            print(f"    {url}")
            
            # Verificar tipo de URL
            if url.startswith('data:image'):
                print(f"    ⚠️  Es una imagen BASE64 (embebida)")
                print(f"    Tamaño: ~{len(url)} caracteres")
            elif url.startswith('http'):
                print(f"    ✅ Es una URL HTTP/HTTPS")
            else:
                print(f"    ⚠️  Formato no reconocido")
        else:
            print(f"\n  ❌ NO tiene quality_photo_url")
        
        print()
    
    # Ver ejemplos de productos que SÍ tienen foto
    print("=" * 80)
    print("📸 PRODUCTOS CON FOTOS (ejemplos)")
    print("=" * 80)
    
    query2 = text("""
        SELECT id, name, quality_photo_url
        FROM products
        WHERE quality_photo_url IS NOT NULL
        AND (LOWER(name) LIKE '%alcachofa%' 
             OR LOWER(name) LIKE '%tomate%' 
             OR LOWER(name) LIKE '%mango%')
        LIMIT 5;
    """)
    
    examples = conn.execute(query2).fetchall()
    
    for ex in examples:
        print(f"\n  {ex.name}:")
        url = ex.quality_photo_url
        if url.startswith('data:image'):
            print(f"    Tipo: BASE64 embebida")
            print(f"    Inicio: {url[:50]}...")
        else:
            print(f"    URL: {url[:80]}{'...' if len(url) > 80 else ''}")

print("\n" + "=" * 80)

