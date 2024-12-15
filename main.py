import sys
from base_de_datos.database import (
    setup_database_precios, clear_table_precios, insert_product, 
    setup_database_recetas, insert_receta
)
from scraping.scraper import scrape_data, scrape_recetas  # Asegúrate de importar scrape_recetas
from modelos.recomendacion_transformer import cargar_datos_productos, cargar_datos_recetas, recomendar_recetas

USE_DATABASE = False  # Cambiar a True si se quieren usar las bases de datos.

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
        productos_df = cargar_datos_productos()  # Ya incluye lógica para archivos y base de datos
        recetas_df = cargar_datos_recetas()  # Ya incluye lógica para archivos y base de datos

        if productos_df.empty or recetas_df.empty:
            print("No se encontraron datos suficientes para generar recomendaciones.")
            return

        # Aquí puedes llamar a las funciones de recomendación existentes
        presupuesto_semanal = 30000  # Este valor podría ser dinámico
        recomendaciones, costo_total = recomendar_recetas(presupuesto_semanal, productos_df, recetas_df)

        if recomendaciones:
            print(f"\nRecomendaciones para un presupuesto semanal de {presupuesto_semanal}:")
            for receta in recomendaciones:
                print(f"- {receta['nombre']} (Costo: ${receta['costo']:.2f})")
            print(f"Total estimado: ${costo_total:.2f}")
        else:
            print("No se encontraron suficientes recetas que se ajusten al presupuesto.")

    except Exception as e:
        print(f"Error durante la generación de recomendaciones: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "scrape_precios":
            ejecutar_scraper_precios()
        elif sys.argv[1] == "scrape_recetas":
            ejecutar_scraper_recetas()
        elif sys.argv[1] == "recom":
            if len(sys.argv) > 2 and sys.argv[2] == "db":
                USE_DATABASE = True
            ejecutar_recomendacion()
        else:
            print("Modo no reconocido. Usa 'scrape_precios', 'scrape_recetas' o 'recom [db|file]'.")
    else:
        print("Por favor, especifica un modo. Usa 'scrape_precios', 'scrape_recetas' o 'recom [db|file]'.")

