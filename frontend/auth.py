import streamlit as st


def save_token(token: str):
    st.session_state["token"] = token


def get_token():
    return st.session_state.get("token")


def logout():
    st.session_state.clear()


def is_logged_in():
    return "token" in st.session_state

def get_token():
    return st.session_state.get("token")