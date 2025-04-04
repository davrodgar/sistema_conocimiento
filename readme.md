# 🧠 Sistema de Conocimiento para Documentos Empresariales

Este proyecto forma parte del Trabajo Fin de Máster (TFM) del Máster de Ingeniería del Software de la Universidad de Sevilla.  
Tiene como objetivo desarrollar un sistema que procese documentos de texto en diferentes formatos, extraiga conocimiento relevante, lo almacene eficientemente y permita su consulta en lenguaje natural.

## 📚 Módulos del sistema

1. **Ingesta de Documentos**  
   Monitoriza una carpeta para detectar nuevos archivos depositados.

2. **Extracción y Procesamiento del Conocimiento**  
   Utiliza Apache Tika y otras herramientas para extraer texto estructurado desde documentos `.pdf`, `.docx`, `.doc`...

3. **Almacenamiento del Conocimiento**  
   Guarda tanto los documentos originales como el conocimiento extraído de forma estructurada.

4. **Consulta en Lenguaje Natural** *(en desarrollo)*  
   Permite realizar consultas en lenguaje natural sobre el conocimiento almacenado.

5. **Control de Seguridad y Privacidad** *(opcional)*  
   Aplica reglas para proteger información sensible.

6. **Aprendizaje y Mejora Continua** *(en desarrollo)*  
   Utiliza feedback del usuario para mejorar la precisión del sistema.

## 🛠 Requisitos

- Python 3.9+
- Apache Tika corriendo en `localhost:9998`
- Virtualenv (opcional pero recomendado)

## ▶️ Instalación

```bash
# Clonar el repositorio
git clone https://github.com/davrodgar/sistema_conocimiento.git
cd sistema_conocimiento

# Crear y activar entorno virtual
python -m venv venv_TFM2025
# En Windows
venv_TFM2025\Scripts\activate
# En macOS/Linux
source venv_TFM2025/bin/activate

# Instalar dependencias
pip install -r requirements.txt