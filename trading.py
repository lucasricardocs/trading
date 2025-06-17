import streamlit as st
import random

st.set_page_config(page_title="Fagulhas Realistas", layout="wide")

# CSS com aprimoramentos
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

/* Fagulhas alongadas */
.spark.long {
    width: 2px !important;
    height: 10px !important;
    background: linear-gradient(to top, rgba(255,255,255,0.7), rgba(255,255,255,0));
    border-radius: 50%%;
    filter: blur(0.8px);
}

/* Animação de subida */
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

/* Efeito de brilho intermitente */
@keyframes flicker {
    0%%, 100%% {
        opacity: 0.8;
    }
    50%% {
        opacity: 0.3;
    }
}

/* Conteúdo */
.css-18e3th9 {
    background-color: rgba(255, 255, 255, 0.05) !important;
    padding: 2rem;
    border-radius: 10px;
    backdrop-filter: blur(8px);
}
</style>
"""

# Função para gerar CSS das fagulhas
def gerar_fagulhas(qtd=70):
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

# Inserindo CSS dinâmico
st.markdown(css % gerar_fagulhas(80), unsafe_allow_html=True)

# Divs das fagulhas
spark_divs = "".join([
    f"<div class='spark {'long' if random.random() < 0.3 else ''}'></div>"
    for _ in range(80)
])
st.markdown(spark_divs, unsafe_allow_html=True)

# Conteúdo do app
st.markdown(
    "<h1 style='text-align: center; color: white;'>🔥 Fagulhas Ultra Realistas</h1>",
    unsafe_allow_html=True,
)

st.markdown(
    "<p style='text-align: center; color: white;'>Movimento suave, glow, blur, zigue-zague e brilho intermitente, simulando um braseiro perfeito.</p>",
    unsafe_allow_html=True,
)

st.write("💡 Seus inputs, gráficos e funcionalidades podem ser adicionados normalmente.")

nome = st.text_input("Digite seu nome:")
if nome:
    st.success(f"Seja bem-vindo, {nome}! 🔥✨")
