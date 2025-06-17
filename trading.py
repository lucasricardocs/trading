import streamlit as st
import random

st.set_page_config(page_title="Fagulhas Realistas + Som", layout="wide")

# Função para interpolar cor HSL entre branco quente e vermelho
def interpolate_hsl_color(h1, l1, h2, l2, t):
    # h: hue em graus (0-360)
    # l: lightness em %
    # t: interpolação 0 a 1
    h = h1 + (h2 - h1) * t
    l = l1 + (l2 - l1) * t
    return f"hsl({h:.1f}, 100%, {l:.1f}%)"

# CSS base + animações
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
  animation-name: rise_sway, flicker;
  animation-timing-function: linear, ease-in-out;
  animation-iteration-count: infinite;
  opacity: 0;
  will-change: transform, opacity, background-color;
}

@keyframes rise_sway {
  0% {
    transform: translateY(0) translateX(0) scale(1);
    opacity: 1;
  }
  25% {
    transform: translateY(-27.5vh) translateX(var(--hshift)) scale(0.85);
    opacity: 0.8;
  }
  50% {
    transform: translateY(-55vh) translateX(0) scale(0.6);
    opacity: 0.5;
  }
  75% {
    transform: translateY(-82.5vh) translateX(calc(var(--hshift) * -1)) scale(0.4);
    opacity: 0.3;
  }
  100% {
    transform: translateY(-110vh) translateX(0) scale(0.2);
    opacity: 0;
  }
}

@keyframes flicker {
  0%, 100% {
    opacity: 0.8;
  }
  50% {
    opacity: 0.3;
  }
}
</style>
"""

# Gera CSS dinâmico para cada fagulha individual com cores, tamanhos e tempos variados
def gerar_fagulhas(n=80):
    estilos = ""
    for i in range(n):
        left = random.uniform(0, 100)
        size = random.uniform(8, 20)  # tamanho base no início
        dur_rise = random.uniform(4, 8)
        dur_flicker = random.uniform(1, 3)
        delay = random.uniform(0, 8)
        hshift = random.uniform(-20, 20)  # deslocamento horizontal máximo para sway

        # Cor do branco quente ao vermelho de brasa usando HSL (mais natural)
        cor_interpolada = interpolate_hsl_color(30, 90, 10, 50, random.random())

        estilos += f"""
        .spark:nth-child({i+1}) {{
            left: {left:.2f}%;
            width: {size:.2f}px;
            height: {size:.2f}px;
            --hshift: {hshift:.2f}px;
            --dur-rise: {dur_rise:.2f}s;
            --dur-flicker: {dur_flicker:.2f}s;
            --delay: {delay:.2f}s;
            animation-duration: var(--dur-rise), var(--dur-flicker);
            animation-delay: var(--delay), var(--delay);
            background: radial-gradient(circle, {cor_interpolada} 0%, transparent 70%);
            filter: drop-shadow(0 0 4px {cor_interpolada});
        }}
        """
    return estilos

# HTML completo com CSS, fagulhas e som ambiente
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

# Exibir no Streamlit
st.markdown(html, unsafe_allow_html=True)

# Texto fixo centralizado e estilizado
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
