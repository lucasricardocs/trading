import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Fagulhas Realistas com Canvas", layout="wide")

# HTML + JS para rodar tsParticles (biblioteca de partículas)
html_code = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <title>Fagulhas Realistas</title>
  <style>
    body, html {
      margin: 0; padding: 0; overflow: hidden; background: black; height: 100vh; width: 100vw;
    }
    #tsparticles {
      position: fixed; width: 100%; height: 100%;
    }
  </style>
</head>
<body>
  <div id="tsparticles"></div>

  <!-- tsParticles lib -->
  <script src="https://cdn.jsdelivr.net/npm/tsparticles@2/tsparticles.bundle.min.js"></script>

  <script>
    tsParticles.load("tsparticles", {
      fpsLimit: 60,
      background: {
        color: "#000000",
      },
      particles: {
        number: {
          value: 100,
          density: {
            enable: true,
            area: 800,
          }
        },
        color: {
          value: ["#fffcf2", "#ffd166", "#fca311"]
        },
        shape: {
          type: "circle"
        },
        opacity: {
          value: 0.8,
          random: true,
          anim: {
            enable: true,
            speed: 1,
            opacity_min: 0.3,
            sync: false
          }
        },
        size: {
          value: 2,
          random: { enable: true, minimumValue: 1 },
          anim: {
            enable: true,
            speed: 2,
            size_min: 0.5,
            sync: false
          }
        },
        move: {
          enable: true,
          speed: 3,
          direction: "top",
          random: true,
          straight: false,
          outModes: {
            default: "out"
          },
          attract: {
            enable: false,
          }
        },
        // adiciona efeito de cauda usando trail
        trail: {
          enable: true,
          length: 10,
          fillColor: "#000000"
        },
        rotate: {
          value: 0,
          random: true,
          direction: "random",
          animation: {
            enable: true,
            speed: 15,
            sync: false
          }
        }
      },
      detectRetina: true,
    });
  </script>
</body>
</html>
"""

st.components.v1.html(html_code, height=600, scrolling=False)

st.markdown("""
# 🔥 Fagulhas Ultra Realistas com Canvas + tsParticles  
Som ambiente com fagulhas subindo, com brilho, movimento aleatório e cauda longa.  
""")

# Áudio de som ambiente
audio_html = """
<audio autoplay loop controls style="width: 100%;">
  <source src="https://cdn.pixabay.com/download/audio/2022/03/15/audio_ef3fcd5aab.mp3?filename=fireplace-crackling-11268.mp3" type="audio/mp3">
Seu navegador não suporta áudio.
</audio>
"""
st.markdown(audio_html, unsafe_allow_html=True)
