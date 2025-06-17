import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import time

st.set_page_config(page_title="Fagulhas Realistas + Som", layout="wide")

# Número de fagulhas
NUM_PARTICLES = 80

# Inicialização das partículas
x = np.random.uniform(0, 1, NUM_PARTICLES)
y = np.random.uniform(0, 0.05, NUM_PARTICLES)
size = np.random.uniform(50, 100, NUM_PARTICLES)
alpha = np.ones(NUM_PARTICLES)
vx = np.random.uniform(-0.002, 0.002, NUM_PARTICLES)  # oscilação horizontal
vy = np.random.uniform(0.004, 0.01, NUM_PARTICLES)    # velocidade vertical

# Som ambiente do braseiro
audio_html = """
<audio autoplay loop controls style="width:100%;">
  <source src="https://cdn.pixabay.com/download/audio/2022/03/15/audio_ef3fcd5aab.mp3?filename=fireplace-crackling-11268.mp3" type="audio/mp3">
  Seu navegador não suporta áudio.
</audio>
"""

st.markdown(audio_html, unsafe_allow_html=True)

# Criar figura matplotlib full screen (streamlit limita um pouco, mas deixamos grande)
fig, ax = plt.subplots(figsize=(12, 8))
fig.patch.set_facecolor('black')
ax.set_facecolor('black')
ax.axis('off')

placeholder = st.empty()

st.markdown("<h2 style='color: orange; text-align: center;'>🔥 Fagulhas Realistas com Som de Braseiro 🔥</h2>", unsafe_allow_html=True)

# Loop da animação
for _ in range(1000):
    ax.clear()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    # Atualiza posição das partículas
    x += vx
    y += vy

    # Diminui tamanho e opacidade com a altura para simular afastamento
    size = np.interp(y, [0, 1], [100, 10])
    alpha = np.interp(y, [0, 1], [1, 0])

    # Oscilação lateral caótica
    vx += np.random.uniform(-0.0005, 0.0005, NUM_PARTICLES)
    vx = np.clip(vx, -0.004, 0.004)

    # Reiniciar partículas que saíram da tela
    fora = y > 1
    y[fora] = 0
    x[fora] = np.random.uniform(0, 1, fora.sum())
    vx[fora] = np.random.uniform(-0.002, 0.002, fora.sum())
    vy[fora] = np.random.uniform(0.004, 0.01, fora.sum())
    size[fora] = np.random.uniform(50, 100, fora.sum())
    alpha[fora] = 1

    # Desenhar partículas com cores entre amarelo e laranja, para mais realismo
    for i in range(NUM_PARTICLES):
        color = (1.0, np.random.uniform(0.4, 0.7), 0)  # rgb amarelo-laranja variável
        ax.scatter(x[i], y[i], s=size[i], c=[color], alpha=alpha[i], edgecolors='none')

    placeholder.pyplot(fig)
    time.sleep(0.03)
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
