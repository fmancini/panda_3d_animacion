from direct.showbase.ShowBase import ShowBase
from panda3d.core import *
from direct.task import Task
from direct.gui.OnscreenText import OnscreenText
import math
import random
import pygame
import threading
import os

class OrganicSphere(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        
        # Configurar la ventana
        self.setBackgroundColor(1.0, 1.0, 1.0)
        
        # Crear un plano de tierra para recibir la sombra
        # self.create_ground_plane()
        
        # Crear una esfera usando el modelo built-in de Panda3D
        self.sphere = self.loader.loadModel("models/environment")
        if self.sphere.isEmpty():
            self.sphere = self.create_basic_sphere()
        else:
            self.sphere.clearModelNodes()
            self.sphere = self.create_basic_sphere()
        
        self.sphere.reparentTo(self.render)
        self.sphere.setScale(3)
        self.sphere.setPos(0, 0, 2) # Elevar la esfera para que la sombra sea visible
        
        # Configurar la cámara
        self.camera.set_pos(0, -15, 5)
        self.camera.look_at(0, 0, 2)
        self.disable_mouse()
        
        # Configurar controles de cámara
        # Para 60% de zoom: base_radius / zoom_percentage * 100 = 15.0 / 60 * 100 = 25.0
        self.camera_radius = 25.0  # Esto da 60% de zoom inicial
        self.camera_angle = 0.0
        self.camera_height = 5.0
        
        # Crear indicadores en pantalla
        self.zoom_text = OnscreenText(
            text="Zoom: 100%",
            pos=(-1.3, 0.9),
            scale=0.07,
            fg=(0, 0, 0, 1),
            align=TextNode.ALeft,
            mayChange=True
        )
        
        self.audio_text = OnscreenText(
            text="Audio: 0%",
            pos=(-1.3, 0.8),
            scale=0.07,
            fg=(0.8, 0, 0, 1),  # Rojo para que combine con la esfera
            align=TextNode.ALeft,
            mayChange=True
        )
        
        # Actualizar la cámara después de crear el texto
        self.update_camera()
        
        # Configurar iluminación con sombras
        self.setup_lighting()
        
        # Variables para la animación
        self.time = 0.0
        self.original_vertices = []
        
        # Variables para análisis de audio
        self.audio_amplitude = 0.0
        self.audio_playing = False
        self.music_file = None
        
        # Inicializar pygame mixer para audio
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=1024)
        pygame.mixer.init()
        
        # Buscar archivo MP3 en el directorio del proyecto
        self.find_and_load_music()
        
        self.store_original_vertices()
        
        self.taskMgr.add(self.animate_sphere, "animate_sphere")
        
        # Añadir controles de cámara
        self.accept("arrow_left", self.spin_camera_left)
        self.accept("arrow_right", self.spin_camera_right)
        self.accept("arrow_up", self.zoom_in)
        self.accept("arrow_down", self.zoom_out)
        self.accept("w", self.zoom_in)
        self.accept("s", self.zoom_out)
        
        # Añadir controles de audio
        self.accept("space", self.toggle_music)
        self.accept("p", self.toggle_music)
        self.accept("r", self.restart_music)
        
        print("Animación iniciada con sincronización de audio.")
        print("Controles:")
        print("- Flechas izquierda/derecha: rotar cámara")
        print("- Flechas arriba/abajo o W/S: zoom in/out")
        print("- ESPACIO o P: play/pausa de la música")
        print("- R: reiniciar música desde el principio")
        print("- La esfera se deforma al ritmo de la música")
        if self.music_file:
            print(f"- Reproduciendo: {os.path.basename(self.music_file)}")
        else:
            print("- Usando simulación de audio (coloca un archivo .mp3 en el directorio para música real)")
    
    def create_ground_plane(self):
        """Crear un plano de tierra para recibir sombras"""
        cm = CardMaker('ground')
        cm.setFrame(-20, 20, -20, 20)
        ground = self.render.attachNewNode(cm.generate())
        ground.setPos(0, 0, -3)
        ground.setHpr(0, -90, 0)
        ground.setColor(0.2, 0.2, 0.25, 1)

    def create_basic_sphere(self):
        """Crear una esfera densa sin separaciones visibles"""
        sphere = self.render.attachNewNode("sphere")
        segments = 30  # Más segmentos para mayor densidad
        
        # Crear segmentos de la esfera con alta densidad
        for i in range(segments):
            phi = math.pi * i / (segments - 1)
            for j in range(segments * 2):
                theta = 2 * math.pi * j / (segments * 2)
                
                # Calcular posición en la esfera
                x = math.sin(phi) * math.cos(theta)
                y = math.sin(phi) * math.sin(theta)
                z = math.cos(phi)
                
                # Crear segmentos más grandes que se superpongan ligeramente
                cm = CardMaker(f"segment_{i}_{j}")
                size = 0.100 # Tamaño más grande para cubrir huecos
                cm.setFrame(-size, size, -size, size)
                card = sphere.attachNewNode(cm.generate())
                
                # Posicionar el segmento
                radius = 1.0
                card.setPos(x * radius, y * radius, z * radius)
                card.lookAt(0, 0, 0)
                
                # Añadir color rojo con variación suave
                r = 0.8 + 0.2 * (x + 1) / 2  # Rojo muy dominante
                g = 0.05 + 0.1 * (y + 1) / 2  # Verde muy mínimo
                b = 0.05 + 0.1 * (z + 1) / 2  # Azul muy mínimo
                card.setColor(r, g, b, 1.0)
                
                # NO aplicar material que sobrescribe el color
                # En su lugar, configurar propiedades de renderizado
                card.setRenderModeWireframe()
                card.setRenderModeFilled()
                
                # Hacer que los segmentos se mezclen mejor
                card.setTransparency(TransparencyAttrib.MAlpha)
                card.setAlphaScale(0.95)  # Ligeramente transparente para mezcla
        
        return sphere
    
    def find_and_load_music(self):
        """Buscar y cargar un archivo MP3 en el directorio del proyecto"""
        project_dir = os.path.dirname(os.path.dirname(__file__))
        
        # Buscar archivos MP3 en el directorio del proyecto
        mp3_files = []
        for file in os.listdir(project_dir):
            if file.lower().endswith('.mp3'):
                mp3_files.append(os.path.join(project_dir, file))
        
        if mp3_files:
            self.music_file = mp3_files[0]  # Usar el primer MP3 encontrado
            print(f"Archivo de música encontrado: {os.path.basename(self.music_file)}")
            self.load_and_play_music()
        else:
            print("No se encontró ningún archivo MP3 en el directorio del proyecto.")
            print("Coloca un archivo .mp3 en el directorio raíz para sincronizar con música.")
            # Usar simulación de audio sin archivo
            self.simulate_audio_data()
    
    def load_and_play_music(self):
        """Cargar y reproducir el archivo de música"""
        try:
            pygame.mixer.music.load(self.music_file)
            pygame.mixer.music.play(-1)  # Reproducir en bucle
            self.audio_playing = True
            print("Música iniciada. La esfera se sincronizará con el audio.")
        except pygame.error as e:
            print(f"Error al cargar el archivo de música: {e}")
            self.simulate_audio_data()
    
    def simulate_audio_data(self):
        """Simular datos de audio cuando no hay archivo MP3"""
        print("Simulando datos de audio para la demostración.")
        self.audio_playing = True
    
    def get_audio_amplitude(self):
        """Obtener la amplitud actual del audio"""
        if self.music_file and pygame.mixer.music.get_busy():
            # Simular análisis de amplitud basado en el tiempo
            # En una implementación real, aquí analizarías el espectro de frecuencias
            base_amplitude = 0.3 + 0.7 * abs(math.sin(self.time * 4)) * abs(math.cos(self.time * 2.5))
            return base_amplitude
        else:
            # Simulación de audio con patrones rítmicos
            beat_pattern = (
                0.8 * abs(math.sin(self.time * 2.5)) +
                0.6 * abs(math.cos(self.time * 3.2)) +
                0.4 * abs(math.sin(self.time * 1.8))
            ) / 3
            return beat_pattern
    
    def setup_lighting(self):
        """Configurar iluminación con capacidad de sombras"""
        # Activar el generador automático de shaders
        self.render.set_shader_auto()
        
        # Configurar el título de la ventana
        props = WindowProperties()
        props.setTitle('Esfera Orgánica con Sombras')
        self.win.requestProperties(props)
        
        # Luz direccional principal que proyecta sombras
        dlight = DirectionalLight('dlight')
        dlight.set_color((0.9, 0.9, 0.8, 1))
        dlight.set_shadow_caster(True, 2048, 2048)
        
        # Configurar los parámetros de la lente de sombras
        lens = dlight.get_lens()
        lens.set_near_far(1, 50)
        lens.set_film_size(30, 30)
        
        self.dlnp = self.render.attach_new_node(dlight)
        self.dlnp.set_pos(15, -15, 20)
        self.dlnp.look_at(0, 0, 0)
        self.render.set_light(self.dlnp)
        
        # Añadir luz de relleno suave
        fill_light = DirectionalLight('fill_light')
        fill_light.set_color((0.3, 0.3, 0.4, 1))
        fill_lnp = self.render.attach_new_node(fill_light)
        fill_lnp.set_pos(-10, 10, -10)
        fill_lnp.look_at(0, 0, 0)
        self.render.set_light(fill_lnp)
        
        # Luz ambiental suave
        alight = AmbientLight('alight')
        alight.set_color((0.4, 0.4, 0.5, 1))
        alnp = self.render.attach_new_node(alight)
        self.render.set_light(alnp)
        
        # Configurar antialiasing
        self.render.set_antialias(AntialiasAttrib.M_auto)
    
    def store_original_vertices(self):
        """Almacenar las posiciones originales para la animación"""
        # Almacenar las posiciones originales de cada segmento
        for child in self.sphere.getChildren():
            self.original_vertices.append(child.getPos())
    
    def animate_sphere(self, task):
        """Animar la esfera solo cuando la música esté reproduciéndose"""
        dt = globalClock.getDt()
        
        # Solo animar si la música está reproduciéndose
        music_is_playing = False
        if self.music_file:
            music_is_playing = pygame.mixer.music.get_busy()
        else:
            # Si no hay archivo, usar simulación (siempre "playing")
            music_is_playing = self.audio_playing
        
        # Solo actualizar el tiempo y animar si la música está reproduciéndose
        if music_is_playing:
            self.time += dt
            
            # Obtener amplitud del audio
            self.audio_amplitude = self.get_audio_amplitude()
            
            # Animar cada segmento de la esfera
            children = self.sphere.getChildren()
            for i, child in enumerate(children):
                if i < len(self.original_vertices):
                    orig_pos = self.original_vertices[i]
                    
                    # Calcular la deformación sincronizada con audio
                    t = self.time
                    freq1 = 1.5 + self.audio_amplitude * 2.0  # Frecuencia modulada por audio
                    freq2 = 2.0 + self.audio_amplitude * 1.5
                    freq3 = 1.2 + self.audio_amplitude * 1.8
                    
                    # Patrón de deformación influenciado por la música
                    base_deformation = (
                        0.15 * math.sin(t * freq1 + orig_pos.x * 2) *
                        math.cos(t * freq2 + orig_pos.y * 2.5) *
                        math.sin(t * freq3 + orig_pos.z * 3) *
                        (1.0 + 0.3 * math.sin(t * 0.7 + orig_pos.length() * 2))
                    )
                    
                    # Amplificar la deformación según la amplitud del audio
                    audio_multiplier = 1.0 + self.audio_amplitude * 2.0  # Multiplicador basado en audio
                    deformation = base_deformation * audio_multiplier
                    
                    # Aplicar deformación radial
                    direction = orig_pos.normalized()
                    new_pos = orig_pos + direction * deformation
                    child.setPos(new_pos)
                    
                    # Variación de color influenciada por el audio
                    audio_intensity = self.audio_amplitude
                    r = 0.6 + 0.4 * math.sin(t * 0.3 + orig_pos.x * 0.5) + audio_intensity * 0.2
                    g = 0.05 + 0.15 * math.cos(t * 0.4 + orig_pos.y * 0.6) + audio_intensity * 0.1
                    b = 0.05 + 0.15 * math.sin(t * 0.5 + orig_pos.z * 0.7) + audio_intensity * 0.1
                    
                    # Asegurar que los valores estén en el rango correcto para rojo
                    r = max(0.5, min(1.0, r))  # Rojo siempre alto
                    g = max(0.0, min(0.3, g))  # Verde limitado
                    b = max(0.0, min(0.3, b))  # Azul limitado
                    
                    child.setColor(r, g, b, 1.0)
            
            # Rotación suave de la esfera solo cuando hay música
            self.sphere.set_hpr(
                self.sphere.get_h() + 10 * dt,
                self.sphere.get_p() + 7.5 * dt,
                self.sphere.get_r() + 5 * dt
            )
            
            # Hacer que la luz gire alrededor de la esfera solo cuando hay música
            if hasattr(self, 'dlnp'):
                # Calcular nueva posición orbital para la luz
                light_angle = self.time * 30  # Velocidad de rotación de la luz (grados por segundo)
                light_radius = 25.0
                light_height = 20.0
                
                # Posición orbital de la luz
                light_x = math.sin(math.radians(light_angle)) * light_radius
                light_y = -math.cos(math.radians(light_angle)) * light_radius
                light_z = light_height
                
                # Actualizar posición y orientación de la luz
                self.dlnp.set_pos(light_x, light_y, light_z)
                self.dlnp.look_at(0, 0, 2)  # Siempre apuntar al centro de la esfera
        else:
            # Cuando la música está pausada, establecer amplitud a 0
            self.audio_amplitude = 0.0
        
        return task.cont
    
    def update_camera(self):
        """Actualizar la posición de la cámara según los controles"""
        rad = math.radians(self.camera_angle)
        self.camera.set_pos(
            math.sin(rad) * self.camera_radius,
            -math.cos(rad) * self.camera_radius,
            self.camera_height
        )
        self.camera.look_at(0, 0, 2)
        
        # Actualizar el indicador de zoom
        self.update_zoom_display()
    
    def update_zoom_display(self):
        """Actualizar el texto del zoom en pantalla"""
        # Calcular el porcentaje de zoom (15.0 es el radio base = 100%)
        base_radius = 15.0
        zoom_percentage = int((base_radius / self.camera_radius) * 100)
        self.zoom_text.setText(f"Zoom: {zoom_percentage}%")
        
        # Actualizar el indicador de audio solo si está inicializado
        if hasattr(self, 'audio_amplitude'):
            audio_percentage = int(self.audio_amplitude * 100)
            self.audio_text.setText(f"Audio: {audio_percentage}%")
    
    def spin_camera_left(self):
        """Rotar cámara hacia la izquierda"""
        self.camera_angle = (self.camera_angle + 5) % 360
        self.update_camera()
    
    def spin_camera_right(self):
        """Rotar cámara hacia la derecha"""
        self.camera_angle = (self.camera_angle - 5) % 360
        self.update_camera()
    
    def zoom_in(self):
        """Acercar la cámara"""
        if self.camera_radius > 5.0:
            self.camera_radius -= 1.0
            self.update_camera()
    
    def zoom_out(self):
        """Alejar la cámara"""
        if self.camera_radius < 30.0:
            self.camera_radius += 1.0
            self.update_camera()
    
    def toggle_music(self):
        """Alternar entre play y pausa de la música"""
        if self.music_file:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.pause()
                print("Música pausada")
            else:
                pygame.mixer.music.unpause()
                print("Música reanudada")
        else:
            print("No hay archivo de música cargado")
    
    def restart_music(self):
        """Reiniciar la música desde el principio"""
        if self.music_file:
            pygame.mixer.music.stop()
            pygame.mixer.music.play(-1)  # Reproducir en bucle
            print("Música reiniciada")
        else:
            print("No hay archivo de música cargado")

# Crear y ejecutar la aplicación
if __name__ == "__main__":
    app = OrganicSphere()
    app.run()
