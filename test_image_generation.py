"""
Script de prueba para generar imágenes de ofertas
Ejecutar: python test_image_generation.py
"""
import os
import sys

# Agregar el directorio app al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.social.utils.image_processor import generate_offer_image

def test_generate_image():
    """Prueba la generación de una imagen de oferta"""
    print("=" * 60)
    print("🧪 PRUEBA: Generación de Imagen de Oferta")
    print("=" * 60)
    
    # Datos de prueba - usar una imagen pública
    test_cases = [
        {
            "offer_type": "fruta",
            "product_name": "Naranja",
            "price": "$1.500 kg",
            "reference_price": "Jumbo $2.500 kg",
            "product_image_url": "https://images.unsplash.com/photo-1582979512210-99b6a53386f9?w=800"  # Naranja
        },
        {
            "offer_type": "verdura",
            "product_name": "Lechuga",
            "price": "$900 kg",
            "reference_price": "Jumbo $1.500 kg",
            "product_image_url": "https://images.unsplash.com/photo-1622206151226-18ca2c9ab4a1?w=800"  # Lechuga
        },
        {
            "offer_type": "especial",
            "product_name": "Mango",
            "price": "$2.400 kg",
            "reference_price": "Kivi: 4.000 kg",
            "product_image_url": "https://images.unsplash.com/photo-1553279768-865429fa0078?w=800"  # Mango
        }
    ]
    
    print("\n📋 Casos de prueba:")
    for i, test in enumerate(test_cases, 1):
        print(f"  {i}. {test['offer_type'].capitalize()}: {test['product_name']} - {test['price']}")
    
    print("\n" + "=" * 60)
    
    results = []
    for i, test in enumerate(test_cases, 1):
        print(f"\n🔄 Generando imagen {i}/{len(test_cases)}: {test['product_name']}")
        print("-" * 60)
        
        try:
            result = generate_offer_image(
                offer_type=test['offer_type'],
                product_name=test['product_name'],
                price=test['price'],
                reference_price=test['reference_price'],
                product_image_url=test['product_image_url']
            )
            
            if result and os.path.exists(result):
                file_size = os.path.getsize(result) / 1024  # KB
                results.append({
                    "success": True,
                    "product": test['product_name'],
                    "path": result,
                    "size": f"{file_size:.2f} KB"
                })
                print(f"✅ ÉXITO: Imagen generada - {file_size:.2f} KB")
            else:
                results.append({
                    "success": False,
                    "product": test['product_name'],
                    "error": "Archivo no generado"
                })
                print(f"❌ ERROR: No se generó el archivo")
        except Exception as e:
            results.append({
                "success": False,
                "product": test['product_name'],
                "error": str(e)
            })
            print(f"❌ ERROR: {e}")
    
    # Resumen
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE RESULTADOS")
    print("=" * 60)
    
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    
    print(f"\n✅ Exitosas: {successful}/{len(results)}")
    print(f"❌ Fallidas: {failed}/{len(results)}")
    
    if successful > 0:
        print("\n📁 Imágenes generadas:")
        for r in results:
            if r['success']:
                print(f"  ✓ {r['product']}: {r['path']} ({r['size']})")
    
    if failed > 0:
        print("\n❌ Errores:")
        for r in results:
            if not r['success']:
                print(f"  ✗ {r['product']}: {r['error']}")
    
    print("\n" + "=" * 60)
    
    if successful == len(results):
        print("🎉 ¡TODAS LAS PRUEBAS PASARON!")
        print("\n💡 Puedes ver las imágenes en: backend/generated_images/")
        return True
    else:
        print("⚠️  ALGUNAS PRUEBAS FALLARON")
        print("\n💡 Revisa los logs arriba para más detalles")
        return False


if __name__ == "__main__":
    try:
        success = test_generate_image()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

