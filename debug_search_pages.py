"""
debug_search_pages.py — ¿Qué devuelven las páginas de búsqueda?
Ejecutar desde la raíz: python debug_search_pages.py
"""
from urllib.parse import quote_plus
from scraper import DomainScraper

scraper = DomainScraper()
headers = {"User-Agent": "NeuroMedIR-CorpusBuilder/2.0"}

q = quote_plus("sarna")

urls = {
    "MSD ES search": f"https://www.msdmanuals.com/es/hogar/searchresults?query={q}",
    "MedlinePlus ES search": f"https://medlineplus.gov/spanish/search/?query={q}",
}

for name, url in urls.items():
    print("\n" + "=" * 70)
    print(f"{name}")
    print(f"URL: {url}")
    print("=" * 70)
    resp = scraper.fetch(url, headers=headers)
    if resp is None:
        print("  fetch FALLÓ (None)")
        continue
    print(f"  status: {resp.status_code}")
    print(f"  content-type: {resp.headers.get('Content-Type', '?')}")
    html = resp.content
    print(f"  HTML length: {len(html)} bytes")

    # Extraer enlaces y ver cuántos parecen artículos vs navegación
    links = scraper.extract_links(html, base_url=url)
    print(f"  total enlaces extraídos: {len(links)}")

    # Filtrar enlaces que mencionen sarna o escabiosis
    sarna_links = [l for l in links if "sarna" in l.lower() or "escabiosis" in l.lower()
                   or "scabies" in l.lower()]
    print(f"  enlaces que mencionan sarna/escabiosis: {len(sarna_links)}")
    for l in sarna_links[:10]:
        print(f"     {l}")

    # Ver una muestra de los primeros 15 enlaces para entender la estructura
    print(f"  muestra de primeros 15 enlaces:")
    for l in links[:15]:
        print(f"     {l}")