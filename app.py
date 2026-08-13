import base64
import binascii
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


TAGAKAAMERA = st.components.v2.component(
    "applate_tagakaamera",
    html="""
    <div id="camera-root">
        <div id="camera-shell">
            <video id="camera-video" autoplay playsinline muted></video>
            <div id="camera-guide" aria-hidden="true"></div>
            <div id="camera-status" role="status">Avan tagakaamerat…</div>
            <div id="camera-controls">
                <button id="switch-camera" type="button" aria-label="Vaheta kaamerat">
                    ↻
                </button>
                <button id="take-photo" type="button" disabled>
                    <span class="shutter-ring"><span class="shutter-dot"></span></span>
                    <span class="button-label">Pildista</span>
                </button>
            </div>
        </div>
    </div>
    """,
    css="""
    :host {
        display: block;
        color: var(--st-text-color);
    }

    #camera-root {
        width: 100%;
    }

    #camera-shell {
        position: relative;
        width: 100%;
        height: min(56.25vw, 520px);
        min-height: 260px;
        overflow: hidden;
        background: #111;
        border-radius: var(--st-border-radius, 0.5rem);
    }

    #camera-video {
        width: 100%;
        height: 100%;
        display: block;
        object-fit: cover;
        background: #111;
    }

    #camera-guide {
        position: absolute;
        left: 12%;
        right: 12%;
        top: 33%;
        height: 30%;
        border: 2px solid rgba(255, 255, 255, 0.86);
        border-radius: 0.5rem;
        box-shadow: 0 0 0 999px rgba(0, 0, 0, 0.14);
        pointer-events: none;
    }

    #camera-status {
        position: absolute;
        inset: 0;
        display: grid;
        place-items: center;
        padding: 1rem;
        color: white;
        text-align: center;
        background: rgba(0, 0, 0, 0.56);
        font: 600 0.95rem/1.35 var(--st-font, sans-serif);
    }

    #camera-status.ready {
        display: none;
    }

    #camera-controls {
        position: absolute;
        z-index: 2;
        left: 0;
        right: 0;
        bottom: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 82px;
        padding: 8px 16px;
        background: linear-gradient(transparent, rgba(0, 0, 0, 0.72));
    }

    button {
        appearance: none;
        border: 0;
        font: 600 0.9rem/1 var(--st-font, sans-serif);
        cursor: pointer;
        touch-action: manipulation;
    }

    button:disabled {
        cursor: wait;
        opacity: 0.55;
    }

    #take-photo {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 4px;
        color: white;
        background: transparent;
    }

    .shutter-ring {
        display: grid;
        place-items: center;
        width: 52px;
        height: 52px;
        border: 3px solid white;
        border-radius: 50%;
    }

    .shutter-dot {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: white;
    }

    #switch-camera {
        position: absolute;
        right: 18px;
        bottom: 23px;
        width: 44px;
        height: 44px;
        border: 1px solid rgba(255, 255, 255, 0.5);
        border-radius: 50%;
        color: white;
        background: rgba(0, 0, 0, 0.46);
        font-size: 1.6rem;
    }

    @media (orientation: portrait) {
        #camera-root {
            width: 100vw;
            margin-left: calc(50% - 50vw);
        }

        #camera-shell {
            width: 100vw;
            height: 33.333svh;
            min-height: 240px;
            border-radius: 0;
        }
    }
    """,
    js="""
    const cameraInstances = new WeakMap()

    function stopStream(instance) {
        if (instance.stream) {
            instance.stream.getTracks().forEach(track => track.stop())
            instance.stream = null
        }
    }

    export default function (component) {
        const { parentElement, setTriggerValue } = component
        const video = parentElement.querySelector("#camera-video")
        const status = parentElement.querySelector("#camera-status")
        const takeButton = parentElement.querySelector("#take-photo")
        const switchButton = parentElement.querySelector("#switch-camera")
        if (!video || !status || !takeButton || !switchButton) return

        let instance = cameraInstances.get(parentElement)
        if (!instance) {
            instance = {
                stream: null,
                facingMode: "environment",
                requestId: 0,
                disposed: false,
            }
            cameraInstances.set(parentElement, instance)
        }

        async function startCamera(facingMode) {
            const requestId = ++instance.requestId
            stopStream(instance)
            takeButton.disabled = true
            status.textContent = facingMode === "environment"
                ? "Avan tagakaamerat…"
                : "Avan esikaamerat…"
            status.classList.remove("ready")

            try {
                let stream
                try {
                    stream = await navigator.mediaDevices.getUserMedia({
                        audio: false,
                        video: {
                            facingMode: { exact: facingMode },
                            width: { ideal: 640 },
                            height: { ideal: 480 },
                        },
                    })
                } catch (strictError) {
                    stream = await navigator.mediaDevices.getUserMedia({
                        audio: false,
                        video: {
                            facingMode: { ideal: facingMode },
                            width: { ideal: 640 },
                            height: { ideal: 480 },
                        },
                    })
                }

                if (instance.disposed || requestId !== instance.requestId) {
                    stream.getTracks().forEach(track => track.stop())
                    return
                }

                instance.stream = stream
                instance.facingMode = facingMode
                video.srcObject = stream
                await video.play()
                status.classList.add("ready")
                takeButton.disabled = false
            } catch (error) {
                stopStream(instance)
                status.textContent = error?.name === "NotAllowedError"
                    ? "Luba brauseris kaamera kasutamine."
                    : "Kaamerat ei õnnestunud avada."
            }
        }

        takeButton.onclick = () => {
            if (!instance.stream || !video.videoWidth || !video.videoHeight) return

            takeButton.disabled = true
            status.textContent = "Saadan kontrolli…"
            status.classList.remove("ready")

            const scale = Math.min(1, 480 / video.videoHeight)
            const canvas = document.createElement("canvas")
            canvas.width = Math.max(1, Math.round(video.videoWidth * scale))
            canvas.height = Math.max(1, Math.round(video.videoHeight * scale))
            const context = canvas.getContext("2d", { alpha: false })
            context.drawImage(video, 0, 0, canvas.width, canvas.height)
            const jpeg = canvas.toDataURL("image/jpeg", 0.82)

            video.srcObject = null
            stopStream(instance)
            canvas.width = 1
            canvas.height = 1
            setTriggerValue("captured", jpeg)
        }

        switchButton.onclick = () => {
            const nextFacingMode = instance.facingMode === "environment"
                ? "user"
                : "environment"
            startCamera(nextFacingMode)
        }

        startCamera("environment")

        return () => {
            instance.disposed = true
            instance.requestId += 1
            video.srcObject = null
            stopStream(instance)
            cameraInstances.delete(parentElement)
        }
    }
    """,
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


def dekodeeri_kaamerapilt(data_url):
    if not isinstance(data_url, str) or not data_url.startswith("data:image/jpeg;base64,"):
        raise ValueError("Vigane kaamerapildi vorming")

    encoded = data_url.split(",", 1)[1]
    return base64.b64decode(encoded, validate=True)


def pilt_tehtud(camera_key):
    component_state = st.session_state.get(camera_key)
    captured = getattr(component_state, "captured", None)
    if captured is None and isinstance(component_state, dict):
        captured = component_state.get("captured")

    if captured:
        try:
            st.session_state.pending_image = dekodeeri_kaamerapilt(captured)
        except (ValueError, binascii.Error):
            st.session_state.pending_image = None
            st.session_state.camera_error = "Pildi saatmine ebaõnnestus. Proovi uuesti."
            return

        st.session_state.camera_error = None
        st.session_state.vaade = "tootlemine"


def alusta_algusest():
    st.session_state.vaade = "kaamera"
    st.session_state.pending_image = None
    st.session_state.tuvastatud = ""
    st.session_state.camera_error = None
    st.session_state.camera_id += 1


st.session_state.setdefault("vaade", "kaamera")
st.session_state.setdefault("pending_image", None)
st.session_state.setdefault("tuvastatud", "")
st.session_state.setdefault("camera_id", 0)
st.session_state.setdefault("camera_error", None)


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

    camera_key = f"kaamera_{st.session_state.camera_id}"
    TAGAKAAMERA(
        key=camera_key,
        data={"preferred_facing_mode": "environment"},
        on_captured_change=lambda: pilt_tehtud(camera_key),
        width="stretch",
    )

    if st.session_state.camera_error:
        st.error(st.session_state.camera_error, icon=":material/error:")

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
