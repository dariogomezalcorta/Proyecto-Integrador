from base_de_datos.database import setup_database, clear_table, insert_product
from scraping.scraper import scrape_data

def main():
    # Configurar la base de datos y limpiarla antes de empezar
    setup_database()
    clear_table()

    # Ejecutar el scraping
    productos = scrape_data()
    for nombre, precio_min, precio_max in productos:
        insert_product(nombre, precio_min, precio_max)

if __name__ == "__main__":
    main()
