import streamlit as st

# CSS para efeito de fundo com partículas claras (fagulhas)
css = """
<style>
body {
    background-color: #000000;
    overflow: hidden;
}

/* Criando partículas */
.particle {
    position: fixed;
    border-radius: 50%;
    background-color: rgba(255, 255, 255, 0.8);
    animation: move 10s linear infinite;
}

/* Definindo múltiplas partículas */
.particle:nth-child(1) {
    width: 2px;
    height: 2px;
    top: 10%;
    left: 20%;
    animation-duration: 12s;
}
.particle:nth-child(2) {
    width: 3px;
    height: 3px;
    top: 40%;
    left: 70%;
    animation-duration: 8s;
}
.particle:nth-child(3) {
    width: 2px;
    height: 2px;
    top: 60%;
    left: 30%;
    animation-duration: 10s;
}
.particle:nth-child(4) {
    width: 4px;
    height: 4px;
    top: 80%;
    left: 80%;
    animation-duration: 14s;
}
.particle:nth-child(5) {
    width: 3px;
    height: 3px;
    top: 50%;
    left: 50%;
    animation-duration: 9s;
}

/* Movimento das partículas (subindo) */
@keyframes move {
    0% {
        transform: translateY(0) scale(1);
        opacity: 1;
    }
    100% {
        transform: translateY(-100vh) scale(0.5);
        opacity: 0;
    }
}

/* Caixa de conteúdo com efeito vidro */
.css-18e3th9 {
    background-color: rgba(255, 255, 255, 0.05) !important;
    padding: 2rem;
    border-radius: 10px;
    backdrop-filter: blur(8px);
}
</style>

<!-- Criando as partículas -->
<div class="particle"></div>
<div class="particle"></div>
<div class="particle"></div>
<div class="particle"></div>
<div class="particle"></div>
"""

st.markdown(css, unsafe_allow_html=True)

# Conteúdo do app
st.markdown(
    "<h1 style='text-align: center; color: white;'>✨ App com Fagulhas Claras</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align: center; color: white;'>Background escuro com partículas brancas animadas.</p>",
    unsafe_allow_html=True,
)

st.write("💡 Adicione aqui os elementos do seu app normalmente.")

# Exemplo de interação
nome = st.text_input("Digite seu nome:")
if nome:
    st.success(f"Olá, {nome}! 🚀")
