from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
from dotenv import load_dotenv
load_dotenv()

def extract_data():
    # 1. Opties instellen
    options = Options()
    options.add_argument('--start-maximized')

    # 2. Driver starten
    driver = webdriver.Chrome(options=options)

    # 3. Website openen
    driver.get('https://webgate.ec.europa.eu/tracesnt/directory/publication/organic-operator/index#!?sort=-issuedOn')

    try:
        wait = WebDriverWait(driver, 10)

        # Stap 1: Klik op "Geavanceerd zoeken"
        geavanceerd_zoeken_knop = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Geavanceerd zoeken')]"))
        )
        geavanceerd_zoeken_knop.click()
        print("✔️ Geavanceerd zoeken geopend.")

        time.sleep(2)

        # Stap 2: Open de dropdown 'Categorieën producten'
        categorie_dropdown = wait.until(
            EC.element_to_be_clickable((By.ID, "categories"))
        )
        categorie_dropdown.click()
        print("✔️ Categorieën dropdown geopend.")

        time.sleep(1)

        # Stap 3: Vink de juiste categorie aan (a) Onverwerkte planten
        categorie_label = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//label[@for='categoryUNPROCESSED_PLANT_PRODUCTS_INCLUDING_SEEDS']"))
        )
        categorie_label.click()
        print("✔️ (a) Categorie 'Onverwerkte planten' succesvol aangevinkt via label.")

        time.sleep(1)

        # Stap 4: Klik op de 'Zoeken' knop
        zoek_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#organicOperatorCertificateListingSearch button[type='submit']"))
        )
        zoek_button.click()
        print("✔️ Zoeken knop geklikt.")

    except Exception as e:
        print(f"⚠️ Fout opgetreden: {e}")

    # 5. Scroll naar beneden om alle resultaten te laden
    SCROLL_PAUSE_TIME = 5
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
        time.sleep(SCROLL_PAUSE_TIME)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    print("Alle data geladen!")

    # 6. HTML ophalen en tabel uitlezen
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    table = soup.find('table', {'id': 'organicOperatorCertificates'})
    rows = table.find('tbody').find_all('tr')

    # 7. Gegevens extraheren
    data = []
    for row in rows:
        columns = row.find_all('td')
        if columns:
            reference = columns[0].text.strip()
            operator = columns[1].text.strip()
            authority = columns[2].text.strip()
            activities = ', '.join([act.text for act in columns[3].find_all('span')])
            categories = ', '.join([cat.text for cat in columns[4].find_all('span')])
            issued_on = columns[5].text.strip()
            expires_on = columns[6].text.strip()
            data.append([reference, operator, authority, activities, categories, issued_on, expires_on])

    # 8. Exporteren naar Excel
    df = pd.DataFrame(data, columns=['Reference', 'Operator', 'Authority', 'Activities', 'Categories', 'Issued On', 'Expires On'])
    print(df)
    out = os.getenv("BIO_CERT_OUT")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    df.to_excel(out, index=False)

    print("✅ Scraping voltooid en opgeslagen als 'organic_certificates.xlsx'!")

    # 9. Browser afsluiten
    driver.quit()


def extract_operator_parts_dynamic(operator_tekst):
    regels_orig = str(operator_tekst).splitlines()
    regels = [r.strip() for r in regels_orig]

    # Posities van lege regels
    empty_indices = [i for i, r in enumerate(regels) if not r.strip()]

    # Zoek land: een niet-lege regel die tussen twee lege regels staat
    land = ""
    land_index = -1
    for i in range(1, len(regels) - 1):
        if regels[i].strip() and i - 1 in empty_indices and i + 1 in empty_indices:
            land = regels[i].strip()
            land_index = i
            break

    # Bedrijfsnaam
    bedrijfsnaam = regels[0].strip() if regels else ""

    # Adres: regels tussen regel 1 en land (exclusief)
    adres = " ".join([r.strip() for i, r in enumerate(regels[1:land_index]) if r.strip()]) if land_index > 1 else ""

    # Groep exploitanten: laatste niet-lege regel
    groep = ""
    for r in reversed(regels):
        if r.strip() not in ("", land, bedrijfsnaam):
            groep = r.strip()
            break

    return pd.Series([bedrijfsnaam, adres, land, groep])
def main():
    extract_data()
    # Pad naar jouw Excelbestand
    bestand = os.getenv("BIO_CERT_OUT")
    df = pd.read_excel(bestand)

    # Verwerk de 'Operator'-kolom
    nieuwe_kolommen = df["Operator"].apply(extract_operator_parts_dynamic)
    nieuwe_kolommen.columns = ["Bedrijfsnaam", "Adres", "Land", "Groep exploitanten"]

    # Combineer met originele DataFrame
    df_clean = pd.concat([df, nieuwe_kolommen], axis=1)

    # Opslaan naar nieuw bestand
    output_pad = os.getenv("BIO_CERT_CLEAN")
    df_clean.to_excel(output_pad, index=False)

    print(f"✔️ Bestand dynamisch opgeschoond en opgeslagen als: {output_pad}")
if __name__ == '__main__':
    main()
