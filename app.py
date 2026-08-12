import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import gc

@st.cache_resource
def lae_mudel():
    return easyocr.Reader(['en', 'uk'])

lugeja = lae_mudel()
# Eesti numbrimärgid, sorteeritud numbri järgi. Ukraina märk lõpus.
lubatud = [
    "033XRL",
    "042BMP",
    "070BMY",
    "120PLS",
    "121VZW",
    "142BYG",
    "217BVK",
    "219TNR",
    "264DBK",
    "398MGL",
    "403NDN",
    "507TKK",
    "518BFX",
    "537DCF",
    "567DRA",
    "618JSR",
    "687MBH",
    "803PGB",
    "819MKE",
    "827HHL",
    "912SDL",
    "936DCH",
    "СВ0347СС",
]

st.title("Reg nr kontroll")
st.info("Kui kaamera ei avane, lae numbrimärgist pilt üles.")

# Kaamera
picture = st.camera_input("Pildista numbrimärk")

if picture is not None:
    st.image(picture, caption='Saadud pilt', use_container_width=True)
    
    # Dekodeeri ja töötlusta
    img = Image.open(picture)
    
    with st.spinner('Töötlen pilti...'):
        tulemus = lugeja.readtext(np.array(img), detail=0)
        tuvastatud = "".join(tulemus).replace(" ", "").upper().replace("EST", "").replace("UKR", "")
    
    st.write("Tuvastati:", tuvastatud)
    
    if any(nr in tuvastatud for nr in lubatud):
        st.success("LUBA OLEMAS")
    else:
        st.error("LUBA PUUDUB")
    
    gc.collect()
