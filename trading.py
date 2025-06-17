import streamlit as st
import random

st.set_page_config(page_title="Fagulhas Realistas + Som", layout="wide")

# CSS principal com animação das fagulhas
css = """
<style>
html, body {
  margin: 0; padding: 0; height: 100%; width: 100%; overflow: hidden;
  background: radial-gradient(circle at center bottom, #2a1000, #000);
}

.spark {
  position: fixed;
  bottom: 0;
  border-radius: 50%;
  filter: drop-shadow(0 0 6px);
  animation-name: rise, flicker, sway;
  animation-timing-function: linear, ease-in-out, ease-in-out;
  animation-iteration-count: infinite, infinite, infinite;
  opacity: 0;
  will-change: transform, opacity, background-color;
}

/* Subida + diminuição de tamanho */
@keyframes rise {
  0% {
    transform: translateY(0) translateX(0) scale(1);
    opacity: 1;
  }
  100% {
    transform: translateY(-110vh) translateX(var(--hshift)) scale(0.2);
    opacity: 0;
  }
}

/* Piscar do brilho */
@keyframes flicker {
  0%, 100% {
    opacity: 0.8;
  }
  50% {
    opacity: 0.3;
  }
}

/* Oscilação lateral caótica */
@keyframes sway {
  0% {
    transform: translateX(0);
  }
  25% {
    transform: translateX(var(--hshift));
  }
  50% {
    transform: translateX(0);
  }
  75% {
    transform: translateX(calc(var(--hshift) * -1));
  }
  100% {
    transform: translateX(0);
  }
}
</style>
"""

# Gerar as regras CSS para cada fagulha individualmente
def gerar_fagulhas(n=80):
    estilos = ""
    for i in range(n):
        left = random.uniform(0, 100)
        size = random.uniform(8, 20)  # tamanho base no início
        dur_rise = random.uniform(4, 8)
        dur_flicker = random.uniform(1, 3)
        dur_sway = random.uniform(3, 7)
        delay = random.uniform(0, 8)
        hshift = random.uniform(-20, 20)  # deslocamento horizontal máximo para sway

        # Cor do branco ao vermelho (valores intermediários para cores quentes)
        # Vamos criar um gradiente de cor aleatória entre branco e vermelho
        # usando hsl para mais naturalidade:
        # branca: hsl(30, 100%, 90%)
        # vermelha: hsl(10, 100%, 50%)
        # valor interpolado para cada fagulha

        cor_interpolada = interpolate_hsl_color(30, 90, 10, 50, random.random())

        estilos += f"""
        .spark:nth-child({i+1}) {{
            left: {left}%;
            width: {size}px;
            height: {size}px;
            --hshift: {hshift}px;
            animation-duration: {dur_rise}s, {dur_flicker}s, {dur_sway}s;
            animation-delay: {delay}s, {delay}s, {delay}s;
            background: radial-gradient(circle, {cor_interpolada} 0%, transparent 70%);
            filter: drop-shadow(0 0 4px {cor_interpolada});
        }}
        """
    return estilos

def interpolate_hsl_color(h1, l1, h2, l2, t):
    # h: hue em graus (0-360)
    # l: lightness em %
    # t: interpolação 0 a 1
    h = h1 + (h2 - h1) * t
    l = l1 + (l2 - l1) * t
    return f"hsl({h:.1f}, 100%, {l:.1f}%)"

# Gerar o HTML + CSS + fagulhas + áudio
html = f"""
{css}
<style>
{gerar_fagulhas(80)}
</style>

<div>
  {"".join(["<div class='spark'></div>" for _ in range(80)])}
</div>

<audio autoplay loop style="position: fixed; bottom: 15px; left: 15px; z-index: 9999;">
  <source src="https://cdn.pixabay.com/download/audio/2022/03/15/audio_ef3fcd5aab.mp3?filename=fireplace-crackling-11268.mp3" type="audio/mp3">
  Seu navegador não suporta áudio.
</audio>
"""

# Mostrar no Streamlit
st.markdown(html, unsafe_allow_html=True)

# Texto centralizado para título
st.markdown("""
<div style='
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: #ff4500;
  font-size: 3rem;
  font-weight: 900;
  text-shadow: 0 0 15px #ff4500;
  user-select: none;
  pointer-events: none;
'>
🔥 Fagulhas Realistas + Som Ambiente 🔥
</div>
""", unsafe_allow_html=True)
