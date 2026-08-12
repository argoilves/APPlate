import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import gc

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

# Kaamera
picture = st.camera_input("Pildista numbrimärk")

if picture is not None:
    st.image(picture, caption='Saadud pilt', use_column_width=True)
    
    # Dekodeeri ja töötlusta
    img = Image.open(picture)
    
    with st.spinner('Töötlen pilti...'):
        tulemus = lugeja.readtext(np.array(img), detail=0)
        tuvastatud = "".join(tulemus).replace(" ", "").upper()
    
    st.write("Tuvastati:", tuvastatud)
    
    if any(nr in tuvastatud for nr in lubatud):
        st.success("LUBA OLEMAS")
    else:
        st.error("LUBA PUUDUB")
    
    gc.collect()
