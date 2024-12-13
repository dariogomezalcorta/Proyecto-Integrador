import pandas as pd
import re
from base_de_datos.database import connect_db_recetas, connect_db_precios
from fuzzywuzzy import fuzz, process
import os
import sys
import unicodedata
import spacy
from sqlalchemy import create_engine, text

def connect_db_recetas():
    engine = create_engine('postgresql://postgres:.Pikachu12345.@localhost:5432/Recetas_Cocineros')
    return engine

def connect_db_precios():
    engine = create_engine('postgresql://postgres:.Pikachu12345.@localhost:5432/PreciosClaros')
    return engine

nlp = spacy.load("es_core_news_md")

ruta_archivo = r"C:\Users\dario\OneDrive\Escritorio\Proyecto-Integrador\resultados.txt"

palabras_irrelevantes = [
    "INGREDIENTES", "Extra:", "Cubierta:", "Masa:", "Relleno:", "Opción:", "Opcionales:", "Salsa:", "Caldo", "Aderezo",
    "Hummus", "Ligue", "Preparación", "Pasos", "Método", "Instrucciones", "Procedimiento", "Porciones", "Rinde",
    "Pizca", "Pellizco", "Manojo", "Paquete", "Sobre", "Con", "Y", "O", "Cantidad", "Partes", "Sugerencia",
    "Cuchara", "Cucharadita", "Pizca", "Porción", "Cocción", "Tiempo", "Freír", "Hornear", "Hervir", "Revolver",
    "Mezclar", "Batir", "Enfriar", "Reposar", "Ligeramente", "Fresco", "Crudo", "Picada", "Cortada", "En",
    "Tiras", "Cubos", "Fileteada", "Molido", "Rallado", "Tostado", "Tamaño", "Grande", "Mediana", "Pequeña",
    "A gusto", "Según preferencia", "Opcional", "Puede acompañar", "Decorar con", "A elección", "Optativo", "C/N",
    "Al gusto", "En rodajas", "Batidas a nieve", "Rinde", "Entre", "Para servir:", "Para acompañar:", "Para la masa:",
    "Para el relleno:", "Paso", "Nivel", "Punto", "Pieza", "Unidades", "Armado:", "Marinada:", "Frito:", 
    "Guarnición:", "Canasta:", "Aderezo:", "Emplatado:", "Extra:", "Para el pan:", "Ensalada:", 
    "Para las papas picantes ??", "-", ":", "?", ".", "1⃣", "puñado", "taza", "atados", "1 unid"
]

conversiones = {
    "kg": 1000, "gramos": 1, "g": 1, "litro": 1000, "mililitros": 1, "ml": 1, "cda": 15, "cdta": 5, "taza": 240, "pizca": 0.36, "manojo": 50, 
    "unidad": 1, "huevo": 60, "paquete": 500, "lata": 400, "hoja": 1, "diente": 5, "botella": 1000, "frasco": 200, "pellizco": 0.18, "limon": 65,        
    "jugo de limon": 50, "limones": 65, "naranja": 130, "jugo de naranja": 100, "papa": 150, "zanahoria": 70, "tomate": 120, "cebolla": 150,     
    "pimiento": 120, "banana": 120, "manzana": 180, "pera": 160, "pepino": 200, "calabaza": 400, "berenjena": 300, "ajo": 5, "ramita": 5, 
    "hoja de laurel": 0.2, "cabeza de ajo": 30,
}

def extraer_cantidad_unidad(ingrediente):
    match = re.search(r'(\d+)\s*(kg|gramos|g|mililitros|ml|litro|lata|cda|cdta|taza|hoja|diente|chorrito|puñado)', ingrediente.lower())
    if match:
        cantidad = int(match.group(1))
        unidad = match.group(2)
        ingrediente_limpio = ingrediente[:match.start()].strip()
    else:
        if any(ing in ingrediente.lower() for ing in ["sal", "pimienta", "aceite", "agua"]):
            cantidad = 1
            unidad = "cda"
        else:
            cantidad = 1
            unidad = None
        ingrediente_limpio = ingrediente.strip()
    
    return ingrediente_limpio, cantidad, unidad


def limpiar_descripciones(ingrediente):
    ingrediente = ingrediente.lower()
    ingrediente = re.sub(r'[\-\(\)\.,]', '', ingrediente).strip()
    ingrediente = re.sub(r'\b(grande|mediana|pequena|picada|cortada|en cubos|en rodajas|limpio|limpios|fresco|frescos|desgranado|natural)\b', '', ingrediente).strip()
    ingrediente = re.sub(r'\s+', ' ', ingrediente).strip()
    return ingrediente

def limpiar_ingredientes(ingredientes):
    ingredientes_limpios = []
    for ingrediente in ingredientes.split('\n'):
        palabras = ingrediente.split()
        palabras_limpias = [palabra for palabra in palabras if palabra.upper() not in palabras_irrelevantes]
        ingredientes_limpios.append(' '.join(palabras_limpias))
    return '\n'.join(ingredientes_limpios)

def cargar_datos_recetas():
    engine = connect_db_recetas()
    query = "SELECT nombre, ingredientes FROM recetas WHERE nombre NOT ILIKE '%alfajor%' AND nombre NOT ILIKE '%torta%'"
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query)).mappings()  # Usamos .mappings() para obtener un diccionario por fila
            recetas = [dict(row) for row in result]
            recetas_df = pd.DataFrame(recetas)
        if recetas_df.empty:
            print("No se encontraron datos en la tabla de recetas.")
        else:
            print(f"Datos cargados de recetas: {recetas_df.shape[0]} filas.")
    except Exception as e:
        print(f"Error al cargar datos de recetas: {e}")
        recetas_df = pd.DataFrame()  # DataFrame vacío en caso de error
    finally:
        engine.dispose()
    return recetas_df

def cargar_datos_productos():
    engine = connect_db_precios()
    query = "SELECT nombre, precio_min FROM productos"
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query)).mappings()
            productos = [dict(row) for row in result]
            productos_df = pd.DataFrame(productos)
        if productos_df.empty:
            print("No se encontraron datos en la tabla de productos.")
        else:
            print(f"Datos cargados de productos: {productos_df.shape[0]} filas.")
    except Exception as e:
        print(f"Error al cargar datos de productos: {e}")
        productos_df = pd.DataFrame()
    finally:
        engine.dispose()

    if not productos_df.empty:
        productos_df['nombre_limpio'] = productos_df['nombre'].apply(limpiar_descripciones)
        productos_df['embedding'] = productos_df['nombre_limpio'].apply(lambda x: nlp(x).vector if nlp(x).vector_norm else None)
    
    return productos_df

def convertir_unidades(ingrediente, cantidad, unidad):
    if unidad in conversiones:
        return cantidad * conversiones[unidad]
    print(f"Unidad desconocida '{unidad}' en ingrediente: {ingrediente}")
    return cantidad

def emparejar_ingredientes(ingredientes, productos_df):
    ingredientes_limpios = limpiar_ingredientes(ingredientes)
    ingredientes_lista = ingredientes_limpios.split('\n')
    costo_total = 0
    ingredientes_encontrados = 0
    
    for ingrediente in ingredientes_lista:
        print(f"Buscando coincidencias para el ingrediente: '{ingrediente}'")  # Depuración
        doc_ingrediente = nlp(ingrediente.lower())
        mejor_producto, mejor_score = None, -1
        for index, row in productos_df.dropna(subset=['embedding']).iterrows():
            if doc_ingrediente.vector_norm and row['embedding'].vector_norm:
                similarity_spacy = doc_ingrediente.similarity(row['embedding'])
            else:
                similarity_spacy = 0
            similarity_fuzzy = fuzz.token_sort_ratio(ingrediente.lower(), row['nombre'].lower()) / 100
            similarity = max(similarity_spacy, similarity_fuzzy)
            if similarity > mejor_score:
                mejor_score = similarity
                mejor_producto = row['nombre']
        
        if mejor_score > 0.7:
            print(f"Mejor coincidencia para '{ingrediente}' es '{mejor_producto}' con similitud {mejor_score}")  # Depuración
            producto_encontrado = productos_df[productos_df['nombre'] == mejor_producto]
            precio_min = producto_encontrado['precio_min'].min()
            costo_total += precio_min
            ingredientes_encontrados += 1
        else:
            print(f"No se encontró coincidencia para el ingrediente: '{ingrediente}'")  # Depuración

    print(f"Costo total de ingredientes encontrados: {costo_total}, Ingredientes encontrados: {ingredientes_encontrados}")  # Depuración
    return costo_total, ingredientes_encontrados

def recomendar_recetas(presupuesto_semanal, productos_df, recetas_df, max_recetas=5):
    recetas_recomendadas = []
    costo_semanal = 0
    for index, row in recetas_df.iterrows():
        ingredientes = row['ingredientes']
        costo_receta, ingredientes_encontrados = emparejar_ingredientes(ingredientes, productos_df)
        print(f"Procesando receta: {row['nombre']} - Costo: {costo_receta}, Ingredientes encontrados: {ingredientes_encontrados}")  # Depuración
        if ingredientes_encontrados >= len(ingredientes.split('\n')) - 2:
            if (costo_semanal + costo_receta) <= presupuesto_semanal:
                recetas_recomendadas.append({
                    "nombre": row['nombre'],
                    "costo": costo_receta
                })
                costo_semanal += costo_receta
                print(f"Receta '{row['nombre']}' añadida con costo {costo_receta}. Costo semanal acumulado: {costo_semanal}")  # Depuración
            else:
                print(f"Receta '{row['nombre']}' excluida: excede el presupuesto semanal.")  # Depuración
        if len(recetas_recomendadas) >= max_recetas:
            break

    return recetas_recomendadas, costo_semanal

def generar_recomendaciones(presupuesto_semanal):
    print("Generando recomendaciones...")
    recetas_df = cargar_datos_recetas()
    productos_df = cargar_datos_productos()
    try:
        if recetas_df.empty or productos_df.empty:
            print("No se encontraron datos suficientes para generar recomendaciones.")
            return
        
        # No redirigimos a archivo para ver el resultado en la consola
        recomendaciones, costo_total = recomendar_recetas(presupuesto_semanal, productos_df, recetas_df)
        if recomendaciones:
            print(f"Recomendaciones para un presupuesto semanal de {presupuesto_semanal}:")
            for receta in recomendaciones:
                print(f"- {receta['nombre']} (Costo: ${receta['costo']:.2f})")
            print(f"Total estimado: ${costo_total:.2f}")
        else:
            print("No se encontraron suficientes recetas que se ajusten al presupuesto.")
    
    except Exception as e:
        print(f"Error durante la generación de recomendaciones: {e}")

if __name__ == "__main__":
    presupuesto_semanal = 30000
    generar_recomendaciones(presupuesto_semanal)
