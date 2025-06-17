import streamlit as st
import random

st.set_page_config(page_title="Fagulhas Realistas + Som", layout="wide")

# CSS base + animação das fagulhas com escala, opacidade e brilho relacionados à profundidade
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
  animation-iteration-count: infinite, infinite;
  opacity: 0;
  will-change: transform, opacity, background-color, filter;
  pointer-events: none;
}

/* Animação com subida, movimento lateral caótico, escala e opacidade que simulam profundidade */
@keyframes rise_sway {
  0% {
    transform: translateY(0) translateX(0) scale(1);
    opacity: 1;
    filter: drop-shadow(0 0 8px var(--color));
  }
  20% {
    transform: translateY(-22vh) translateX(calc(var(--hshift) * 0.8)) scale(0.85);
    opacity: 0.85;
    filter: drop-shadow(0 0 6.8px var(--color));
  }
  40% {
    transform: translateY(-44vh) translateX(calc(var(--hshift) * -0.7)) scale(0.65);
    opacity: 0.6;
    filter: drop-shadow(0 0 5px var(--color));
  }
  60% {
    transform: translateY(-66vh) translateX(calc(var(--hshift) * 0.6)) scale(0.4);
    opacity: 0.4;
    filter: drop-shadow(0 0 3px var(--color));
  }
  80% {
    transform: translateY(-88vh) translateX(calc(var(--hshift) * -0.5)) scale(0.25);
    opacity: 0.25;
    filter: drop-shadow(0 0 2px var(--color));
  }
  100% {
    transform: translateY(-110vh) translateX(0) scale(0.1);
    opacity: 0;
    filter: drop-shadow(0 0 1px var(--color));
  }
}

/* Piscar de brilho */
@keyframes flicker {
  0%, 100% {
    opacity: 0.8;
  }
  50% {
    opacity: 0.4;
  }
}

</style>
"""

# Função que gera cor interpolada em HSL do branco quente ao vermelho de brasa
def interpolate_hsl_color(h1, l1, h2, l2, t):
    h = h1 + (h2 - h1) * t
    l = l1 + (l2 - l1) * t
    return f"hsl({h:.1f}, 100%, {l:.1f}%)"

# Gerar regras CSS para as fagulhas individualmente
def gerar_fagulhas(n=80):
    estilos = ""
    for i in range(n):
        left = random.uniform(0, 100)
        size = random.uniform(8, 20)  # tamanho base no início
        dur_rise = random.uniform(4, 8)
        dur_flicker = random.uniform(1, 3)
        delay = random.uniform(0, 8)
        hshift = random.uniform(-40, 40)  # movimento lateral maior
        
        # Interpolação cor: de branco quente (H:30 L:90) para vermelho (H:10 L:50)
        cor = interpolate_hsl_color(30, 90, 10, 50, random.random())
        
        estilos += f"""
        .spark:nth-child({i+1}) {{
            left: {left}%;
            width: {size}px;
            height: {size}px;
            --hshift: {hshift}px;
            --color: {cor};
            animation-duration: {dur_rise}s, {dur_flicker}s;
            animation-delay: {delay}s, {delay}s;
            background: radial-gradient(circle, var(--color) 0%, transparent 70%);
            filter: drop-shadow(0 0 6px var(--color));
        }}
        """
    return estilos

# Montar HTML + CSS + fagulhas + áudio ambiente
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
