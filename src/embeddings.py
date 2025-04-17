import os
import re

# Directorios
PROCESSED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/processed"))
SEGMENTED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/segmented"))

# Crear la carpeta de salida si no existe
if not os.path.exists(SEGMENTED_DIR):
    os.makedirs(SEGMENTED_DIR)

def segmentar_en_parrafos(texto):
    """
    Separa el texto en párrafos usando:
    - Dobles saltos de línea
    - Punto seguido de salto de línea y una mayúscula (inicio de un nuevo párrafo)
    """
    # Normalizar saltos de línea
    texto = re.sub(r'\n+', '\n', texto)  # Reemplazar múltiples saltos por uno solo

    # Separar por dobles saltos de línea o punto seguido de un salto de línea y mayúscula
    parrafos = re.split(r"\n\s*\n|(?<=\.)\n(?=[A-Z])", texto)

    # Filtrar fragmentos muy cortos
    parrafos = [p.strip() for p in parrafos if len(p.strip()) > 30]

    return parrafos

def procesar_archivos_txt():
    """
    Procesa todos los archivos .txt en la carpeta PROCESSED_DIR,
    segmenta su contenido en párrafos y guarda los resultados en SEGMENTED_DIR.
    """
    for archivo in os.listdir(PROCESSED_DIR):
        if archivo.endswith(".txt"):
            ruta_archivo = os.path.join(PROCESSED_DIR, archivo)
            print(f"📂 Procesando archivo: {archivo}")

            # Leer el contenido del archivo
            with open(ruta_archivo, "r", encoding="utf-8") as f:
                texto = f.read()

            # Segmentar el texto en párrafos
            parrafos = segmentar_en_parrafos(texto)

            # Guardar los párrafos segmentados en un nuevo archivo
            archivo_segmentado = os.path.join(SEGMENTED_DIR, archivo)
            with open(archivo_segmentado, "w", encoding="utf-8") as f:
                f.write("\n\n".join(parrafos))

            print(f"✅ Archivo segmentado guardado en: {archivo_segmentado}")

if __name__ == "__main__":
    procesar_archivos_txt()