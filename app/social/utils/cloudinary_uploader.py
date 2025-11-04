"""
Utilidad para subir imágenes a Cloudinary
Para que las imágenes persistan entre redeploys
"""
import os
import cloudinary
import cloudinary.uploader
from typing import Optional

# Configurar Cloudinary al importar
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)


def upload_offer_image(
    local_image_path: str,
    product_name: str,
    offer_type: str  # 'fruta', 'verdura', 'especial'
) -> Optional[str]:
    """
    Sube una imagen de oferta a Cloudinary
    
    Args:
        local_image_path: Ruta local de la imagen generada
        product_name: Nombre del producto (ej: "Tomate")
        offer_type: Tipo de oferta ('fruta', 'verdura', 'especial')
    
    Returns:
        URL pública de Cloudinary o None si falla
    """
    try:
        # Verificar que Cloudinary esté configurado
        if not all([
            os.getenv('CLOUDINARY_CLOUD_NAME'),
            os.getenv('CLOUDINARY_API_KEY'),
            os.getenv('CLOUDINARY_API_SECRET')
        ]):
            print("⚠️  Cloudinary no configurado - usando almacenamiento local (se borrará en redeploy)")
            return None
        
        # Crear public_id único para la imagen
        safe_name = product_name.lower().replace(' ', '_').replace('/', '_')
        public_id = f"ofertas/{offer_type}_{safe_name}"
        
        print(f"📤 Subiendo imagen a Cloudinary: {public_id}")
        
        # Subir imagen
        result = cloudinary.uploader.upload(
            local_image_path,
            folder="kivi",  # Carpeta raíz en Cloudinary
            public_id=public_id,
            overwrite=True,  # Reemplazar si ya existe
            resource_type="image",
            invalidate=True  # Invalidar cache del CDN
        )
        
        # Obtener URL segura (HTTPS)
        url = result['secure_url']
        print(f"✅ Imagen subida exitosamente: {url[:60]}...")
        
        return url
        
    except Exception as e:
        print(f"❌ Error subiendo imagen a Cloudinary: {e}")
        print(f"   Usando almacenamiento local (se borrará en redeploy)")
        return None


def delete_offer_image(public_id: str) -> bool:
    """
    Elimina una imagen de Cloudinary
    
    Args:
        public_id: ID público de la imagen en Cloudinary
    
    Returns:
        True si se eliminó correctamente
    """
    try:
        result = cloudinary.uploader.destroy(public_id)
        return result.get('result') == 'ok'
    except Exception as e:
        print(f"Error eliminando imagen de Cloudinary: {e}")
        return False


def get_cloudinary_url_from_local_path(local_path: str) -> str:
    """
    Extrae la URL de Cloudinary desde una ruta local
    Útil para migrar imágenes existentes
    """
    # Esto es para futuro uso si necesitas migrar imágenes
    filename = os.path.basename(local_path)
    name_without_ext = os.path.splitext(filename)[0]
    
    # Reconstruir URL de Cloudinary
    cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME')
    if not cloud_name:
        return local_path
    
    return f"https://res.cloudinary.com/{cloud_name}/image/upload/kivi/ofertas/{name_without_ext}"

