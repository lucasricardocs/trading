import streamlit as st
import random

st.set_page_config(page_title="Fagulhas Realistas com Som", layout="wide")

# CSS para efeito visual
css = """
<style>
body {
    background-color: #000000;
    overflow: hidden;
}

.spark {
    position: fixed;
    bottom: 0;
    background: radial-gradient(circle, rgba(255,255,255,1) 0%%, rgba(255,255,255,0) 70%%);
    border-radius: 50%%;
    opacity: 0;
    filter: blur(1px);
    animation: rise linear infinite, flicker ease-in-out infinite;
    mix-blend-mode: screen;
}

.spark.long {
    width: 2px !important;
    height: 10px !important;
    background: linear-gradient(to top, rgba(255,255,255,0.7), rgba(255,255,255,0));
    border-radius: 50%%;
    filter: blur(0.8px);
}

@keyframes rise {
    0%% {
        transform: translateY(0) translateX(0) scale(1) rotate(0deg);
        opacity: 1;
    }
    30%% {
        opacity: 1;
    }
    100%% {
        transform: translateY(-120vh) translateX(var(--horizontal-shift)) scale(0.5) rotate(var(--rotation));
        opacity: 0;
    }
}

@keyframes flicker {
    0%%, 100%% {
        opacity: 0.8;
    }
    50%% {
        opacity: 0.3;
    }
}

.css-18e3th9 {
    background-color: rgba(255, 255, 255, 0.05) !important;
    padding: 2rem;
    border-radius: 10px;
    backdrop-filter: blur(8px);
}
</style>
"""

# 🎵 Código HTML para som ambiente
audio_html = """
<audio autoplay loop>
  <source src="https://cdn.pixabay.com/download/audio/2022/03/15/audio_ef3fcd5aab.mp3?filename=fireplace-crackling-11268.mp3" type="audio/mp3">
Seu navegador não suporta áudio.
</audio>
"""

def gerar_fagulhas(qtd=80):
    fagulhas = ""
    for i in range(qtd):
        left = random.randint(0, 100)
        size = random.uniform(2, 4)
        duration = random.uniform(5, 9)
        delay = random.uniform(0, 8)
        shift = random.randint(-60, 60)
        rotation = random.randint(-20, 20)

        long_class = "long" if random.random() < 0.3 else ""

        fagulhas += f"""
        .spark:nth-child({i+1}) {{
            left: {left}%;
            width: {size}px;
            height: {size}px;
            --horizontal-shift: {shift}px;
            --rotation: {rotation}deg;
            animation-duration: {duration}s, {random.uniform(1,3)}s;
            animation-delay: {delay}s, {random.uniform(0,2)}s;
        }}
        .spark.long:nth-child({i+1}) {{
            left: {left}%;
            --horizontal-shift: {shift}px;
            --rotation: {rotation}deg;
            animation-duration: {duration}s, {random.uniform(1,3)}s;
            animation-delay: {delay}s, {random.uniform(0,2)}s;
        }}
        """
    return fagulhas

# 🔥 Inserindo CSS + som
st.markdown(css + "<style>" + gerar_fagulhas(80) + "</style>", unsafe_allow_html=True)
st.markdown(audio_html, unsafe_allow_html=True)

# 🔥 Criando fagulhas
spark_divs = "".join([
    f"<div class='spark {'long' if random.random() < 0.3 else ''}'></div>"
    for _ in range(80)
])
st.markdown(spark_divs, unsafe_allow_html=True)

st.markdown(
    "<h1 style='text-align: center; color: white;'>🔥 Fagulhas Ultra Realistas + Som</h1>",
    unsafe_allow_html=True,
)

st.markdown(
    "<p style='text-align: center; color: white;'>Fagulhas subindo, glow, blur, brilho intermitente, som ambiente de braseiro. Experiência completa.</p>",
    unsafe_allow_html=True,
)

st.write("💡 Aqui você pode inserir suas funções, inputs, gráficos ou qualquer outro conteúdo.")

nome = st.text_input("Digite seu nome:")
if nome:
    st.success(f"Bem-vindo, {nome}! 🔥✨ Curta o som do braseiro ao fundo.")
