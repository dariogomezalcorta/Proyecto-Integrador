import pandas as pd
import numpy as np
from transformers import AutoTokenizer, AutoModel
import torch
from sqlalchemy import create_engine, text
from sklearn.metrics.pairwise import cosine_similarity
from fuzzywuzzy import fuzz
import os
import atexit
import json
import re
from Levenshtein import distance as levenshtein_distance
import time
import sys

print(f"Directorio actual: {os.getcwd()}")

# Opcionalidad para cargar desde archivos o base de datos
USE_DATABASE = False  # Cambia esto según tus necesidades

import sys

# Redirigir todas las salidas estándar a log_resultados.txt
class Logger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log_file = open(filename, "a", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)  # Escribe en la consola
        self.log_file.write(message)  # Escribe en el archivo de log

    def flush(self):
        self.terminal.flush()
        self.log_file.flush()

# Redirigir la salida estándar
sys.stdout = Logger("log_resultados.txt")

def medir_tiempo(func):
    def wrapper(*args, **kwargs):
        inicio = time.time()
        resultado = func(*args, **kwargs)
        fin = time.time()
        tiempo_ejecucion = fin - inicio

        # Solo registra tiempos en el archivo, sin imprimir en pantalla
        if tiempo_ejecucion > 0.001:
            nombre_funcion = func.__name__
            with open("log_resultados.txt", "a") as log_file:
                log_file.write(f"Tiempo de ejecución de {nombre_funcion}: {tiempo_ejecucion:.5f} segundos\n")
        
        return resultado
    return wrapper

# Ruta para almacenar el archivo de caché
CACHE_FILE_PATH = "ingredientes_cache.json"

def cargar_cache_ingredientes():
    try:
        if os.path.exists(CACHE_FILE_PATH):
            with open(CACHE_FILE_PATH, 'r', encoding='utf-8') as file:
                cache = json.load(file)
                print("Caché cargado correctamente:", cache)
                return cache
    except json.JSONDecodeError:
        print("Error al cargar el caché de ingredientes: archivo JSON corrupto.")
    return {}

def guardar_cache_ingredientes():
    try:
        print("Guardando el caché de ingredientes...")  # Debugging
        if ingredientes_cache:
            with open(CACHE_FILE_PATH, 'w', encoding='utf-8') as file:
                json.dump(ingredientes_cache, file, ensure_ascii=False, indent=4)
            print("Caché guardado correctamente:", ingredientes_cache)
        else:
            print("Advertencia: No hay datos en el caché para guardar.")
    except Exception as e:
        print(f"Error al guardar el caché de ingredientes: {e}")


# Función que se ejecuta después de cada actualización de caché
def actualizar_cache_ingrediente(ingrediente, producto_barato, precio_min):
    """Actualiza el caché de un ingrediente específico y guarda el archivo de caché."""
    ingredientes_cache[ingrediente] = (producto_barato, precio_min)
    print(f"Actualización de caché: {ingrediente} -> Producto: {producto_barato['nombre']}, Precio: {precio_min}")  # Debugging
    guardar_cache_ingredientes()

ingredientes_cache = cargar_cache_ingredientes()
atexit.register(guardar_cache_ingredientes)

# Configuración de Transformers
tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/paraphrase-MiniLM-L6-v2")
model = AutoModel.from_pretrained("sentence-transformers/paraphrase-MiniLM-L6-v2")

# Listas combinadas de términos irrelevantes y de presentación
palabras_irrelevantes = set([
    "INGREDIENTES", "Extra:", "Cubierta:", "Masa:", "Relleno:", "Opción:", "Opcionales:", "Salsa:", "Caldo", "Aderezo","Hummus", "Ligue", "Preparación", "Pasos", "Método", "Instrucciones", "Procedimiento", "Porciones", "Rinde","Pizca", "Pellizco", "Manojo", "Paquete", "Sobre", "Con", "Y", "O", "Cantidad", "Partes", "Sugerencia","Cuchara", "Cucharadita", "Pizca", "Porción", "Cocción", "Tiempo", "Freír", "Hornear", "Hervir", "Revolver",
    "Mezclar", "Batir", "Enfriar", "Reposar", "Ligeramente", "Fresco", "Crudo", "Picada", "Cortada", "En","Tiras", "Cubos", "Fileteada", "Molido", "Rallado", "Tostado", "Tamaño", "Grande", "Mediana", "Pequeña","A gusto", "Según preferencia", "Opcional", "Puede acompañar", "Decorar con", "A elección", "Optativo", "C/N","Al gusto", "En rodajas", "Batidas a nieve", "Rinde", "Entre", "Para servir:", "Para acompañar:", "Para la masa:",
    "Para el relleno:", "Paso", "Nivel", "Punto", "Pieza", "Unidades", "Armado:", "Marinada:", "Frito:", "Guarnición:", "Canasta:", "Aderezo:", "Emplatado:", "Extra:", "Para el pan:", "Ensalada:", "Para las papas picantes ??", "-", ":", "?", ".", "1⃣", "puñado", "taza", "atados", "1 unid",

    # Unidades adicionales
    "cc", "cm³", "ml", "mg", "chorrito", "toque", "medida", "gajo", "cáscara", "cucharón", "rodaja", "bol pequeño","botella", "cartón", "saco", "ramita", "mazo", "puñado", "porción", "rebanada", "diente", "ramita", "litro","litros", "vaso", "cuenco", "bocado", "bol", "tazón", "cazuela", "tarro", "sobre", "bolsita", "pote", "bol pequeño","rodaja", "filete", "fetas",

    # Términos de presentación adicionales
    "ahumado", "caramelizado", "curado", "al vacío", "prensado", "en dados", "en tiritas", "descascarado", "en puré","en pluma", "fileteado", "al microondas", "al fuego lento", "cocción corta", "en aceite", "embebido", "infusionado","a la brasa", "dorado", "en escabeche", "frito", "pochado", "al natural", "semicrudo", "en compota", "pasado por harina", "con pan rallado", "desgrasado", "rehidratado", "a la parrilla", "en juliana", "en rodajas",
    "en cubitos", "en fetas", "en mitades", "macerado", "marinada", "escaldado", "empanado", "glaseado", "confitado","encurtido", "adobado", "crudo", "al natural", "cocido", "asado", "hervido", "pochado", "braseado", "con semillas","sin sal", "sin piel", "escurrido", "al vapor", "al horno", "en láminas", "en bastones", "en diagonal", "chorreado","en conserva", "picadísimo", "troceado", "desgranado", "triturado", "rallado", "entero", "pelado", "con piel",
    "sin espinas", "al dente", "semi-cocido", "a la plancha", "gratinado", "blanqueado", "rebozado", "apanado","empanado", "grillado", "condimentado", "salpimentado", "endulzado", "en almíbar", "en conserva", "exprimido","escurrido", "caramelizado", "condimentado", "sazonado", "troceado", "asado", "horneado", "al vapor", "a la parrilla",

    # Adjetivos adicionales
    "carnoso", "granulado", "arenoso", "tierno", "denso", "espeso", "líquido", "suave", "robusto", "frutal", "herbal","especiado", "acidulado", "graso", "ligero", "fibroso", "elástico", "sedoso", "terso", "gomoso", "picante", "balsámico", "fresco", "aromático", "dulce", "sabroso", "neutro", "cálido", "amargo", "maduro", "bajo en grasa","reposado", "dorada", "tibio", "frío", "fuerte", "intenso", "crocante", "crujiente", "cremoso", "esponjoso", 
    "jugoso", "liviano", "integral", "procesado", "natural", "casero", "integral", "compacto", "con textura", "con sabor", "pequeño", "grande", "mediano", "chico", "fuerte", "especiado", "cítrico"
])

conversiones = {
    "kg": 1000, "gramos": 1, "g": 1, "miligramos": 0.001, "mg": 0.001,"litro": 1000, "mililitros": 1, "ml": 1, "cc": 1, "cm³": 1,"cda": 15, "cdta": 5, "taza": 240, "pizca": 0.36, "manojo": 50,"unidad": 1, "huevo": 60, "paquete": 500, "lata": 400, "hoja": 1,
    "diente": 5, "botella": 1000, "frasco": 200, "pellizco": 0.18,"limon": 65, "jugo de limon": 50, "limones": 65, "naranja": 130,"jugo de naranja": 100, "papa": 150, "zanahoria": 70, "tomate": 120,"cebolla": 150, "pimiento": 120, "banana": 120, "manzana": 180,
    "pera": 160, "pepino": 200, "calabaza": 400, "berenjena": 300,"ajo": 5, "ramita": 5, "hoja de laurel": 0.2, "cabeza de ajo": 30,"chorrito": 5, "toque": 2, "gajo": 15, "cáscara": 2, "cucharón": 50,"rodaja": 30, "bol pequeño": 150, "cartón": 1000, "saco": 2000,
    "ramita": 5, "mazo": 100, "puñado": 30, "porción": 200, "rebanada": 30,"medida": 50, "gota": 0.05, "vaso": 240, "pote": 200, "bolsita": 30
}

# Ajustes en la función para generar palabras clave válidas
def limpiar_descripciones(ingrediente):
    ingrediente = ingrediente.lower()
    ingrediente = re.sub(r'\b(\d+\s*(kg|gramos|g|mililitros|ml|litro|lata|cda|cdta|taza|hoja|diente|chorrito|puñado|cc|cm³|mg|ml|cucharón))\b', '', ingrediente)

    for termino in palabras_irrelevantes:
        ingrediente = re.sub(rf'\b{re.escape(termino)}\b', '', ingrediente)

    ingrediente = re.sub(r'[\-\(\)\.,]', '', ingrediente).strip()
    ingrediente = re.sub(r'\s+', ' ', ingrediente).strip()

    return ingrediente

def validar_ingrediente(ingrediente):
    # Ingredientes con menos de 3 caracteres o solo números son irrelevantes
    return len(ingrediente) > 2 and not ingrediente.isnumeric()

# Función para limpiar y normalizar los ingredientes
def limpiar_ingredientes(ingredientes):
    ingredientes_limpios = []
    for ingrediente in ingredientes.split('\n'):
        ingrediente = re.sub(r'\b(\d+\s*(kg|gramos|g|mililitros|ml|cda|cdta))\b', '', ingrediente.lower())
        for termino in palabras_irrelevantes:
            ingrediente = re.sub(rf'\b{re.escape(termino)}\b', '', ingrediente)
        ingrediente = re.sub(r'[\-\(\)\.,]', '', ingrediente).strip()
        ingrediente = re.sub(r'\s+', ' ', ingrediente).strip()
        ingredientes_limpios.append(ingrediente)
    return '\n'.join(ingredientes_limpios)

# Función para extraer cantidad y unidad
def extraer_cantidad_unidad(ingrediente):
    match = re.search(r'(\d+)\s*(kg|gramos|g|miligramos|mg|centímetros cúbicos|cc|mililitros|ml|litro|lata|cda|cdta|taza|hoja|diente|chorrito|puñado|medida|gajo|bol|botella|cartón|saco|ramita|mazo)', ingrediente.lower())
    
    if match:
        cantidad = int(match.group(1))
        unidad = match.group(2)
        ingrediente_limpio = ingrediente[:match.start()].strip()
    else:
        # Asignación por defecto si no hay una cantidad explícita
        if any(ing in ingrediente.lower() for ing in ["sal", "pimienta", "aceite", "agua"]):
            cantidad = 1
            unidad = "cda"
        else:
            cantidad = 1
            unidad = None
        ingrediente_limpio = ingrediente.strip()
    
    return ingrediente_limpio, cantidad, unidad

# Función para obtener embeddings
def get_batch_embeddings(texts, batch_size=64):
    if isinstance(texts, str):
        texts = [texts]

    embeddings = []
    try:
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            
            # Depuración: Mostrar información del lote actual
            print(f"\nProcesando lote {i // batch_size + 1}/{-(-len(texts) // batch_size)}")
            print(f"Textos en el lote: {batch_texts}")

            # Tokenización y generación de embeddings
            inputs = tokenizer(batch_texts, return_tensors="pt", padding=True, truncation=True)
            with torch.no_grad():
                outputs = model(**inputs)
            batch_embeddings = outputs.last_hidden_state.mean(dim=1).cpu().numpy()

            # Depuración: Confirmar forma del lote actual de embeddings
            print(f"Forma de embeddings generados para este lote: {batch_embeddings.shape}")

            # Añadir embeddings del lote a la lista principal
            embeddings.extend(batch_embeddings)

    except Exception as e:
        print(f"Error durante la generación de embeddings: {e}")
        raise

    # Depuración: Confirmar que el número de embeddings generados coincide con los textos procesados
    print(f"\nNúmero total de textos procesados: {len(texts)}")
    print(f"Número total de embeddings generados: {len(embeddings)}")

    if len(embeddings) != len(texts):
        print("Advertencia: El número de embeddings generados no coincide con el número de textos procesados.")
        raise ValueError("Número inconsistente de embeddings generados.")

    # Determinar si retornar un único embedding o una lista de embeddings
    if len(embeddings) == 1:
        print(f"Retornando un único embedding con forma: {embeddings[0].shape}")
        return embeddings[0]
    else:
        print(f"Retornando array de embeddings con forma: {np.array(embeddings).shape}")
        return np.array(embeddings)

def validar_productos_df(productos_df):
    columnas_esperadas = {"nombre", "precio_min"}
    if not columnas_esperadas.issubset(productos_df.columns):
        print(f"Columnas disponibles: {productos_df.columns.tolist()}")
        raise ValueError(f"El archivo de productos no tiene las columnas requeridas: {columnas_esperadas}")

def validar_recetas_df(recetas_df):
    columnas_esperadas = {"nombre", "ingredientes"}
    if not columnas_esperadas.issubset(recetas_df.columns):
        raise ValueError(f"El archivo de recetas no tiene las columnas requeridas: {columnas_esperadas}")

# Conexión a la base de datos
def connect_db_precios():
    return create_engine('postgresql://postgres:.Pikachu12345.@localhost:5432/PreciosClaros')

def connect_db_recetas():
    return create_engine('postgresql://postgres:.Pikachu12345.@localhost:5432/Recetas_Cocineros')

def cargar_datos_productos():
    if USE_DATABASE:
        # Lógica existente para cargar desde PostgreSQL
        engine = connect_db_precios()
        query = "SELECT nombre, precio_min FROM productos LIMIT 50"
        try:
            with engine.connect() as conn:
                result = conn.execute(text(query)).mappings()
                productos = [dict(row) for row in result]
                productos_df = pd.DataFrame(productos)
        except Exception as e:
            print(f"Error al cargar datos de productos: {e}")
            productos_df = pd.DataFrame()
        finally:
            engine.dispose()
    else:
        # Leer desde archivo CSV
        try:
            productos_df = pd.read_csv("PreciosClaros.csv")
        except FileNotFoundError:
            print("Archivo PreciosClaros.csv no encontrado.")
            productos_df = pd.DataFrame()

    print(f"Productos antes de limpiar: {len(productos_df)}")
    productos_df = productos_df.drop_duplicates(subset='nombre')
    productos_df = productos_df.dropna(subset=['nombre', 'precio_min'])
    print(f"Productos tras limpiar duplicados y nulos: {len(productos_df)}")

    if not productos_df.empty:
        # Generar columna `nombre_limpio`
        try:
            productos_df['nombre_limpio'] = productos_df['nombre'].apply(limpiar_descripciones)
            # Validar contenido de `nombre_limpio`
            print("Validación de `nombre_limpio`:")
            print(productos_df['nombre_limpio'].head())
            if productos_df['nombre_limpio'].isnull().any():
                raise ValueError("Existen valores nulos en `nombre_limpio`.")
        except Exception as e:
            print(f"Error al generar o validar `nombre_limpio`: {e}")
            return pd.DataFrame()  # Retornar DataFrame vacío si falla

        # Precalcular o cargar embeddings
        productos_df = precalcular_embeddings_productos(productos_df)

        print(f"Primeros registros tras calcular embeddings: {productos_df.head()}")

    if productos_df.empty:
        print("Error: No se cargaron datos de productos. Verifica el archivo CSV.")
    else:
        print(f"Productos cargados correctamente: {len(productos_df)}")

    return productos_df

def precalcular_embeddings_productos(productos_df, embeddings_file="productos_embeddings.npy"):
    if not productos_df.empty and not os.path.exists(embeddings_file):
        print("Embeddings no encontrados. Iniciando cálculo...")

        # Depuración: Validar productos para embeddings
        print(f"Primeros productos para embeddings: {productos_df['nombre_limpio'].head()}")

        try:
            # Generar embeddings
            productos_df['embedding'] = get_batch_embeddings(productos_df['nombre_limpio'].tolist())

            # Debug: Verificar los embeddings generados
            print(f"Primeros embeddings generados: {productos_df['embedding'].head()}")
            print(f"Forma del primer embedding: {productos_df['embedding'].iloc[0].shape if len(productos_df) > 0 else 'Sin datos'}")

            # Guardar los embeddings
            print(f"Guardando embeddings en {embeddings_file}...")
            np.save(embeddings_file, productos_df['embedding'].tolist())
            print(f"Embeddings guardados correctamente en: {embeddings_file}")

            # Depuración: Confirmar que el archivo se creó
            if os.path.exists(embeddings_file):
                print(f"Archivo {embeddings_file} creado correctamente.")
            else:
                print(f"Error: No se pudo crear el archivo {embeddings_file}. Revisa permisos de escritura.")
        except Exception as e:
            print(f"Error al calcular o guardar embeddings: {e}")
            raise
    elif os.path.exists(embeddings_file):
        print("Cargando embeddings desde archivo...")
        try:
            # Cargar embeddings desde archivo
            embeddings = np.load(embeddings_file, allow_pickle=True)
            print(f"Embeddings cargados correctamente. Total: {len(embeddings)}")

            # Verificar que los embeddings cargados coincidan en número con los productos
            if len(embeddings) != len(productos_df):
                print(f"Error: Número de embeddings ({len(embeddings)}) no coincide con productos ({len(productos_df)}).")
                print("Verifica si el archivo de embeddings está actualizado o si los productos han cambiado.")
                raise ValueError("Número de embeddings inconsistente con el DataFrame de productos.")

            # Asignar cada embedding como un vector 1D
            productos_df['embedding'] = [np.array(emb) for emb in embeddings]

            # Depuración: Validar que todos los embeddings son vectores 1D
            for idx, emb in enumerate(productos_df['embedding']):
                if emb.ndim != 1:
                    print(f"Error: Embedding en la fila {idx} no es un vector 1D. Forma: {emb.shape}")
                    raise ValueError(f"Embedding inconsistente detectado en el índice {idx}.")
        except Exception as e:
            print(f"Error al cargar o procesar los embeddings: {e}")
            raise
    else:
        raise ValueError("No se encontraron embeddings precalculados ni se pudo calcular embeddings nuevos.")
    
    # Resumen final
    print(f"Total de productos: {len(productos_df)}")
    print(f"Total de embeddings procesados correctamente: {productos_df['embedding'].notnull().sum()}")

    return productos_df

# Cargar datos de recetas
def cargar_datos_recetas():
    if USE_DATABASE:
        # Lógica existente para cargar desde PostgreSQL
        engine = connect_db_recetas()
        query = "SELECT nombre, ingredientes FROM recetas LIMIT 10"
        try:
            with engine.connect() as conn:
                result = conn.execute(text(query)).mappings()
                recetas = [dict(row) for row in result]
                recetas_df = pd.DataFrame(recetas)
        except Exception as e:
            print(f"Error al cargar datos de recetas: {e}")
            recetas_df = pd.DataFrame()
        finally:
            engine.dispose()
    else:
        # Leer desde archivo JSON
        try:
            with open("recetas.json", "r", encoding="utf-8") as file:
                recetas = json.load(file)
                recetas_df = pd.DataFrame(recetas)
        except FileNotFoundError:
            print("Archivo recetas.json no encontrado.")
            recetas_df = pd.DataFrame()

    # Eliminar duplicados
    recetas_df = recetas_df.drop_duplicates(subset='nombre')
    # Eliminar filas con valores nulos
    recetas_df = recetas_df.dropna(subset=['nombre', 'ingredientes'])
    # Confirmar si hay filas tras limpieza
    print(f"Recetas después de limpieza: {len(recetas_df)}")

    if not recetas_df.empty:
        # Validar columnas del DataFrame
        validar_recetas_df(recetas_df)

        # Limpiar los ingredientes irrelevantes antes de procesarlos
        recetas_df['ingredientes'] = recetas_df['ingredientes'].apply(filtrar_no_ingredientes)

    if recetas_df.empty:
        print("Error: No se cargaron datos de recetas. Verifica el archivo JSON.")
    else:
        print(f"Recetas cargadas: {len(recetas_df)}")
        print(recetas_df.head())  # Muestra las primeras filas del DataFrame
        print(recetas_df.info())  # Información sobre columnas y tipos de datos

    return recetas_df

# Configuración de pesos y cache de ingredientes
PESO_FUZZY = 0.8  # Subimos ligeramente el peso de coincidencia
PESO_EMBEDDING = 0.2
MIN_PUNTAJE_FUZZY = 85

# Umbral de Levenshtein para nombres casi idénticos
UMBRAL_LEVENSHTEIN = 3

# Diccionario de sinónimos
sinonimos_ingredientes = {
    # Aceites y grasas
    "aceite de oliva": ["aceite", "aceite neutro", "aceite vegetal", "aceite de girasol", "aceite de coco"],
    "manteca": ["mantequilla", "margarina", "grasa", "manteca vegetal"],
    "mantequilla": ["manteca", "margarina"],
    
    # Verduras
    "cebolla": ["cebolla de verdeo", "cebolla morada", "cebolla blanca", "cebolleta", "cebolla de verdeo", "chalote"],
    "pimiento": ["pimiento rojo", "pimiento verde", "pimiento amarillo", "morrón", "ají"],
    "ajo": ["diente de ajo", "ajo en polvo", "ajos"],
    "calabaza": ["zapallo", "calabacín", "anco", "butternut"],
    "choclo": ["maíz", "granos de choclo", "choclo amarillo", "mazorca", "elote"],
    "papa": ["patata", "papa amarilla", "papa blanca"],
    "tomate": ["tomate triturado", "salsa de tomate", "tomate perita", "tomate cherry", "puré de tomate"],
    "batata": ["boniato", "camote"],
    "zapallito": ["zucchini", "zapallito verde"],
    "remolacha": ["betabel", "remolacha roja"],
    "berenjena": ["eggplant"],
    "rúcula": ["arúgula", "lechuga rucula"],
    "lechuga": ["repollo", "radicheta", "radicchio", "escarola", "hojas verdes"],

    # Legumbres
    "garbanzo": ["chícharo", "chicharo"],
    "lenteja": ["lentejón", "lentejas verdes", "lentejas pardas"],
    "poroto": ["judía", "frijol", "alubia", "habichuela", "loubia"],
    
    # Hierbas y especias
    "perejil": ["cilantro", "coriandro"],
    "cilantro": ["perejil chino", "coriandro"],
    "albahaca": ["basilico"],
    "romero": ["rosemary"],
    "tomillo": ["thyme"],
    "laurel": ["hoja de laurel", "bay leaf"],
    "orégano": ["oregano seco", "orégano fresco"],
    "mostaza": ["mostaza en polvo", "mostaza Dijon"],
    "curry": ["polvo de curry", "pasta de curry"],
    "pimentón": ["paprika", "ají molido", "chile en polvo", "pimiento molido"],
    "jengibre": ["jengibre fresco", "jengibre en polvo"],
    "limón": ["jugo de limón", "ralladura de limón"],
    "vinagre": ["aceto", "vinagre de vino", "vinagre de manzana", "vinagre balsámico", "vinagre blanco"],

    # Lácteos y derivados
    "queso": ["queso rallado", "queso cremoso", "queso parmesano", "queso azul", "queso en hebras", "queso cheddar", "queso mozzarella"],
    "yogur": ["yogurt", "yogur natural", "yogurt griego"],
    "leche": ["leche entera", "leche descremada", "leche vegetal", "leche de almendra", "leche de soja"],

    # Harinas y cereales
    "harina": ["harina de trigo", "harina 0000", "harina integral", "harina leudante", "harina de maíz", "harina de arroz"],
    "pan rallado": ["miga de pan", "pan molido", "panko"],
    "arroz": ["arroz integral", "arroz yamaní", "arroz basmati", "arroz jazmín", "arroz para risotto", "arroz blanco"],
    "fideos": ["pasta", "espagueti", "macarrones", "tallarines", "fusilli", "penne"],

    # Proteínas y carnes
    "huevo": ["huevos", "clara de huevo", "yema de huevo"],
    "pollo": ["pechuga de pollo", "muslo de pollo", "alitas de pollo"],
    "carne de res": ["ternera", "bife", "carne molida", "vaca"],
    "carne de cerdo": ["puerco", "cerdo", "chorizo"],
    "tofu": ["queso de soja", "soja fermentada"],
    "soja": ["soja texturizada", "porotos de soja"],

    # Mariscos
    "pescado": ["filete de pescado", "salmón", "atún", "merluza"],
    "marisco": ["camarón", "gamba", "langostino", "calamar", "pulpo"],

    # Otros
    "caldo": ["consomé", "sopa base", "fondo"],
    "salsa de soja": ["soya", "salsa de soya", "salsa teriyaki"],
    "miel": ["jarabe de agave", "miel de maple"],
    "chocolate": ["chocolate amargo", "cacao en polvo", "chocolate negro", "chocolate blanco"],
    "maicena": ["fécula de maíz", "almidón de maíz"],
    "azúcar": ["azúcar blanca", "azúcar rubia", "azúcar morena", "azúcar de coco"],
    "sal": ["sal gruesa", "sal fina", "sal marina"],
    "pimienta": ["pimienta negra", "pimienta blanca", "pimienta en grano"],
}

# Diccionario de categorías y umbrales adaptativos
categorias_umbral = {
    "aceite": 0.8, "cebolla": 0.85, "pimiento": 0.85, "ajo": 0.9, "zanahoria": 0.85, "calabaza": 0.85, "choclo": 0.8,"queso": 0.8,"huevo": 0.9,"harina": 0.85,"arroz": 0.85,
    "tomate": 0.8,"espinaca": 0.85,"perejil": 0.9,"cilantro": 0.85,"albahaca": 0.85,"remolacha": 0.85,"manteca": 0.8,"garbanzo": 0.8,"limón": 0.9,"papa": 0.85,
    "berenjena": 0.85,"zapallito": 0.85,"lenteja": 0.85,"soja": 0.8,"maíz": 0.8,"alcaucil": 0.8,"puerro": 0.85,"rúcula": 0.85,"yogur": 0.8,"apio": 0.8,"caldo": 0.8,
    "hongo": 0.8,"batata": 0.85,"pan": 0.8,"tofu": 0.8,"mostaza": 0.8,"coliflor": 0.8,"curry": 0.8,"lechuga": 0.8,"vinagre": 0.8,
}

def obtener_umbral_ingrediente(ingrediente):
    for categoria, umbral in categorias_umbral.items():
        if categoria in ingrediente:
            return umbral
    return 0.7  # Umbral por defecto si no está en el diccionario

## Diccionario global para almacenar embeddings precargados de ingredientes frecuentes
ingredientes_frecuentes = [
    "cebolla", "ajo", "pimiento", "calabaza", "choclo", "queso", "huevo", "harina", "arroz", "tomate", "espinaca", "perejil", "cilantro", "zanahoria", "lechuga", "leche", "queso crema", "mozzarella", "crema de leche", "tofu", "carne de res", 
    "pollo", "garbanzos", "lentejas", "porotos", "avena", "frutilla", "banana", "pepino", "palta", "zapallo", "tomate cherry", "orégano", "pimienta", "ají molido", "laurel", "mostaza", "pan rallado", "aceite de oliva", "vinagre", "azúcar", "sal"
]
embeddings_cache_frecuentes = {ingrediente: get_batch_embeddings(ingrediente) for ingrediente in ingredientes_frecuentes}

# Obtener el término principal para cada ingrediente y, si aplica, un embedding precargado
@medir_tiempo
def obtener_termino_principal(ingrediente):
    for term_principal, sinonimos in sinonimos_ingredientes.items():
        if any(sinonimo in ingrediente.lower() for sinonimo in sinonimos):
            return term_principal, embeddings_cache_frecuentes.get(term_principal)
    return ingrediente.lower(), None

def obtener_palabras_clave(ingrediente):
    # Limpieza inicial del texto
    ingrediente = limpiar_descripciones(ingrediente)

    # Extraer cantidad y unidad para eliminar estos términos
    ingrediente_limpio, cantidad, unidad = extraer_cantidad_unidad(ingrediente)

    # Extraer solo términos esenciales
    palabras = ingrediente_limpio.split()
    palabras_clave = [
        obtener_termino_principal(palabra)[0]  # Mapea sinónimos a término principal
        for palabra in palabras
        if palabra not in palabras_irrelevantes and len(palabra) > 2
    ]

    # Seleccionar solo la palabra principal (más relevante)
    palabra_principal = palabras_clave[0] if palabras_clave else ingrediente_limpio
    return [palabra_principal]  # Devuelve solo la palabra principal

def filtrar_no_ingredientes(ingredientes):
    return '\n'.join(
        ing for ing in ingredientes.split('\n')
        if not any(irrelevante.lower() in ing.lower() for irrelevante in palabras_irrelevantes)
    )

def buscar_productos_palabras_clave(palabra_clave, engine):
    # Si no encuentra con la palabra clave, intenta con sus sinónimos
    sinónimos = sinonimos_ingredientes.get(palabra_clave, [palabra_clave])
    for termino in sinónimos:
        query = text(f"SELECT nombre, precio_min FROM productos WHERE nombre ILIKE :termino AND NOT nombre ILIKE '%jugo%' AND NOT nombre ILIKE '%gaseosa%'")
        params = {"termino": f"%{termino}%"}
        
        with engine.connect() as conn:
            result = conn.execute(query, params)
            productos_filtrados = pd.DataFrame(result.fetchall(), columns=result.keys())
            
            # Si encuentra resultados, retorna
            if not productos_filtrados.empty:
                return productos_filtrados

    return pd.DataFrame()  # Si no encuentra nada, retorna DataFrame vacío


# Puntos de optimización
@medir_tiempo
def calcular_puntaje_producto(producto, palabras_clave, ingrediente_embedding):
    puntaje = 0

    for palabra in palabras_clave:
        # Calcular similitud fuzzy entre las palabras clave y el nombre del producto
        similarity_fuzzy = fuzz.partial_ratio(palabra.lower(), producto['nombre'].lower()) / 100
        if similarity_fuzzy < MIN_PUNTAJE_FUZZY:
            continue

        # Obtener el embedding del producto desde la columna de embeddings
        producto_embedding = np.array(producto['embedding'])

        # Asegurarse de que tanto el embedding del producto como el del ingrediente sean vectores 1D
        if len(producto_embedding.shape) > 1:
            producto_embedding = producto_embedding.flatten()
        if len(ingrediente_embedding.shape) > 1:
            ingrediente_embedding = ingrediente_embedding.flatten()

        # Reshape para usar en cosine_similarity
        producto_embedding_reshaped = producto_embedding.reshape(1, -1)
        ingrediente_embedding_reshaped = ingrediente_embedding.reshape(1, -1)

        # Calcular la similitud del embedding
        similarity_embedding = cosine_similarity(ingrediente_embedding_reshaped, producto_embedding_reshaped).flatten()[0]

        # Combinar las similitudes usando los pesos definidos
        puntaje += PESO_FUZZY * similarity_fuzzy + PESO_EMBEDDING * similarity_embedding

    return puntaje

# Ingredientes que no necesitan cálculo de costo
INGREDIENTES_EXCLUIDOS = {"agua", "sal", "pimienta"}

@medir_tiempo
def emparejar_ingredientes(ingredientes, productos_df):
    # Validar que el DataFrame no esté vacío y tenga las columnas esperadas
    if productos_df.empty:
        raise ValueError("El DataFrame de productos está vacío. Verifica el archivo CSV o la base de datos.")
    
    columnas_esperadas = {"nombre", "precio_min"}
    if not columnas_esperadas.issubset(productos_df.columns):
        raise ValueError(f"El DataFrame de productos no tiene las columnas requeridas: {columnas_esperadas}")

    # Inspección inicial del DataFrame
    print(f"Total de productos en DataFrame: {len(productos_df)}")
    print(f"Columnas del DataFrame: {productos_df.columns.tolist()}")
    if 'embedding' in productos_df.columns:
        print(f"Primer embedding (si existe): {productos_df['embedding'].iloc[0] if not productos_df.empty else 'Sin datos'}")
    else:
        print("Advertencia: El DataFrame de productos no contiene la columna 'embedding'.")

    # Validar que los ingredientes no estén vacíos
    if not ingredientes.strip():
        raise ValueError("La lista de ingredientes está vacía o no es válida.")

    # Continuar con el procesamiento después de las validaciones
    costo_total = 0
    ingredientes_faltantes = []
    ingredientes_encontrados = 0

    ingredientes_lista = [
        ing for ing in ingredientes.split('\n')
        if ing.strip() and validar_ingrediente(limpiar_descripciones(ing))
    ]
    if USE_DATABASE:
        engine = connect_db_precios()
    else:
        engine = None

    for i, ingrediente in enumerate(ingredientes_lista):
        ingrediente_limpio, cantidad, unidad = extraer_cantidad_unidad(ingrediente)

        if ingrediente_limpio in INGREDIENTES_EXCLUIDOS:
            print(f"Ignorando {ingrediente_limpio} por estar en la lista de excluidos.")
            continue

        if ingrediente_limpio in ingredientes_cache:
            mejor_producto, precio_min = ingredientes_cache[ingrediente_limpio]
            print(f"Usando caché para {ingrediente_limpio} -> Producto: {mejor_producto['nombre']}, Costo: {precio_min}")
        else:
            palabras_clave = obtener_palabras_clave(ingrediente_limpio)
            ingrediente_embedding = get_batch_embeddings(ingrediente_limpio)

            # Verificación de embeddings
            if ingrediente_embedding.ndim != 1:
                print(f"Error: El embedding del ingrediente '{ingrediente_limpio}' no es un vector 1D.")
                print(f"Forma del embedding: {ingrediente_embedding.shape}")
                continue
            print(f"Procesando ingrediente {i + 1}/{len(ingredientes_lista)}: {ingrediente} con palabras clave: {palabras_clave}")

            productos_filtrados = buscar_productos_palabras_clave(palabras_clave[0], engine)
            if productos_filtrados.empty and not USE_DATABASE:
                print(f"Buscando en productos_df para {palabras_clave[0]}...")
                productos_filtrados = productos_df[productos_df['nombre_limpio'].str.contains(palabras_clave[0], na=False, case=False)]

            umbral = obtener_umbral_ingrediente(ingrediente)
            productos_candidatos = []
            for _, row in productos_filtrados.iterrows():
                producto_embedding = np.array(row['embedding'])
                if producto_embedding.ndim != 1:
                    print(f"Error: Embedding del producto '{row['nombre']}' no es un vector 1D.")
                    print(f"Forma del embedding: {producto_embedding.shape}")
                    continue

                print(f"Evaluando producto: {row['nombre']}")
                print(f"Embedding del producto (forma): {producto_embedding.shape}")
                print(f"Embedding del ingrediente (forma): {ingrediente_embedding.shape}")

                puntaje_producto = calcular_puntaje_producto(row, palabras_clave, ingrediente_embedding)
                print(f"Puntaje calculado para producto '{row['nombre']}': {puntaje_producto}")

                if puntaje_producto > umbral:
                    productos_candidatos.append((row, puntaje_producto))

            if productos_candidatos:
                producto_barato = min(productos_candidatos, key=lambda x: x[0]['precio_min'])[0]
                precio_min = producto_barato['precio_min']

                if unidad in conversiones:
                    precio_min = (precio_min / conversiones[unidad]) * cantidad
                else:
                    print(f"Advertencia: Unidad '{unidad}' no encontrada. Usando cantidad como predeterminada.")
                    precio_min *= cantidad

                actualizar_cache_ingrediente(ingrediente_limpio, producto_barato, precio_min)
            else:
                print(f"No se encontró coincidencia suficiente para el ingrediente: {ingrediente}")
                ingredientes_faltantes.append(ingrediente)
                continue

        costo_total += precio_min
        ingredientes_encontrados += 1

    print(f"\nResumen de procesamiento:")
    print(f"Ingredientes encontrados: {ingredientes_encontrados}/{len(ingredientes_lista)}")
    print(f"Ingredientes faltantes: {len(ingredientes_faltantes)}")
    
    if ingredientes_faltantes:
        with open("ingredientes_faltantes.log", "w") as log_file:
            for faltante in ingredientes_faltantes:
                log_file.write(f"{faltante}\n")

    if engine:
        engine.dispose()
    return costo_total, ingredientes_encontrados

# Función para recomendar recetas en base al presupuesto
def recomendar_recetas(presupuesto_semanal, productos_df, recetas_df, max_recetas=5):
    recetas_recomendadas = []
    costo_semanal = 0
    
    for _, row in recetas_df.iterrows():
        ingredientes = row['ingredientes']
        costo_receta, ingredientes_encontrados = emparejar_ingredientes(ingredientes, productos_df)
        
        if ingredientes_encontrados >= len(ingredientes.split('\n')) - 4:
            if (costo_semanal + costo_receta) <= presupuesto_semanal:
                recetas_recomendadas.append({
                    "nombre": row['nombre'],
                    "costo": costo_receta
                })
                costo_semanal += costo_receta
                print(f"Receta '{row['nombre']}' añadida con costo {costo_receta}. Costo semanal acumulado: {costo_semanal}")
        
        if len(recetas_recomendadas) >= max_recetas:
            break

    return recetas_recomendadas, costo_semanal

# Función principal para generar recomendaciones
def generar_recomendaciones(presupuesto_semanal):
    print("Generando recomendaciones...")
    
    # Cargar datos de recetas y productos
    recetas_df = cargar_datos_recetas()
    validar_recetas_df(recetas_df)  # Validar recetas después de cargarlas
    
    productos_df = cargar_datos_productos()
    validar_productos_df(productos_df)  # Validar productos después de cargarlos

    if recetas_df.empty or productos_df.empty:
        print("No se encontraron datos suficientes para generar recomendaciones.")
        return
    
    recomendaciones, costo_total = recomendar_recetas(presupuesto_semanal, productos_df, recetas_df)
    
    if recomendaciones:
        print(f"\nRecomendaciones para un presupuesto semanal de {presupuesto_semanal}:")
        for receta in recomendaciones:
            print(f"- {receta['nombre']} (Costo: ${receta['costo']:.2f})")
        print(f"Total estimado: ${costo_total:.2f}")
    else:
        print("No se encontraron suficientes recetas que se ajusten al presupuesto.")
                
# Ejecutar recomendaciones con un presupuesto dado
if __name__ == "__main__":
    presupuesto_semanal = 40000
    generar_recomendaciones(presupuesto_semanal)

def verificar_embeddings(embeddings_file="productos_embeddings.npy"):
    try:
        if os.path.exists(embeddings_file):
            embeddings = np.load(embeddings_file, allow_pickle=True)
            print(f"Archivo {embeddings_file} encontrado.")
            print(f"Número total de embeddings: {len(embeddings)}")
            print(f"Forma del primer embedding (si existe): {embeddings[0].shape if len(embeddings) > 0 else 'No hay embeddings'}")
        else:
            print(f"Archivo {embeddings_file} no encontrado. Verifica si fue generado correctamente.")
    except Exception as e:
        print(f"Error al cargar embeddings desde {embeddings_file}: {e}")

# Llama esta función para inspeccionar
verificar_embeddings()