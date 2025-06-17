import streamlit as st
import random

st.set_page_config(page_title="Fagulhas Realistas", layout="wide")

# CSS com partículas aprimoradas
css = """
<style>
body {
    background-color: #000000;
    overflow: hidden;
}

.spark {
    position: fixed;
    bottom: 0;
    background: rgba(255, 255, 255, 0.8);
    border-radius: 50%%;
    opacity: 0;
    filter: blur(1px);
    animation: rise linear infinite;
}

/* Fagulhas alongadas */
.spark.long {
    border-radius: 50%%;
    width: 1px !important;
    height: 8px !important;
    transform: rotate(10deg);
    background: rgba(255, 255, 255, 0.6);
    filter: blur(0.8px);
}

%s

@keyframes rise {
    0%% {
        transform: translateY(0) translateX(0) scale(1);
        opacity: 1;
    }
    50%% {
        opacity: 1;
    }
    100%% {
        transform: translateY(-120vh) translateX(var(--horizontal-shift)) scale(0.5);
        opacity: 0;
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

# Função que gera fagulhas
def gerar_fagulhas(qtd=60):
    fagulhas = ""
    for i in range(qtd):
        left = random.randint(0, 100)  # posição na base
        size = random.uniform(2, 4)    # tamanho base
        duration = random.uniform(4, 8)  # duração da subida
        delay = random.uniform(0, 8)    # atraso inicial
        shift = random.randint(-50, 50) # deslocamento lateral

        # Decide se é uma fagulha normal ou alongada (30% chance)
        long_class = "long" if random.random() < 0.3 else ""

        fagulhas += f"""
        .spark:nth-child({i+1}) {{
            left: {left}%;
            width: {size}px;
            height: {size}px;
            --horizontal-shift: {shift}px;
            animation-duration: {duration}s;
            animation-delay: {delay}s;
        }}
        .spark.long:nth-child({i+1}) {{
            left: {left}%;
            --horizontal-shift: {shift}px;
            animation-duration: {duration}s;
            animation-delay: {delay}s;
        }}
        """
    return fagulhas

# Inserindo CSS dinâmico
st.markdown(css % gerar_fagulhas(70), unsafe_allow_html=True)

# Criando divs das fagulhas
spark_divs = "".join([
    f"<div class='spark {'long' if random.random() < 0.3 else ''}'></div>"
    for _ in range(70)
])
st.markdown(spark_divs, unsafe_allow_html=True)

# Conteúdo do app
st.markdown(
    "<h1 style='text-align: center; color: white;'>🔥 Fagulhas Realistas</h1>",
    unsafe_allow_html=True,
)

st.markdown(
    "<p style='text-align: center; color: white;'>Simulando fagulhas subindo de um braseiro, com movimento e blur suave.</p>",
    unsafe_allow_html=True,
)

st.write("💡 Insira seus inputs, gráficos e interações aqui.")

nome = st.text_input("Digite seu nome:")
if nome:
    st.success(f"Olá, {nome}! 🔥✨")
