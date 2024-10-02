from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re

def scrape_category(driver, wait, categoria_xpath):
    # Hacer clic en la categoría seleccionada
    categoria_button = wait.until(EC.element_to_be_clickable((By.XPATH, categoria_xpath)))
    categoria_button.click()
    print(f"Categoría {categoria_xpath} abierta.")

    all_results = []
    current_page = 0

    while True:
        current_page += 1
        print(f"Procesando página: {current_page}")

        # Esperar que los productos carguen
        try:
            items = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.col-md-4.col-xs-12.producto.ng-scope')))
            print(f"Encontrados {len(items)} productos en la página actual.")

            for item in items:
                nombre = item.find_element(By.CSS_SELECTOR, '.nombre-producto.ng-binding').text
                precio = item.find_element(By.CSS_SELECTOR, '.precio.ng-binding').text

                if nombre and precio:
                    # Modificar la expresión regular para capturar precios con espacios y comas
                    precios = re.findall(r"\$([\d\s,.]+)", precio)

                    if len(precios) == 2:
                        # Eliminar los espacios en blanco de los precios y convertir las comas en puntos decimales
                        precio_min = precios[0].replace(" ", "").replace(".", "").replace(",", ".").strip()
                        precio_max = precios[1].replace(" ", "").replace(".", "").replace(",", ".").strip()

                        # Validar que los precios no sean absurdos
                        if float(precio_min) > 1 and float(precio_max) > 1:
                            all_results.append((nombre, precio_min, precio_max))
                        else:
                            print(f"Precios no válidos para {nombre}: {precio_min} - {precio_max}")

                    elif len(precios) == 1:
                        # Caso donde solo hay un precio
                        precio_unico = precios[0].replace(" ", "").replace(".", "").replace(",", ".").strip()

                        # Validar que el precio no sea absurdo
                        if float(precio_unico) > 1:
                            all_results.append((nombre, precio_unico, precio_unico))
                        else:
                            print(f"Precio único no válido para {nombre}: {precio_unico}")

        except Exception as e:
            print(f"Error al procesar la página {current_page}: {e}")
            break

        # Intentar pasar a la siguiente página, si el botón existe
        try:
            next_page_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[aria-label="Next"]')))
            if 'disabled' in next_page_button.get_attribute('class'):
                print(f"No hay más páginas. Finalizando scraping de la categoría en la página {current_page}.")
                break

            next_page_button.click()
            print("Cambiando a la siguiente página...")
            wait.until(EC.staleness_of(items[0]))  # Esperar a que la página siguiente cargue completamente

        except Exception as e:
            print(f"Error al intentar cambiar de página: {e}")
            break

    return all_results

def go_home(driver, wait):
    # Volver al home
    home_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//a[@class="navbar-brand"]')))
    home_button.click()
    wait.until(EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "buscador-categorias")]//h6')))
    print("Regresando al Home.")

def scrape_data():
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get("https://www.preciosclaros.gob.ar/#!/buscar-productos")
    wait = WebDriverWait(driver, 40)

    try:
        # Definir las categorías que quieres scrapear
        categorias = {
            "Almacén": '//h6[text()="Almacén"]',
            "Alimentos congelados": '//h6[text()="Alimentos congelados"]',
            "Bebidas sin alcohol": '//h6[text()="Bebidas sin alcohol"]',
            "Frescos": '//h6[text()="Frescos"]'
        }

        all_data = []

        for categoria, xpath in categorias.items():
            print(f"Scrapeando la categoría: {categoria}")
            resultados_categoria = scrape_category(driver, wait, xpath)
            all_data.extend(resultados_categoria)
            
            # Volver al home antes de pasar a la siguiente categoría
            go_home(driver, wait)

        print(f"Total de productos recogidos: {len(all_data)}")
    
    except Exception as e:
        print(f'Error durante el procesamiento: {str(e)}')
        driver.save_screenshot('error_screenshot.png')

    finally:
        driver.quit()

    return all_data

if __name__ == "__main__":
    results = scrape_data()
    print(f"Total de productos recogidos: {len(results)}")
