from scraping.scraper import scrape_data
from database.database import setup_database, insert_product

def main():
    setup_database()  # Configura la tabla de base de datos si aún no existe
    productos = scrape_data()
    for nombre, precio in productos:
        insert_product(nombre, precio)

if __name__ == "__main__":
    main()
