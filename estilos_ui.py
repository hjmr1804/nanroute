"""
estilos_ui.py — Identidad visual de la app (colores y tipografía de la imagen).

Uso: en app.py, justo después de st.set_page_config(...):
    from estilos_ui import aplicar_estilos
    aplicar_estilos()
"""
import streamlit as st

CREMA = "#FDFBDB"
BLANCO = "#FFFFFF"
AZUL = "#E3EEFF"
NEGRO = "#111111"
GRIS = "#4B4B4B"


def aplicar_estilos():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Poppins:wght@600;700;800&display=swap');

    html, body, [class*="css"], .stMarkdown, p, label, div {{
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
        color: {GRIS};
    }}
    h1, h2, h3 {{
        font-family: 'Poppins', 'Inter', sans-serif;
        font-weight: 800; letter-spacing: -0.02em; color: {NEGRO};
    }}

    /* barra lateral en crema */
    section[data-testid="stSidebar"] {{ background: {CREMA}; }}

    /* botones negros tipo píldora */
    .stButton > button, .stDownloadButton > button {{
        background: {NEGRO}; color: {BLANCO}; border: 0; border-radius: 999px;
        padding: 0.5rem 1.4rem; font-weight: 600;
    }}
    .stButton > button:hover, .stDownloadButton > button:hover {{
        background: #333; color: {BLANCO};
    }}

    /* tarjetas de métricas en azul pálido */
    div[data-testid="stMetric"] {{
        background: {AZUL}; border-radius: 14px; padding: 14px 16px;
    }}
    div[data-testid="stMetric"] * {{ color: {NEGRO}; }}

    /* etiqueta "eyebrow" opcional: usa st.markdown('<span class="eyebrow">01 Entregas</span>') */
    .eyebrow {{
        font-size: 12px; letter-spacing: .14em; text-transform: uppercase;
        color: {GRIS}; font-weight: 600;
    }}

    /* crédito del propietario, fijo en la esquina inferior derecha */
    .credito {{
        position: fixed; bottom: 8px; right: 14px; z-index: 1000;
        font-size: 12px; font-weight: 600; color: {GRIS};
        background: rgba(255,255,255,.75); padding: 2px 8px; border-radius: 10px;
    }}
    </style>
    """, unsafe_allow_html=True)
