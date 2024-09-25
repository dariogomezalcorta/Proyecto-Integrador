from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

def scrape_data():
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get("https://www.preciosclaros.gob.ar/#!/buscar-productos")
    wait = WebDriverWait(driver, 40)

    try:
        categoria_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//h6[text()="Almacén"]')))
        categoria_button.click()
        print("Categoría Almacén abierta.")

        all_results = []
        current_page = 0

        while True:
            current_page += 1
            print(f"Procesando página: {current_page}")

            # Esperar que los productos de la página actual carguen
            items = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.col-md-4.col-xs-12.producto.ng-scope')))
            print(f"Encontrados {len(items)} productos en la página actual.")

            for item in items:
                nombre = item.find_element(By.CSS_SELECTOR, '.nombre-producto.ng-binding').text
                precio = item.find_element(By.CSS_SELECTOR, '.precio.ng-binding').text

                if nombre and precio:
                    precios = re.findall(r"\$([\d,.]+)", precio)
                    if len(precios) == 2:
                        precio_min = float(precios[0].replace(".", "").replace(",", ".").strip())
                        precio_max = float(precios[1].replace(".", "").replace(",", ".").strip())
                        all_results.append((nombre, precio_min, precio_max))
                    elif len(precios) == 1:
                        precio_unico = float(precios[0].replace(".", "").replace(",", ".").strip())
                        all_results.append((nombre, precio_unico, precio_unico))

            # Verificar si existe el botón para pasar a la siguiente página
            next_page_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[aria-label="Next"]')))
            if 'disabled' in next_page_button.get_attribute('class'):
                print("No hay más páginas. Finalizando scraping.")
                break

            # Espera activa antes de hacer clic en el siguiente botón para asegurar que la página esté completamente cargada
            time.sleep(3)
            next_page_button.click()
            print("Cambiando a la siguiente página...")
            # Espera para asegurar que el DOM se haya actualizado completamente
            wait.until(EC.staleness_of(items[0]))

    except Exception as e:
        print(f'Error durante el procesamiento: {str(e)}')
        driver.save_screenshot('error_screenshot.png')

    finally:
        driver.quit()

    return all_results

# Ejecutar la función de scraping
results = scrape_data()
print(f"Total de productos recogidos: {len(results)}")
