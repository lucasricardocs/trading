import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Background Vídeo Fullscreen", layout="wide")

video_url = "https://media.istockphoto.com/id/956854910/pt/v%C3%ADdeo/flying-glowing-fire-sparks-with-an-black-background.mp4?s=mp4-640x640-is&k=20&c=gZcBFbSQPpXe1M8jJQYjokYW0zE-uIrFrgGhb52b6hI="

html_code = f"""
<style>
  /* Vídeo full screen, fixo no fundo */
  #bg-video {{
    position: fixed;
    top: 0; left: 0;
    width: 100vw;
    height: 100vh;
    object-fit: cover;
    z-index: -1;
    pointer-events: none; /* deixa clicar através do vídeo */
  }}

  /* Conteúdo do Streamlit com fundo transparente */
  .stApp {{
    background: transparent !important;
  }}

  /* Opcional: para texto ficar legível */
  .content {{
    position: relative;
    z-index: 1;
    color: white;
    padding: 2rem;
    text-align: center;
    text-shadow: 0 0 8px rgba(0,0,0,0.9);
  }}
</style>

<video autoplay muted loop playsinline id="bg-video">
  <source src="{video_url}" type="video/mp4" />
  Seu navegador não suporta vídeo.
</video>

<div class="content">
  <h1>🔥 Fagulhas Realistas Fullscreen</h1>
  <p>Vídeo de fagulhas animadas como background, adaptável a qualquer tela.</p>
</div>
"""

components.html(html_code, height=600, scrolling=False)
