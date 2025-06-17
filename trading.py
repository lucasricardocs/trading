import streamlit as st
import random

st.set_page_config(page_title="Fagulhas Realistas com Som", layout="wide")

NUM_FAGULHAS = 100

def gerar_fagulhas_css(n):
    css = ""
    for i in range(1, n+1):
        left = random.uniform(2, 98)  # posição horizontal %
        size_w = random.uniform(1.5, 4)  # largura da cauda (px)
        size_h = size_w * random.uniform(6, 12)  # altura da cauda (px)
        duration = random.uniform(4, 9)  # duração da subida (segundos)
        delay = random.uniform(0, 8)  # delay antes de começar (segundos)
        oscillation = random.uniform(15, 40)  # amplitude lateral (px)
        flicker_dur = random.uniform(1.5, 3)  # duração flicker (segundos)
        opacity_start = random.uniform(0.6, 1)

        css += f"""
        .spark:nth-child({i}) {{
            left: {left:.2f}%;
            width: {size_w:.2f}px;
            height: {size_h:.2f}px;
            animation-duration: {duration:.2f}s;
            animation-delay: {delay:.2f}s;
            --oscillation: {oscillation:.2f}px;
            --flicker-duration: {flicker_dur:.2f}s;
            opacity: {opacity_start:.2f};
        }}
        """
    return css

css = f"""
<style>
body {{
    margin: 0;
    background-color: #000;
    overflow: hidden;
    height: 100vh;
}}

.spark {{
    position: fixed;
    bottom: 0;
    border-radius: 50% / 100%;
    background: linear-gradient(to top, rgba(255,255,200,1), rgba(255,255,200,0));
    filter: drop-shadow(0 0 8px rgba(255, 180, 80, 0.9));
    opacity: 0;
    animation-name: rise, flicker, sway;
    animation-timing-function: linear, ease-in-out, ease-in-out;
    animation-iteration-count: infinite, infinite, infinite;
    animation-fill-mode: forwards;
    transform-origin: center bottom;
}}

@keyframes rise {{
    0% {{
        bottom: 0;
        opacity: 1;
        transform: translateX(0) scale(1);
    }}
    80% {{
        opacity: 1;
    }}
    100% {{
        bottom: 110vh;
        opacity: 0;
        transform: translateX(var(--oscillation)) scale(0.4);
    }}
}}

@keyframes flicker {{
    0%, 100% {{
        opacity: 1;
    }}
    50% {{
        opacity: 0.3;
    }}
}}

@keyframes sway {{
    0%, 100% {{
        transform: translateX(calc(var(--oscillation) * 1));
    }}
    50% {{
        transform: translateX(calc(var(--oscillation) * -1));
    }}
}}

{gerar_fagulhas_css(NUM_FAGULHAS)}
</style>
"""

audio_html = """
<audio autoplay loop>
  <source src="https://cdn.pixabay.com/download/audio/2022/03/15/audio_ef3fcd5aab.mp3?filename=fireplace-crackling-11268.mp3" type="audio/mp3">
Seu navegador não suporta áudio.
</audio>
"""

# Renderiza CSS e audio
st.markdown(css, unsafe_allow_html=True)
st.markdown(audio_html, unsafe_allow_html=True)

# Cria as divs das fagulhas
spark_divs = "".join(
    "<div class='spark'></div>" for _ in range(NUM_FAGULHAS)
)
st.markdown(spark_divs, unsafe_allow_html=True)

# Título
st.markdown(
    "<h1 style='text-align: center; color: white; margin-top: 2rem;'>🔥 Fagulhas Realistas Estilo Vídeo + Som Ambiente</h1>",
    unsafe_allow_html=True,
)

st.markdown(
    "<p style='text-align: center; color: white;'>Fagulhas subindo com cauda, brilho intenso, oscilação lateral e som de braseiro.</p>",
    unsafe_allow_html=True,
)

nome = st.text_input("Digite seu nome:")
if nome:
    st.success(f"Bem-vindo, {nome}! 🔥✨ Curta o som do braseiro ao fundo.")
import streamlit as st
import random

st.set_page_config(page_title="Fagulhas Realistas com Som", layout="wide")

# CSS base e dinamico
def gerar_fagulhas(qtd=80):
    fagulhas_css = ""
    for i in range(qtd):
        left = random.randint(0, 100)
        size = random.uniform(2, 4)
        duration = random.uniform(5, 9)
        delay = random.uniform(0, 8)
        shift = random.randint(-60, 60)
        rotation = random.randint(-20, 20)

        fagulhas_css += f"""
        .spark:nth-child({i+1}) {{
            left: {left}%;
            width: {size}px;
            height: {size}px;
            --horizontal-shift: {shift}px;
            --rotation: {rotation}deg;
            animation-duration: {duration:.2f}s, {random.uniform(1,3):.2f}s;
            animation-delay: {delay:.2f}s, {random.uniform(0,2):.2f}s;
        }}
        """

    return fagulhas_css

css = f"""
<style>
body {{
    background-color: #000000;
    overflow: hidden;
}}

.spark {{
    position: fixed;
    bottom: 0;
    background: radial-gradient(circle, rgba(255,255,255,1) 0%, rgba(255,255,255,0) 70%);
    border-radius: 50%;
    opacity: 0;
    filter: blur(1px);
    animation: rise linear infinite, flicker ease-in-out infinite;
    mix-blend-mode: screen;
}}

.spark.long {{
    width: 2px !important;
    height: 10px !important;
    background: linear-gradient(to top, rgba(255,255,255,0.7), rgba(255,255,255,0));
    border-radius: 50%;
    filter: blur(0.8px);
}}

@keyframes rise {{
    0% {{
        transform: translateY(0) translateX(0) scale(1) rotate(0deg);
        opacity: 1;
    }}
    30% {{
        opacity: 1;
    }}
    100% {{
        transform: translateY(-120vh) translateX(var(--horizontal-shift)) scale(0.5) rotate(var(--rotation));
        opacity: 0;
    }}
}}

@keyframes flicker {{
    0%, 100% {{
        opacity: 0.8;
    }}
    50% {{
        opacity: 0.3;
    }}
}}

{gerar_fagulhas(80)}

</style>
"""

audio_html = """
<audio autoplay loop>
  <source src="https://cdn.pixabay.com/download/audio/2022/03/15/audio_ef3fcd5aab.mp3?filename=fireplace-crackling-11268.mp3" type="audio/mp3">
Seu navegador não suporta áudio.
</audio>
"""

# Inserindo CSS e audio
st.markdown(css, unsafe_allow_html=True)
st.markdown(audio_html, unsafe_allow_html=True)

# Criando as fagulhas
spark_divs = "".join([
    f"<div class='spark {'long' if random.random() < 0.3 else ''}'></div>"
    for _ in range(80)
])
st.markdown(spark_divs, unsafe_allow_html=True)

# Título e descrição
st.markdown(
    "<h1 style='text-align: center; color: white;'>🔥 Fagulhas Ultra Realistas + Som</h1>",
    unsafe_allow_html=True,
)

st.markdown(
    "<p style='text-align: center; color: white;'>Fagulhas subindo, glow, blur, brilho intermitente, som ambiente de braseiro. Experiência completa.</p>",
    unsafe_allow_html=True,
)

nome = st.text_input("Digite seu nome:")
if nome:
    st.success(f"Bem-vindo, {nome}! 🔥✨ Curta o som do braseiro ao fundo.")
