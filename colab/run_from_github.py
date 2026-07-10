"""
Runner simple para Google Colab.

Uso recomendado en una celda de Colab:

!git clone https://github.com/paulguarnizbravo06-tech/Plataforma-BI-Precios-Lima.git
%cd Plataforma-BI-Precios-Lima
!pip install -r requirements.txt

Luego usa Streamlit Community Cloud para la web.
Colab queda como entorno de analitica/ejecucion que llama el codigo desde GitHub.
"""

REPO_URL = "https://github.com/paulguarnizbravo06-tech/Plataforma-BI-Precios-Lima.git"
STREAMLIT_ENTRYPOINT = "streamlit_app.py"

print("Repositorio:", REPO_URL)
print("App web Streamlit:", STREAMLIT_ENTRYPOINT)
print("En produccion, publica streamlit_app.py desde Streamlit Community Cloud.")
