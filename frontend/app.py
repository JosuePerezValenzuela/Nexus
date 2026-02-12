import os
from typing import cast

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Configuracion
st.set_page_config(page_title="Nexus Health", page_icon="🏥", layout="centered")

# URL del Backend
BACKEND_URL = os.getenv("API_URL", "http://localhost:8000/api/v1/agent/chat")
MODEL_NAME = os.getenv("LLM_MODEL_NAME", "llama-3.1-8b-instant")

st.title("🏥 Nexus Health AI")
st.caption(f"Modelo activo: {MODEL_NAME}")
st.caption("Demo limited to 7 queries/hour, and 10 queries/day")
st.markdown("---")

# Inicializar Historial Visual (Session State)
# Esto es SOLO para que streamlit recurde que pintar en pantalla
if "messages" not in st.session_state:
    st.session_state["messages"] = []

MessageType = dict[str, str]
messages: list[MessageType] = cast(list[MessageType], st.session_state["messages"])

# 2 Pintar mensajes anteriores
for message in messages:
    role = message.get("role", "assistant")
    content = message.get("contetn", "")

    with st.chat_message(role):
        st.markdown(content)

# 3. Input del Usuario
if prompt := st.chat_input("Escribe tu consulta clinica..."):
    # A. Mostrar mensaje del usuario
    user_msg: MessageType = {"role": "user", "content": prompt}
    st.session_state["messages"].append(user_msg)

    with st.chat_message("user"):
        st.markdown(prompt)

    # Llamada al Backend
    with st.chat_message("assistant"):
        with st.spinner("Consultando especialistas..."):
            try:
                # Payload
                payload = {
                    "message": prompt,
                    "thread_id": "demo_session",
                    "model": MODEL_NAME,
                }

                response = requests.post(BACKEND_URL, json=payload)

                if response.status_code == 200:
                    data = response.json()

                    ai_text = data.get("response", str(data))

                    st.markdown(ai_text)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": ai_text}
                    )
                else:
                    error_msg = f"Error {response.status_code}: {response.text}"
                    st.error(error_msg)
            except Exception as e:
                st.error(f"Error de conexion con el backend: {e}")
