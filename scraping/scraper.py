from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

def scrape_data():
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get("https://www.preciosclaros.gob.ar/#!/buscar-productos")
    time.sleep(5)  # Espera para que la página cargue completamente

    # Definir una lista de categorías para navegar
    categorias = ["Almacén", "Bebidas sin alcohol", "Alimentos congelados", "Frescos"]

    # Iterar sobre cada categoría
    all_results = []
    for categoria in categorias:
        # Hacer clic en el botón de la categoría correspondiente usando el texto de la clase h6
        categoria_button = driver.find_element(By.XPATH, f'//h6[text()="{categoria}"]')
        categoria_button.click()
        time.sleep(5)  # Espera para que la página de la categoría cargue completamente
        
        # Extraer productos y precios de la categoría actual
        productos = driver.find_elements(By.CSS_SELECTOR, '.product-name')
        precios = driver.find_elements(By.CSS_SELECTOR, '.price-tag')

        # Guardar los resultados de la categoría
        results = []
        for nombre, precio in zip(productos, precios):
            results.append((nombre.text, precio.text))
        
        # Agregar resultados a la lista global
        all_results.extend(results)
        
        # Regresar a la página de categorías (esto es necesario para evitar errores de navegación)
        driver.get("https://www.preciosclaros.gob.ar/#!/buscar-productos")
        time.sleep(5)
    
    driver.quit()  # Cierra el navegador
    return all_results

