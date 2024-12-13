import sys
from base_de_datos.database import (
    setup_database_precios, clear_table_precios, insert_product, 
    setup_database_recetas, insert_receta
)
from scraping.scraper import scrape_data, scrape_recetas  # Asegúrate de importar scrape_recetas
#from modelos.recomendacion import cargar_datos_interacciones, crear_matriz_similitud_productos, recomendar_productos

def ejecutar_scraper_precios():
    try:
        print("Ejecutando scraper de productos...")
        setup_database_precios()
        clear_table_precios()

        # Ejecutar el scraping de productos
        productos = scrape_data()  # Aquí llamas al scraping de productos
        for nombre, precio_min, precio_max in productos:
            insert_product(nombre, precio_min, precio_max)
        
        print("Scraping de productos completado e insertado en la base de datos.")
    
    except Exception as e:
        print(f"Error durante el scraping de productos: {str(e)}")

def ejecutar_scraper_recetas():
    try:
        print("Ejecutando scraper de recetas...")
        setup_database_recetas()  # Crear la base de datos de recetas si no existe

        # Ejecutar el scraping de recetas
        recetas = scrape_recetas()  # Esta función debe retornar una lista de recetas

        for receta in recetas:
            insert_receta(receta['nombre'], receta['ingredientes'], receta['procedimiento'])

        print("Scraping de recetas completado e insertado en la base de datos.")
    
    except Exception as e:
        print(f"Error durante el scraping de recetas: {str(e)}")

def ejecutar_recomendacion():
    try:
        print("Generando recomendaciones...")
        interacciones = cargar_datos_interacciones()
        similitud_productos_df = crear_matriz_similitud_productos(interacciones)
        
        recomendaciones = recomendar_productos(101, similitud_productos_df, top_n=5)
        print("Recomendaciones:\n", recomendaciones)
    
    except Exception as e:
        print(f"Error durante la generación de recomendaciones: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "scrape_precios":
            ejecutar_scraper_precios()
        elif sys.argv[1] == "scrape_recetas":
            ejecutar_scraper_recetas()
        elif sys.argv[1] == "recom":
            ejecutar_recomendacion()
        else:
            print("Modo no reconocido. Usa 'scrape_precios', 'scrape_recetas' o 'recom'.")
    else:
        print("Por favor, especifica un modo. Usa 'scrape_precios', 'scrape_recetas' o 'recom'.")
