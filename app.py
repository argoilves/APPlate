import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import io
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

# Visuaalne juhend: pikk ristkülik, mis aitab numbrimärgi joondada
st.markdown(
    """
    <style>
    .plate-guide {display:flex;justify-content:center;margin-bottom:8px;}
    .plate-box {
      width:80%;
      aspect-ratio:4/1;
      border:3px dashed #4CAF50;
      border-radius:6px;
      box-shadow: 0 0 0 1000px rgba(0,0,0,0.25) inset;
      background: rgba(0,0,0,0.0);
    }
    .guide-text {text-align:center;color:#666;font-size:14px;margin-bottom:10px;}
    @media(max-width:600px){ .plate-box{width:94%;} }
    </style>
    <div class="guide-text">Aseta numbrimärk rohelise raamiga kasti. Hoia kaugust ~1–2 m, ära liigu liiga lähedale.</div>
    <div class="plate-guide"><div class="plate-box"></div></div>
    """,
    unsafe_allow_html=True,
)

pilt = st.camera_input("Tee numbrimärgist pilt")
if not pilt:
    pilt = st.file_uploader("Või lae pilt üles", type=["png", "jpg", "jpeg"])

if pilt:
    # Loe pildi baitid (sobib nii camera_input kui file_uploader puhul)
    data = pilt.read()
    size = len(data)
    max_bytes = 2 * 1024 * 1024  # 2 MB

    if size > max_bytes:
        st.error(f"Fail liiga suur ({size/1024:.0f} KB). Maksimaalne lubatud suurus on 2 MB.")
    else:
        try:
            img = Image.open(io.BytesIO(data))
            tulemus = lugeja.readtext(np.array(img), detail=0)
            tuvastatud = "".join(tulemus).replace(" ", "").upper()

            st.write("Tuvastati:", tuvastatud)

            if any(nr in tuvastatud for nr in lubatud):
                st.success("LUBA OLEMAS")
            else:
                st.error("LUBA PUUDUB")
        finally:
            # Sulgeme ja kustutame üleslaaditud puhverid ning puhastame mälust viited
            try:
                pilt.close()
            except Exception:
                pass
            try:
                del data
            except Exception:
                pass
            try:
                del img
            except Exception:
                pass
            try:
                del tulemus
            except Exception:
                pass
            try:
                del tuvastatud
            except Exception:
                pass
            pilt = None
            gc.collect()
