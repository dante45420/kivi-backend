"""
Generador de videos para historias de Instagram
Crea videos de 15 segundos con animaciones simples y música
"""
import os
import subprocess
from typing import Dict, Optional, List
import random

# Directorio de assets y generación
ASSETS_DIR = os.path.join(os.path.dirname(__file__), '../assets')
MUSIC_DIR = os.path.join(ASSETS_DIR, 'music')
GENERATED_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'generated_images', 'stories')

# Asegurar directorios
os.makedirs(MUSIC_DIR, exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)

# Dimensiones de historia
STORY_WIDTH = 1080
STORY_HEIGHT = 1920
FPS = 30
DURATION = 15


class StoryVideoGenerator:
    """Genera videos de historias con animaciones simples"""
    
    def __init__(self):
        self.width = STORY_WIDTH
        self.height = STORY_HEIGHT
        self.fps = FPS
        self.duration = DURATION
        self._check_ffmpeg()
    
    def _check_ffmpeg(self):
        """Verifica que FFmpeg esté instalado"""
        try:
            subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                check=True
            )
            print("✅ FFmpeg disponible")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️  FFmpeg no encontrado. Los videos no se podrán generar.")
            print("   Instalar con: brew install ffmpeg (Mac) o apt-get install ffmpeg (Linux)")
    
    def generate_story_video(
        self,
        theme: str,
        base_image_path: str,
        animation_style: str = 'zoom_in',
        music_path: Optional[str] = None
    ) -> str:
        """
        Genera un video de historia a partir de una imagen estática
        
        Args:
            theme: Tema de la historia
            base_image_path: Ruta a la imagen base
            animation_style: Estilo de animación ('zoom_in', 'zoom_out', 'pan_left', 'pan_right', 'fade', 'static')
            music_path: Ruta a archivo de música (opcional)
        
        Returns:
            Ruta del video generado
        """
        
        if not os.path.exists(base_image_path):
            raise FileNotFoundError(f"Imagen base no encontrada: {base_image_path}")
        
        # Nombre del archivo de salida
        base_name = os.path.basename(base_image_path).replace('.png', '')
        output_filename = f"{base_name}_video.mp4"
        output_path = os.path.join(GENERATED_DIR, output_filename)
        
        # Generar video según el estilo de animación
        if animation_style == 'zoom_in':
            self._create_zoom_in_video(base_image_path, output_path)
        elif animation_style == 'zoom_out':
            self._create_zoom_out_video(base_image_path, output_path)
        elif animation_style == 'pan_left':
            self._create_pan_video(base_image_path, output_path, direction='left')
        elif animation_style == 'pan_right':
            self._create_pan_video(base_image_path, output_path, direction='right')
        elif animation_style == 'fade':
            self._create_fade_video(base_image_path, output_path)
        else:  # static
            self._create_static_video(base_image_path, output_path)
        
        # Agregar música si se especifica
        if music_path and os.path.exists(music_path):
            output_path = self._add_music(output_path, music_path)
        
        print(f"✅ Video generado: {output_filename}")
        return output_path
    
    def _create_zoom_in_video(self, input_image: str, output_path: str):
        """Crea video con efecto zoom in (Ken Burns)"""
        
        # FFmpeg filter para zoom in suave
        # Empieza en 100% y termina en 120%
        filter_complex = (
            f"[0:v]scale={self.width*1.2}:{self.height*1.2},"
            f"zoompan=z='min(zoom+0.0015,1.2)':d={self.fps * self.duration}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"s={self.width}x{self.height}:fps={self.fps}"
        )
        
        cmd = [
            'ffmpeg',
            '-loop', '1',
            '-i', input_image,
            '-filter_complex', filter_complex,
            '-t', str(self.duration),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-y',  # Sobrescribir si existe
            output_path
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, check=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error generando zoom in video: {e.stderr}")
            raise
    
    def _create_zoom_out_video(self, input_image: str, output_path: str):
        """Crea video con efecto zoom out"""
        
        # Empieza en 120% y termina en 100%
        filter_complex = (
            f"[0:v]scale={self.width*1.2}:{self.height*1.2},"
            f"zoompan=z='if(lte(zoom,1.0),1.0,max(1.0,zoom-0.0015))':"
            f"d={self.fps * self.duration}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"s={self.width}x{self.height}:fps={self.fps}"
        )
        
        cmd = [
            'ffmpeg',
            '-loop', '1',
            '-i', input_image,
            '-filter_complex', filter_complex,
            '-t', str(self.duration),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-y',
            output_path
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, check=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error generando zoom out video: {e.stderr}")
            raise
    
    def _create_pan_video(self, input_image: str, output_path: str, direction: str = 'left'):
        """Crea video con efecto panorámico (pan)"""
        
        if direction == 'left':
            # Pan de derecha a izquierda
            filter_complex = (
                f"[0:v]scale={int(self.width*1.3)}:-1,"
                f"crop={self.width}:{self.height}:'(in_w-out_w)/2+((in_w-out_w)/2)*sin(t/{self.duration}*2*PI)':"
                f"(in_h-out_h)/2"
            )
        else:  # right
            # Pan de izquierda a derecha
            filter_complex = (
                f"[0:v]scale={int(self.width*1.3)}:-1,"
                f"crop={self.width}:{self.height}:'(in_w-out_w)/2-((in_w-out_w)/2)*sin(t/{self.duration}*2*PI)':"
                f"(in_h-out_h)/2"
            )
        
        cmd = [
            'ffmpeg',
            '-loop', '1',
            '-i', input_image,
            '-filter_complex', filter_complex,
            '-t', str(self.duration),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-y',
            output_path
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, check=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error generando pan video: {e.stderr}")
            raise
    
    def _create_fade_video(self, input_image: str, output_path: str):
        """Crea video con efecto fade in/out"""
        
        # Fade in primeros 2s, fade out últimos 2s
        filter_complex = (
            f"[0:v]fade=t=in:st=0:d=2,fade=t=out:st={self.duration-2}:d=2,"
            f"scale={self.width}:{self.height}"
        )
        
        cmd = [
            'ffmpeg',
            '-loop', '1',
            '-i', input_image,
            '-vf', filter_complex,
            '-t', str(self.duration),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-y',
            output_path
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, check=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error generando fade video: {e.stderr}")
            raise
    
    def _create_static_video(self, input_image: str, output_path: str):
        """Crea video estático (sin animación) a partir de imagen"""
        
        cmd = [
            'ffmpeg',
            '-loop', '1',
            '-i', input_image,
            '-vf', f'scale={self.width}:{self.height}',
            '-t', str(self.duration),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-y',
            output_path
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, check=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error generando video estático: {e.stderr}")
            raise
    
    def _add_music(self, video_path: str, music_path: str) -> str:
        """Agrega música de fondo al video"""
        
        output_filename = video_path.replace('.mp4', '_con_musica.mp4')
        
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-i', music_path,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-shortest',  # Duración del más corto (video)
            '-y',
            output_filename
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, check=True, text=True)
            # Eliminar video sin música
            os.remove(video_path)
            print(f"✅ Música agregada al video")
            return output_filename
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Error agregando música: {e.stderr}")
            return video_path  # Devolver video original sin música
    
    def generate_video_from_story(
        self,
        theme: str,
        image_path: str,
        use_random_animation: bool = True
    ) -> str:
        """
        Genera video con animación aleatoria o específica según el tema
        
        Args:
            theme: Tema de la historia
            image_path: Ruta de la imagen base
            use_random_animation: Si True, elige animación aleatoria
        
        Returns:
            Ruta del video generado
        """
        
        # Animaciones recomendadas por tema
        theme_animations = {
            'tip_semana': ['zoom_in', 'static'],
            'doggo_prueba': ['zoom_in', 'fade'],
            'mito_realidad': ['pan_left', 'static'],
            'beneficio_dia': ['zoom_out', 'fade'],
            'sabias_que': ['zoom_in', 'fade'],
            'detras_camaras': ['pan_right', 'fade'],
            'cliente_semana': ['static', 'fade'],
            'desafio_receta': ['pan_left', 'zoom_in'],
        }
        
        if use_random_animation:
            animations = theme_animations.get(theme, ['zoom_in', 'fade', 'static'])
            animation = random.choice(animations)
        else:
            animation = theme_animations.get(theme, ['static'])[0]
        
        print(f"🎬 Generando video con animación: {animation}")
        
        # Buscar música (si existe)
        music_files = self._get_available_music()
        music_path = random.choice(music_files) if music_files else None
        
        return self.generate_story_video(
            theme=theme,
            base_image_path=image_path,
            animation_style=animation,
            music_path=music_path
        )
    
    def _get_available_music(self) -> List[str]:
        """Obtiene lista de archivos de música disponibles"""
        if not os.path.exists(MUSIC_DIR):
            return []
        
        music_files = []
        for file in os.listdir(MUSIC_DIR):
            if file.endswith(('.mp3', '.wav', '.m4a')):
                music_files.append(os.path.join(MUSIC_DIR, file))
        
        return music_files
    
    def create_thumbnail(self, video_path: str) -> str:
        """Crea thumbnail del video (frame del medio)"""
        
        thumbnail_path = video_path.replace('.mp4', '_thumb.jpg')
        
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-ss', str(self.duration // 2),  # Frame del medio
            '-vframes', '1',
            '-vf', f'scale={self.width}:{self.height}',
            '-y',
            thumbnail_path
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, check=True, text=True)
            print(f"✅ Thumbnail creado: {os.path.basename(thumbnail_path)}")
            return thumbnail_path
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Error creando thumbnail: {e.stderr}")
            return ""
    
    def batch_generate_videos(
        self,
        image_paths: List[str],
        themes: List[str]
    ) -> List[str]:
        """
        Genera múltiples videos en batch
        
        Args:
            image_paths: Lista de rutas de imágenes
            themes: Lista de temas correspondientes
        
        Returns:
            Lista de rutas de videos generados
        """
        
        if len(image_paths) != len(themes):
            raise ValueError("Debe haber un tema por cada imagen")
        
        video_paths = []
        
        for image_path, theme in zip(image_paths, themes):
            try:
                video_path = self.generate_video_from_story(theme, image_path)
                video_paths.append(video_path)
            except Exception as e:
                print(f"❌ Error generando video para {image_path}: {str(e)}")
        
        return video_paths

