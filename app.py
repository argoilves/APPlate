import streamlit as st
import easyocr
import numpy as np
from PIL import Image

@st.cache_resource
def lae_mudel():
    return easyocr.Reader(['en', 'uk'])

lugeja = lae_mudel()
# Enamus on Eesti numbrimärgid, üks neist on Ukraina numbrimärk
lubatud = [
    "618JSR",
    "219TNR",
    "567DRA",
    "217BVK",
    "070BMY",
    "518BFX",
    "142BYG",
    "803PGB",
    "403NDN",
    "507TKK",
    "537DCF",
    "936DCH",
    "120PLS",
    "819MKE",
    "827HHL",
    "042BMP",
    "687MBH",
    "398MGL",
    "СВ0347СС",
    "264DBK",
    "033XRL",
    "912SDL",
    "121VZW",
]

st.title("Reg nr kontroll")
st.info("Kui kaamera ei avane, lae numbrimärgist pilt üles.")

pilt = st.camera_input("Tee numbrimärgist pilt")
if not pilt:
    pilt = st.file_uploader("Või lae pilt üles", type=["png", "jpg", "jpeg"])

if pilt:
    img = Image.open(pilt)
    tulemus = lugeja.readtext(np.array(img), detail=0)
    tuvastatud = "".join(tulemus).replace(" ", "").upper()
    
    st.write("Tuvastati:", tuvastatud)
    
    if any(nr in tuvastatud for nr in lubatud):
        st.success("LUBA OLEMAS")
    else:
        st.error("LUBA PUUDUB")