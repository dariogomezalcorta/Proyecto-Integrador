from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re
import os
import json
import psycopg2
from base_de_datos.database import insert_receta

def scrape_category(driver, wait, categoria_xpath):
    categoria_button = wait.until(EC.element_to_be_clickable((By.XPATH, categoria_xpath)))
    categoria_button.click()
    print(f"Categoría {categoria_xpath} abierta.")

    all_results = []
    current_page = 0

    while True:
        current_page += 1
        print(f"Procesando página: {current_page}")

        try:
            items = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.col-md-4.col-xs-12.producto.ng-scope')))
            print(f"Encontrados {len(items)} productos en la página actual.")

            for item in items:
                nombre = item.find_element(By.CSS_SELECTOR, '.nombre-producto.ng-binding').text
                precio = item.find_element(By.CSS_SELECTOR, '.precio.ng-binding').text

                if nombre and precio:
                    precios = re.findall(r"\$([\d\s,.]+)", precio)

                    if len(precios) == 2:
                        precio_min = precios[0].replace(" ", "").replace(".", "").replace(",", ".").strip()
                        precio_max = precios[1].replace(" ", "").replace(".", "").replace(",", ".").strip()

                        if float(precio_min) > 1 and float(precio_max) > 1:
                            all_results.append((nombre, precio_min, precio_max))
                        else:
                            print(f"Precios no válidos para {nombre}: {precio_min} - {precio_max}")

                    elif len(precios) == 1:
                        precio_unico = precios[0].replace(" ", "").replace(".", "").replace(",", ".").strip()

                        if float(precio_unico) > 1:
                            all_results.append((nombre, precio_unico, precio_unico))
                        else:
                            print(f"Precio único no válido para {nombre}: {precio_unico}")

        except Exception as e:
            print(f"Error al procesar la página {current_page}: {e}")
            break

        try:
            next_page_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[aria-label="Next"]')))
            if 'disabled' in next_page_button.get_attribute('class'):
                print(f"No hay más páginas. Finalizando scraping de la categoría en la página {current_page}.")
                break

            next_page_button.click()
            print("Cambiando a la siguiente página...")
            wait.until(EC.staleness_of(items[0]))

        except Exception as e:
            print(f"Error al intentar cambiar de página: {e}")
            break

    return all_results

def go_home(driver, wait):
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

def clean_procedure(procedure_html):
    soup = BeautifulSoup(procedure_html, 'html.parser')

    for ad in soup.find_all(['ins', 'iframe', 'script']):
        ad.decompose()

    cleaned_procedure = soup.get_text(separator=" ", strip=True)
    cleaned_procedure = re.sub(r'\s+', ' ', cleaned_procedure)

    return cleaned_procedure

# Cargar recetas previamente guardadas en el JSON (si existe)
def load_existing_recipes(json_file):
    if os.path.exists(json_file):
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# Guardar las recetas en el archivo JSON inmediatamente después de extraer una receta
def save_recipe_to_json(receta, json_file):
    all_recipes = load_existing_recipes(json_file)
    all_recipes.append(receta)

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(all_recipes, f, ensure_ascii=False, indent=4) 

def scrape_recetas():
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    wait = WebDriverWait(driver, 60)
    screenshot_dir = 'screenshots'
    json_file = 'recetas.json'

    if not os.path.exists(screenshot_dir):
        os.makedirs(screenshot_dir)

    categorias = {
        "vegetariano": {"url": "https://cocinerosargentinos.com/vegetariano", "paginas": 46},
        "guisos_y_sopas": {"url": "https://cocinerosargentinos.com/guisos-y-sopas", "paginas": 40},
        "arroces_y_pastas": {"url": "https://cocinerosargentinos.com/arroces-y-pastas", "paginas": 85},
        "saludables": {"url": "https://cocinerosargentinos.com/saludables", "paginas": 31},
        "apto_celiaco": {"url": "https://cocinerosargentinos.com/apto-celiaco", "paginas": 7}
    }

    all_recipes = load_existing_recipes(json_file)  # Cargar recetas existentes

    try:
        for categoria, datos in categorias.items():
            for pagina in range(1, datos["paginas"] + 1):
                url = f"{datos['url']}?page={pagina}"
                driver.get(url)
                print(f"Scrapeando página {pagina} de la categoría {categoria}")
                      
                recetas_enlaces = wait.until(EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, 'li.item.col-lg-4.col-md-3.col-sm-4.col-xs-6 a:not([data-metrics-container])')))
                
                if not recetas_enlaces:
                    print(f"No se encontraron recetas en la página {pagina}.")
                    continue
                
                recetas_urls = list(set([receta.get_attribute('href') for receta in recetas_enlaces]))

                for receta_url in recetas_urls:
                    driver.get(receta_url)

                    try:
                        nombre = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.product-name h1'))).text
                        ingredientes = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.short-description'))).text
                        procedimiento_html = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.std'))).get_attribute('innerHTML')
                        procedimiento_limpio = clean_procedure(procedimiento_html)

                        if nombre and ingredientes and procedimiento_limpio:
                            receta = {
                                "nombre": nombre,
                                "ingredientes": ingredientes,
                                "procedimiento": procedimiento_limpio
                            }
                            all_recipes.append(receta)
                            print(f"Receta extraída: {nombre}")

                            # Guardar en JSON inmediatamente
                            save_recipe_to_json(receta, json_file)

                            # Guardar en la base de datos
                            insert_receta(nombre, ingredientes, procedimiento_limpio)

                        else:
                            print(f"Receta incompleta en {receta_url}. Saltando.")

                    except Exception as e:
                        print(f"Error al extraer receta: {e}")
                        screenshot_name = f"error_scraping_{categoria}_pagina_{pagina}.png"
                        driver.save_screenshot(os.path.join(screenshot_dir, screenshot_name))
                        print(f"Captura de pantalla guardada: {screenshot_name}")

                    driver.back()
                    wait.until(EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, 'li.item.col-lg-4.col-md-3.col-sm-4.col-xs-6 a:not([data-metrics-container])')))

                recetas_urls.clear()

    except Exception as e:
        print(f"Error durante el scraping: {str(e)}")

    finally:
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(all_recipes, f, ensure_ascii=False, indent=4)
        print(f"Recetas guardadas en {json_file}")

        driver.quit()

    return all_recipes