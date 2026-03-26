import os
from crawler.crawler import Crawler

def main():
    # Establecer punto de partida (Seed)
    # Recomendación: MedlinePlus Topics o Enciclopedia
    seed_urls = [
        "https://medlineplus.gov/healthtopics.html",          # Inglés
        "https://medlineplus.gov/spanish/healthtopics.html",  # Español
        "https://pubmed.ncbi.nlm.nih.gov/trending/",          # PubMed Trending (Inglés)
        "https://www.who.int/es/health-topics"                # OMS (Español)
    ]
    
    # Inicializar crawler con valores recomendados para pruebas
    my_crawler = Crawler(
        seed_urls=seed_urls,
        max_pages=20,         # Aumentamos para probar las 4 fuentes
        max_depth=2,          # Profundidad de navegación
        delay_seconds=1.5,    # 1.5s entre peticiones (respeta el delay=1 de PubMed)
        user_agent="NeuroMedIR-Crawler/1.0"
    )
    
    # Asegúrate de ejecutar esto situándote en la carpeta NeuroMedIR
    print("Iniciando crawling de prueba con fuentes bilingües...")
    my_crawler.start()
    print("Test completado. Revisa la carpeta 'data/processed'.")

if __name__ == "__main__":
    main()
