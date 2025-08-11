from direct.showbase.ShowBase import ShowBase
from panda3d.core import *
from direct.task import Task
from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import *
import math
import random
import pygame
import threading
import os

class OrganicSphere(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        
        # Configurar la ventana
        self.setBackgroundColor(0.1, 0.1, 0.1)
        
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
        
        # Variables para análisis de audio (inicializar antes de crear GUI)
        self.audio_amplitude = 0.0
        self.audio_playing = False
        self.music_file = None
        self.volume = 0.7  # Volumen inicial (70%)
        self.deformation_factor = 1.0  # Factor de amplitud de deformación (100%)
        
        # Crear indicadores en pantalla (esquina inferior izquierda)
        self.zoom_text = OnscreenText(
            text="Zoom: 100%",
            pos=(-1.35, -0.65),
            scale=0.05,  # Reducido de 0.07 a 0.05
            fg=(0, 0, 0, 1),
            align=TextNode.ALeft,
            mayChange=True
        )
        

        
        # Crear slider de volumen (mejor posicionado)
        self.volume_text = OnscreenText(
            text="Volumen: 70%",
            pos=(-1.35, -0.82),
            scale=0.045,  # Reducido de 0.06 a 0.045
            fg=(0.7, 0.7, 0.7, 1),
            align=TextNode.ALeft,
            mayChange=True
        )
        
        self.volume_slider = DirectSlider(
            range=(0, 1),
            value=self.volume,
            pageSize=0.1,
            pos=(-0.7, 0, -0.82),  # Movido más a la derecha
            scale=0.25,  # Reducido de 0.3 a 0.25
            command=self.update_volume,
            thumb_relief=DGG.RAISED,
            thumb_frameSize=(-0.04, 0.04, -0.06, 0.06),  # Thumb más pequeño
            thumb_frameColor=(0.8, 0.2, 0.2, 1),  # Rojo para el thumb
            frameColor=(0.3, 0.3, 0.3, 1),  # Gris para la barra
            relief=DGG.SUNKEN
        )
        
        # Crear slider de amplitud de deformación (mejor posicionado)
        self.deformation_text = OnscreenText(
            text="Deformación: 100%",
            pos=(-1.35, -0.92),
            scale=0.045,  # Reducido de 0.06 a 0.045
            fg=(0.7, 0.7, 0.7, 1),
            align=TextNode.ALeft,
            mayChange=True
        )
        
        self.deformation_slider = DirectSlider(
            range=(0, 2),  # Rango de 0% a 200% de deformación
            value=self.deformation_factor,
            pageSize=0.1,
            pos=(-0.7, 0, -0.92),  # Movido más a la derecha
            scale=0.25,  # Reducido de 0.3 a 0.25
            command=self.update_deformation,
            thumb_relief=DGG.RAISED,
            thumb_frameSize=(-0.04, 0.04, -0.06, 0.06),  # Thumb más pequeño
            thumb_frameColor=(0.2, 0.8, 0.2, 1),  # Verde para el thumb
            frameColor=(0.3, 0.3, 0.3, 1),  # Gris para la barra
            relief=DGG.SUNKEN
        )
        
        # Actualizar la cámara después de crear el texto
        self.update_camera()
        
        # Configurar iluminación con sombras
        self.setup_lighting()
        
        # Variables para la animación
        self.time = 0.0
        self.original_vertices = []
        
        # Variables para satélites
        self.satellites = []
        self.satellite_orbits = []
        self.num_satellites = 10
        
        # Inicializar pygame mixer para audio
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=1024)
        pygame.mixer.init()
        
        # Buscar archivo MP3 en el directorio del proyecto
        self.find_and_load_music()
        
        # Crear satélites orbitales
        self.create_satellites()
        
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
            pygame.mixer.music.set_volume(self.volume)  # Configurar volumen inicial
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
        props.setTitle('Visualización de Audio - Panda3D')
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
    
    def create_satellites(self):
        """Crear satélites esféricos que orbiten alrededor de la esfera principal"""
        for i in range(self.num_satellites):
            # Crear una esfera pequeña para cada satélite
            satellite_sphere = self.render.attachNewNode("satellite_sphere")
            
            # Crear segmentos para la esfera satélite (máxima densidad posible)
            segments_per_satellite = 16  # Máxima densidad de segmentos
            segment_size = 0.080  # Tamaño ultra pequeño para densidad extrema
            
            satellite_segments = []
            for j in range(segments_per_satellite):
                for k in range(segments_per_satellite):
                    # Crear cada segmento de la esfera satélite
                    segment_maker = CardMaker(f"satellite_segment_{i}_{j}_{k}")
                    segment_maker.setFrame(-segment_size, segment_size, -segment_size, segment_size)
                    segment_node = satellite_sphere.attachNewNode(segment_maker.generate())
                    
                    # Posición esférica para el segmento
                    phi = (j / segments_per_satellite) * 2 * math.pi
                    theta = (k / segments_per_satellite) * math.pi
                    
                    radius = 0.4  # Radio muy pequeño para la esfera satélite
                    x = radius * math.sin(theta) * math.cos(phi)
                    y = radius * math.sin(theta) * math.sin(phi)
                    z = radius * math.cos(theta)
                    
                    segment_node.setPos(x, y, z)
                    segment_node.lookAt(0, 0, 0)  # Orientar hacia el centro
                    
                    satellite_segments.append(segment_node)
            
            # Color rojo como la esfera principal, con ligeras variaciones
            red_variations = [
                (0.9, 0.1, 0.1, 0.9),  # Rojo intenso
                (0.8, 0.15, 0.05, 0.9),  # Rojo con toque naranja
                (0.85, 0.05, 0.15, 0.9),  # Rojo con toque magenta
                (0.95, 0.08, 0.08, 0.9),  # Rojo muy puro
            ]
            satellite_sphere.setColor(*red_variations[i % len(red_variations)])
            satellite_sphere.setTransparency(TransparencyAttrib.MAlpha)
            
            # Configurar movimiento aleatorio inicial
            import random
            orbit_info = {
                'x': random.uniform(-10, 10),  # Posición inicial X aleatoria
                'y': random.uniform(-10, 10),  # Posición inicial Y aleatoria
                'z': random.uniform(-2, 6),    # Posición inicial Z aleatoria
                'vel_x': random.uniform(-2, 2),  # Velocidad X aleatoria
                'vel_y': random.uniform(-2, 2),  # Velocidad Y aleatoria
                'vel_z': random.uniform(-1, 1),  # Velocidad Z aleatoria
                'bounce_factor': 0.8,  # Factor de rebote al chocar
                'collision_distance': 3.5,  # Distancia para colisión con esfera principal
                'collision_time': 0.0,  # Tiempo desde última colisión
                'random_factor': random.uniform(0.5, 1.5),  # Factor de aleatoriedad individual
                'segments': satellite_segments,  # Almacenar segmentos para deformación
                'original_positions': []  # Posiciones originales de los segmentos
            }
            
            # Almacenar posiciones originales de los segmentos del satélite
            for segment in satellite_segments:
                orbit_info['original_positions'].append(segment.getPos())
            
            self.satellites.append(satellite_sphere)
            self.satellite_orbits.append(orbit_info)
    
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
                    
                    # Calcular la deformación extremadamente suave
                    t = self.time
                    # Frecuencias muy bajas para movimientos ultra suaves
                    freq1 = 0.4 + self.audio_amplitude * 0.5  # Frecuencia muy reducida
                    freq2 = 0.5 + self.audio_amplitude * 0.4
                    freq3 = 0.3 + self.audio_amplitude * 0.6
                    
                    # Patrón de deformación ultra suave y orgánico
                    wave1 = math.sin(t * freq1 + orig_pos.x * 1.0)
                    wave2 = math.cos(t * freq2 + orig_pos.y * 1.2)
                    wave3 = math.sin(t * freq3 + orig_pos.z * 1.4)
                    wave4 = math.sin(t * 0.2 + orig_pos.length() * 1.0)
                    
                    # Combinar ondas de manera ultra suave
                    base_deformation = (
                        0.05 * wave1 * wave2 * wave3 * (1.0 + 0.15 * wave4)
                    )
                    
                    # Amplificar la deformación de manera muy gradual
                    audio_multiplier = 1.0 + self.audio_amplitude * 0.8  # Multiplicador ultra suave
                    deformation = base_deformation * audio_multiplier * self.deformation_factor
                    
                    # Aplicar deformación radial
                    direction = orig_pos.normalized()
                    new_pos = orig_pos + direction * deformation
                    child.setPos(new_pos)
                    
                    # Variación de color extremadamente suave
                    audio_intensity = self.audio_amplitude
                    # Cambios de color ultra lentos y sutiles
                    r = 0.75 + 0.1 * math.sin(t * 0.08 + orig_pos.x * 0.2) + audio_intensity * 0.05
                    g = 0.06 + 0.04 * math.cos(t * 0.09 + orig_pos.y * 0.25) + audio_intensity * 0.02
                    b = 0.06 + 0.04 * math.sin(t * 0.07 + orig_pos.z * 0.22) + audio_intensity * 0.02
                    
                    # Asegurar que los valores estén en el rango correcto para rojo
                    r = max(0.7, min(0.9, r))  # Rojo más estable
                    g = max(0.0, min(0.12, g))  # Verde extremadamente limitado
                    b = max(0.0, min(0.12, b))  # Azul extremadamente limitado
                    
                    child.setColor(r, g, b, 1.0)
            
            # Rotación extremadamente suave de la esfera solo cuando hay música
            self.sphere.set_hpr(
                self.sphere.get_h() + 2 * dt,   # Rotación ultra lenta
                self.sphere.get_p() + 1.5 * dt, # Rotación ultra lenta
                self.sphere.get_r() + 1 * dt    # Rotación ultra lenta
            )
            
            # Hacer que la luz gire alrededor de la esfera solo cuando hay música (ultra suave)
            if hasattr(self, 'dlnp'):
                # Calcular nueva posición orbital para la luz (ultra lenta)
                light_angle = self.time * 8  # Velocidad de rotación ultra lenta (grados por segundo)
                light_radius = 25.0
                light_height = 20.0
                
                # Posición orbital de la luz
                light_x = math.sin(math.radians(light_angle)) * light_radius
                light_y = -math.cos(math.radians(light_angle)) * light_radius
                light_z = light_height
                
                # Actualizar posición y orientación de la luz
                self.dlnp.set_pos(light_x, light_y, light_z)
                self.dlnp.look_at(0, 0, 2)  # Siempre apuntar al centro de la esfera
            
            # Animar satélites orbitales
            self.animate_satellites(dt)
        else:
            # Cuando la música está pausada, establecer amplitud a 0
            self.audio_amplitude = 0.0
        
        return task.cont
    
    def animate_satellites(self, dt):
        """Animar satélites pequeños con movimiento aleatorio y colisiones directas"""
        import random
        t = self.time
        
        for i, (satellite, orbit) in enumerate(zip(self.satellites, self.satellite_orbits)):
            # Actualizar posición con movimiento aleatorio
            orbit['x'] += orbit['vel_x'] * dt * orbit['random_factor']
            orbit['y'] += orbit['vel_y'] * dt * orbit['random_factor']
            orbit['z'] += orbit['vel_z'] * dt * orbit['random_factor']
            
            # Añadir componente aleatorio influenciado por la música
            random_intensity = self.audio_amplitude * 2.0
            orbit['vel_x'] += random.uniform(-random_intensity, random_intensity) * dt
            orbit['vel_y'] += random.uniform(-random_intensity, random_intensity) * dt
            orbit['vel_z'] += random.uniform(-random_intensity * 0.5, random_intensity * 0.5) * dt
            
            # Limitar velocidades para evitar movimiento demasiado rápido
            max_vel = 3.0
            orbit['vel_x'] = max(-max_vel, min(max_vel, orbit['vel_x']))
            orbit['vel_y'] = max(-max_vel, min(max_vel, orbit['vel_y']))
            orbit['vel_z'] = max(-max_vel * 0.5, min(max_vel * 0.5, orbit['vel_z']))
            
            # Verificar colisión con la esfera principal (centro en 0,0,2)
            distance_to_center = math.sqrt(orbit['x']**2 + orbit['y']**2 + (orbit['z']-2)**2)
            
            if distance_to_center < orbit['collision_distance']:
                # Colisión directa - rebotar
                orbit['collision_time'] = t
                
                # Calcular dirección de rebote
                if distance_to_center > 0:
                    normal_x = orbit['x'] / distance_to_center
                    normal_y = orbit['y'] / distance_to_center
                    normal_z = (orbit['z'] - 2) / distance_to_center
                else:
                    # Si está exactamente en el centro, rebotar en dirección aleatoria
                    normal_x = random.uniform(-1, 1)
                    normal_y = random.uniform(-1, 1)
                    normal_z = random.uniform(-1, 1)
                
                # Reflejar velocidad (rebote)
                dot_product = (orbit['vel_x'] * normal_x + 
                              orbit['vel_y'] * normal_y + 
                              orbit['vel_z'] * normal_z)
                
                orbit['vel_x'] -= 2 * dot_product * normal_x * orbit['bounce_factor']
                orbit['vel_y'] -= 2 * dot_product * normal_y * orbit['bounce_factor']
                orbit['vel_z'] -= 2 * dot_product * normal_z * orbit['bounce_factor']
                
                # Empujar fuera de la esfera para evitar que se quede atrapado
                push_distance = orbit['collision_distance'] + 0.5
                orbit['x'] = normal_x * push_distance
                orbit['y'] = normal_y * push_distance
                orbit['z'] = 2 + normal_z * push_distance
                
                # Añadir velocidad extra por la música durante la colisión
                collision_boost = self.audio_amplitude * 2.0
                orbit['vel_x'] += normal_x * collision_boost
                orbit['vel_y'] += normal_y * collision_boost
                orbit['vel_z'] += normal_z * collision_boost * 0.5
            
            # Mantener dentro de los límites del viewport
            max_distance = 15
            if abs(orbit['x']) > max_distance:
                orbit['x'] = max_distance * (1 if orbit['x'] > 0 else -1)
                orbit['vel_x'] *= -orbit['bounce_factor']
            if abs(orbit['y']) > max_distance:
                orbit['y'] = max_distance * (1 if orbit['y'] > 0 else -1)
                orbit['vel_y'] *= -orbit['bounce_factor']
            if orbit['z'] < -2:
                orbit['z'] = -2
                orbit['vel_z'] *= -orbit['bounce_factor']
            elif orbit['z'] > 8:
                orbit['z'] = 8
                orbit['vel_z'] *= -orbit['bounce_factor']
            
            # Deformar los segmentos de la esfera satélite al ritmo de la música
            if 'segments' in orbit and 'original_positions' in orbit:
                for j, (segment, orig_pos) in enumerate(zip(orbit['segments'], orbit['original_positions'])):
                    # Deformación más pequeña y rápida para satélites pequeños
                    sat_freq1 = 1.2 + i * 0.3 + self.audio_amplitude * 0.8
                    sat_freq2 = 1.5 + i * 0.2 + self.audio_amplitude * 0.6
                    sat_freq3 = 0.9 + i * 0.4 + self.audio_amplitude * 1.0
                    
                    # Ondas de deformación más intensas para satélites pequeños
                    wave1 = math.sin(t * sat_freq1 + orig_pos.x * 3.0 + i)
                    wave2 = math.cos(t * sat_freq2 + orig_pos.y * 3.5 + i)
                    wave3 = math.sin(t * sat_freq3 + orig_pos.z * 2.8 + i)
                    
                    # Deformación pequeña pero visible
                    base_deformation = 0.02 * wave1 * wave2 * wave3
                    
                    # Amplificar con audio y factor de deformación
                    sat_audio_multiplier = 1.0 + self.audio_amplitude * 0.8
                    deformation = base_deformation * sat_audio_multiplier * self.deformation_factor
                    
                    # Aplicar deformación radial
                    direction = orig_pos.normalized()
                    new_pos = orig_pos + direction * deformation
                    segment.setPos(new_pos)
                    
                    # Colores base rojos como la esfera principal
                    base_colors = [
                        (0.9, 0.1, 0.1),  # Rojo intenso
                        (0.8, 0.15, 0.05),  # Rojo con toque naranja
                        (0.85, 0.05, 0.15),  # Rojo con toque magenta
                        (0.95, 0.08, 0.08),  # Rojo muy puro
                    ]
                    base_color = base_colors[i % len(base_colors)]
                    
                    # Variación de color con la música y colisiones
                    collision_intensity = max(0, 1.0 - (t - orbit['collision_time']) * 4)
                    color_variation = 0.1 * math.sin(t * 0.2 + j * 0.2) * self.audio_amplitude
                    bright_factor = 1.0 + collision_intensity * 0.5
                    
                    r = max(0.1, min(1.0, (base_color[0] + color_variation) * bright_factor))
                    g = max(0.1, min(1.0, (base_color[1] + color_variation) * bright_factor))
                    b = max(0.1, min(1.0, (base_color[2] + color_variation) * bright_factor))
                    
                    segment.setColor(r, g, b, 0.95)
            
            # Aplicar posición final
            satellite.setPos(orbit['x'], orbit['y'], orbit['z'])
            
            # Rotación rápida y aleatoria
            rotation_speed = 50 * (1 + self.audio_amplitude)
            satellite.setHpr(
                satellite.getH() + rotation_speed * dt * (1 + i * 0.5),
                satellite.getP() + rotation_speed * dt * (1 + i * 0.3),
                satellite.getR() + rotation_speed * dt * (1 + i * 0.7)
            )
    
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
    
    def spin_camera_left(self):
        """Rotar cámara hacia la izquierda (más suave)"""
        self.camera_angle = (self.camera_angle + 2) % 360
        self.update_camera()
    
    def spin_camera_right(self):
        """Rotar cámara hacia la derecha (más suave)"""
        self.camera_angle = (self.camera_angle - 2) % 360
        self.update_camera()
    
    def zoom_in(self):
        """Acercar la cámara"""
        if self.camera_radius > 5.0:
            self.camera_radius -= 1.0
            self.update_camera()
    
    def zoom_out(self):
        """Alejar la cámara"""
        if self.camera_radius < 50.0:
            self.camera_radius += 1.0
            self.update_camera()
    
    def update_volume(self):
        """Actualizar el volumen de la música cuando se mueve el slider"""
        self.volume = self.volume_slider['value']
        if self.music_file and pygame.mixer.get_init():
            pygame.mixer.music.set_volume(self.volume)
        
        # Actualizar el texto del volumen en el slider
        volume_percentage = int(self.volume * 100)
        # Opcional: mostrar el porcentaje en el texto del volumen
        self.volume_text.setText(f"Volumen: {volume_percentage}%")
    
    def update_deformation(self):
        """Actualizar el factor de deformación cuando se mueve el slider"""
        self.deformation_factor = self.deformation_slider['value']
        
        # Actualizar el texto del factor de deformación
        deformation_percentage = int(self.deformation_factor * 100)
        self.deformation_text.setText(f"Deformación: {deformation_percentage}%")
    
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
