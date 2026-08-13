import re
from io import BytesIO

import easyocr
import numpy as np
import streamlit as st
from PIL import Image


st.set_page_config(
    page_title="Reg nr kontroll",
    page_icon=":material/license:",
    layout="wide",
)

# Eesti numbrimärgid, sorteeritud numbri järgi. Ukraina märk lõpus.
LUBATUD = {
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
}


@st.cache_resource
def lae_mudel():
    return easyocr.Reader(["en", "uk"])


def puhasta_number(value):
    """Eemalda OCR-i lisatekst ja tagasta kõige tõenäolisem registrinumber."""
    clean = re.sub(r"[^0-9A-ZА-ЯІЇЄ]", "", (value or "").upper())
    clean = clean.replace("EST", "").replace("UKR", "")

    eesti_number = re.search(r"\d{3}[A-Z]{3}", clean)
    if eesti_number:
        return eesti_number.group(0)

    ukraina_number = re.search(r"[А-ЯІЇЄ]{2}\d{4}[А-ЯІЇЄ]{2}", clean)
    if ukraina_number:
        return ukraina_number.group(0)

    return clean[:12]


def loe_number(image_bytes):
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    osad = lae_mudel().readtext(np.array(image), detail=0)
    return puhasta_number("".join(osad))


def pilt_tehtud(camera_key):
    picture = st.session_state.get(camera_key)
    if picture is not None:
        st.session_state.pending_image = picture.getvalue()
        st.session_state.vaade = "tootlemine"


def alusta_algusest():
    st.session_state.vaade = "kaamera"
    st.session_state.pending_image = None
    st.session_state.tuvastatud = ""
    st.session_state.camera_id += 1


st.session_state.setdefault("vaade", "kaamera")
st.session_state.setdefault("pending_image", None)
st.session_state.setdefault("tuvastatud", "")
st.session_state.setdefault("camera_id", 0)


@st.dialog(
    "Kontrolli tulemust",
    width="small",
    dismissible=False,
    icon=":material/license:",
)
def tulemuse_popup():
    number = st.session_state.tuvastatud

    if number:
        st.subheader(number, text_alignment="center")
        if number in LUBATUD:
            st.success("LUBA ON OLEMAS", icon=":material/check_circle:")
        else:
            st.error("LUBA PUUDUB", icon=":material/cancel:")
    else:
        st.warning(
            "Numbrit ei õnnestunud lugeda. Sisesta see käsitsi.",
            icon=":material/edit:",
        )

    st.caption("Vajadusel paranda numbrit ja kontrolli kohe uuesti.")

    with st.form("numbri_kontroll", border=False):
        muudetud_number = st.text_input(
            "Registreerimisnumber",
            key="number_input",
            max_chars=12,
            icon=":material/license:",
        )
        kontrolli = st.form_submit_button(
            "Kontrolli uuesti",
            type="primary",
            icon=":material/search:",
            width="stretch",
        )
        uus = st.form_submit_button(
            "Alusta algusest",
            icon=":material/photo_camera:",
            width="stretch",
        )

    if kontrolli:
        puhastatud = puhasta_number(muudetud_number)
        if not puhastatud:
            st.warning("Sisesta registrinumber.", icon=":material/warning:")
        else:
            st.session_state.tuvastatud = puhastatud
            st.rerun()

    if uus:
        alusta_algusest()
        st.rerun()


if st.session_state.vaade == "kaamera":
    st.title("Reg nr kontroll", text_alignment="center")
    st.caption(
        "Suuna kaamera numbrimärgile ja vajuta pildistamise nuppu.",
        text_alignment="center",
    )

    # Portrait-vaates ulatub kaamera servast servani ja võtab 1/3 ekraani kõrgusest.
    # Pärast klõpsu peidetakse foto ning järgmine rerun avab ainult tulemuse popup'i.
    st.markdown(
        """
        <style>
        @media (orientation: portrait) {
            [data-testid="stCameraInput"] {
                width: 100vw !important;
                margin-left: calc(50% - 50vw) !important;
            }

            [data-testid="stCameraInput"] video {
                width: 100% !important;
                height: 33.333svh !important;
                object-fit: cover !important;
            }

            [data-testid="stCameraInput"] img {
                display: none !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    camera_key = f"kaamera_{st.session_state.camera_id}"
    st.camera_input(
        "Pildista numbrimärk",
        key=camera_key,
        on_change=pilt_tehtud,
        args=(camera_key,),
        label_visibility="collapsed",
        resolution="480p",
        width="stretch",
    )

    # Lae OCR-mudel samal ajal, kui kasutaja kaamerat sihib. Mudel jääb
    # cache_resource abil järgmiste kontrollide jaoks serveri mällu.
    lae_mudel()

elif st.session_state.vaade == "tootlemine":
    st.title("Loen numbrit…", text_alignment="center")
    try:
        with st.spinner("Töötlen pilti…"):
            number = loe_number(st.session_state.pending_image)
    except Exception:
        number = ""
    finally:
        st.session_state.pending_image = None

    st.session_state.tuvastatud = number
    st.session_state.pop("number_input", None)
    st.session_state.number_input = number
    st.session_state.vaade = "tulemus"
    st.rerun()

else:
    st.title("Reg nr kontroll", text_alignment="center")
    tulemuse_popup()
