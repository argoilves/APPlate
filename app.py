import base64
import binascii
import re
from io import BytesIO
from uuid import uuid4

import easyocr
import numpy as np
import streamlit as st
from PIL import Image


st.set_page_config(
    page_title="Reg nr kontroll",
    page_icon=":material/license:",
    layout="wide",
)

st.html(
    """
    <style>
    @media (max-width: 700px) {
        [data-testid="stMainBlockContainer"] {
            padding-top: 3.5rem !important;
            padding-bottom: calc(3rem + env(safe-area-inset-bottom, 0px)) !important;
        }

        [data-testid="stAppViewContainer"] p,
        [data-testid="stDialog"] p {
            font-size: 1.05rem;
            line-height: 1.45;
        }

        [data-testid="stCaptionContainer"] p {
            font-size: 1rem !important;
            line-height: 1.4 !important;
        }

        .st-key-manual_number label p,
        .st-key-number_input label p {
            font-size: 1.1rem !important;
            font-weight: 700 !important;
        }

        .st-key-manual_number input,
        .st-key-number_input input {
            min-height: 3.6rem !important;
            font-size: 1.3rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }

        .st-key-kasitsi_submit button,
        .st-key-popup_submit button,
        .st-key-popup_restart button {
            width: 100% !important;
            min-height: 3.6rem !important;
            font-size: 1.15rem !important;
            font-weight: 700 !important;
        }

        .st-key-kasitsi_submit {
            margin-bottom: max(0.75rem, env(safe-area-inset-bottom, 0px));
        }

        [data-testid="stAlert"] p {
            font-size: 1.15rem !important;
            font-weight: 700 !important;
            line-height: 1.4 !important;
        }

        [data-testid="stDialog"] h2 {
            font-size: 1.65rem !important;
            font-weight: 750 !important;
        }
    }
    </style>
    """
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
        font: 700 1.15rem/1.4 var(--st-font, sans-serif);
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
        min-height: 94px;
        padding: 8px 16px;
        background: linear-gradient(transparent, rgba(0, 0, 0, 0.72));
    }

    button {
        appearance: none;
        border: 0;
        font: 700 1.05rem/1 var(--st-font, sans-serif);
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
        width: 58px;
        height: 58px;
        border: 3px solid white;
        border-radius: 50%;
    }

    .shutter-dot {
        width: 46px;
        height: 46px;
        border-radius: 50%;
        background: white;
    }

    #switch-camera {
        position: absolute;
        right: 18px;
        bottom: 25px;
        width: 50px;
        height: 50px;
        border: 1px solid rgba(255, 255, 255, 0.5);
        border-radius: 50%;
        color: white;
        background: rgba(0, 0, 0, 0.46);
        font-size: 1.8rem;
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


LOATA_AJALUGU = st.components.v2.component(
    "applate_loata_ajalugu",
    html="""
    <section id="history-root" hidden>
        <strong id="history-status"></strong>
        <p id="history-count"></p>
        <ul id="history-list"></ul>
        <button id="history-download" type="button">Laadi ajalugu (.csv)</button>
    </section>
    """,
    css="""
    :host {
        display: block;
        color: var(--st-text-color);
        font-family: var(--st-font);
    }

    #history-root {
        margin: 0.35rem 0 1rem;
        padding: 0.9rem;
        border: 1px solid var(--st-border-color, rgba(49, 51, 63, 0.2));
        border-radius: var(--st-border-radius, 0.75rem);
        background: var(--st-secondary-background-color);
    }

    #history-status {
        display: block;
        font-size: 1.05rem;
        line-height: 1.35;
    }

    #history-count {
        margin: 0.35rem 0 0.45rem;
        font-size: 0.95rem;
        line-height: 1.4;
    }

    #history-list {
        margin: 0 0 0.75rem;
        padding-left: 1.25rem;
        font-size: 0.95rem;
        line-height: 1.45;
    }

    #history-download {
        width: 100%;
        min-height: 3rem;
        padding: 0.65rem 0.9rem;
        border: 0;
        border-radius: var(--st-button-radius, var(--st-border-radius, 0.75rem));
        color: white;
        background: var(--st-primary-color);
        font: inherit;
        font-size: 1rem;
        font-weight: 700;
        cursor: pointer;
    }

    #history-download:disabled {
        cursor: not-allowed;
        opacity: 0.55;
    }
    """,
    js=r"""
    const historyStorageKey = "applate_loata_ajalugu_v1"
    const maxHistoryItems = 1000

    function normalizePlate(value) {
        const clean = String(value ?? "")
            .toUpperCase()
            .replace(/[^0-9A-ZА-ЯІЇЄ]/g, "")

        const estonian = clean.match(/\d{3}[A-Z]{3}/)
        if (estonian) return estonian[0]

        const ukrainian = clean.match(/[А-ЯІЇЄ]{2}\d{4}[А-ЯІЇЄ]{2}/)
        if (ukrainian) return ukrainian[0]

        return clean.slice(0, 12)
    }

    function readHistory() {
        const parsed = JSON.parse(localStorage.getItem(historyStorageKey) || "[]")
        if (!Array.isArray(parsed)) return []

        return parsed
            .map(item => ({
                id: String(item?.id ?? ""),
                number: normalizePlate(item?.number),
                checked_at: String(item?.checked_at ?? ""),
            }))
            .filter(item => item.id && item.number && !Number.isNaN(Date.parse(item.checked_at)))
    }

    function saveHistory(history) {
        localStorage.setItem(historyStorageKey, JSON.stringify(history.slice(-maxHistoryItems)))
    }

    function formatCheckedAt(value) {
        return new Intl.DateTimeFormat("et-EE", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        }).format(new Date(value))
    }

    function historyCsv(history) {
        const dateFormat = new Intl.DateTimeFormat("et-EE", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
        })
        const timeFormat = new Intl.DateTimeFormat("et-EE", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
        })
        const rows = history.map(item => {
            const checkedAt = new Date(item.checked_at)
            return [dateFormat.format(checkedAt), timeFormat.format(checkedAt), item.number].join(";")
        })
        return "\uFEFFKuupäev;Kellaaeg;Registrinumber\n" + rows.join("\n")
    }

    export default function (component) {
        const { data, parentElement } = component
        const root = parentElement.querySelector("#history-root")
        const status = parentElement.querySelector("#history-status")
        const count = parentElement.querySelector("#history-count")
        const list = parentElement.querySelector("#history-list")
        const downloadButton = parentElement.querySelector("#history-download")
        if (!root || !status || !count || !list || !downloadButton) return

        const show = Boolean(data?.show)
        if (parentElement.host) {
            parentElement.host.style.display = show ? "block" : "none"
        }
        root.hidden = !show

        const allowed = new Set((data?.allowed_numbers ?? []).map(normalizePlate))
        const allowedPrefixes = new Set((data?.allowed_prefixes ?? []).map(normalizePlate))
        const deniedNumber = normalizePlate(data?.denied_number)
        const eventId = String(data?.event_id ?? "")
        let history = []
        let storageAvailable = true

        const isAllowed = number => {
            const normalized = normalizePlate(number)
            return allowed.has(normalized) || allowedPrefixes.has(normalized.slice(0, 3))
        }

        try {
            history = readHistory().filter(item => !isAllowed(item.number))
            if (
                deniedNumber
                && eventId
                && !isAllowed(deniedNumber)
                && !history.some(item => item.id === eventId)
            ) {
                history.push({
                    id: eventId,
                    number: deniedNumber,
                    checked_at: new Date().toISOString(),
                })
            }
            history = history.slice(-maxHistoryItems)
            saveHistory(history)
        } catch (_) {
            storageAvailable = false
        }

        if (!show) return

        if (!storageAvailable) {
            status.textContent = "Ajaloo salvestamine pole selles brauseris saadaval."
            count.textContent = "Registrinumbrit ega pilti ei salvestatud."
            list.replaceChildren()
            downloadButton.disabled = true
            return
        }

        status.textContent = deniedNumber
            ? `${deniedNumber} salvestati selle seadme ajalukku.`
            : "Selle seadme loata kontrollide ajalugu."
        count.textContent = `Ajaloos on ${history.length} loata kontrolli.`

        const recentItems = history.slice(-3).reverse()
        list.replaceChildren(...recentItems.map(item => {
            const row = document.createElement("li")
            row.textContent = `${item.number} · ${formatCheckedAt(item.checked_at)}`
            return row
        }))

        downloadButton.disabled = history.length === 0
        downloadButton.onclick = () => {
            const blob = new Blob([historyCsv(history)], { type: "text/csv;charset=utf-8" })
            const url = URL.createObjectURL(blob)
            const link = document.createElement("a")
            const today = new Intl.DateTimeFormat("sv-SE").format(new Date())
            link.href = url
            link.download = `applate_loata_ajalugu_${today}.csv`
            root.appendChild(link)
            link.click()
            link.remove()
            setTimeout(() => URL.revokeObjectURL(url), 0)
        }
    }
    """,
)

def puhasta_number(value):
    """Normaliseeri loendi, OCR-i või käsitsi sisestatud registrinumber."""
    clean = re.sub(r"[^0-9A-ZА-ЯІЇЄ]", "", str(value or "").upper())

    eesti_number = re.search(r"\d{3}[A-Z]{3}", clean)
    if eesti_number:
        return eesti_number.group(0)

    ukraina_number = re.search(r"[А-ЯІЇЄ]{2}\d{4}[А-ЯІЇЄ]{2}", clean)
    if ukraina_number:
        return ukraina_number.group(0)

    return clean[:12]


# Vanad täisnumbrid jäävad alles, et varasemad load töötaksid edasi.
LUBATUD_SISESTUS = {
    "618 JSR",
    "219 TNR",
    "567 DRA",
    "217 BVK",
    "070 BMY",
    "518 BFX",
    "142 BYG",
    "803 PGB",
    "403 NDN",
    "507 TKK",
    "537 DCF",
    "936 DCH",
    "120 PLS",
    "819 MKE",
    "827 HHL",
    "042 BMP",
    "687 MBH",
    "398 MGL",
    "СВ0347СС",
    "264 DBK",
    "033 XRL",
    "912 SDL",
    "121 VZW",
}
LUBATUD = frozenset(map(puhasta_number, LUBATUD_SISESTUS))

# Uuest loendist saadakse ainult registrimärgi kolm esimest märki. Eesti
# numbrimärkidel on need kolm numbrit; AT3 kirje katab sama loogikaga ka
# Ukraina formaadis alguse. Tühikud, sidekriipsud ja tähesuurus ei loe.
LUBATUD_ALGUSTE_SISESTUS = {
    "618",
    "219",
    "567",
    "217",
    "070",
    "518",
    "142",
    "803",
    "403",
    "507",
    "537",
    "936",
    "120",
    "819",
    "827",
    "042",
    "687",
    "398",
    "255",
    "264",
    "033",
    "912",
    "121",
    "084",
    "087",
    "882",
    "793",
    "692",
    "404",
    "937",
    "554",
    "АТ3",
    "AT3",
    "916",
}
LUBATUD_ALGUSED = frozenset(map(puhasta_number, LUBATUD_ALGUSTE_SISESTUS))


def on_lubatud(value):
    """Kontrolli vana täisnumbrit või uue loendi kolme esimest märki."""
    number = puhasta_number(value)
    return bool(number) and (number in LUBATUD or number[:3] in LUBATUD_ALGUSED)


def kuva_loata_ajalugu(*, key, number="", event_id="", show=False):
    """Sünkroniseeri selle brauseri loata kontrollide kohalik ajalugu."""
    return LOATA_AJALUGU(
        key=key,
        data={
            "allowed_numbers": sorted(LUBATUD),
            "allowed_prefixes": sorted(LUBATUD_ALGUSED),
            "denied_number": puhasta_number(number),
            "event_id": event_id,
            "show": show,
        },
        width="stretch",
    )


@st.cache_resource
def lae_mudel():
    return easyocr.Reader(["en", "uk"])


def loe_number(image_bytes):
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    osad = lae_mudel().readtext(np.array(image), detail=0)
    return puhasta_number("".join(osad))


def dekodeeri_kaamerapilt(data_url):
    if not isinstance(data_url, str) or not data_url.startswith("data:image/jpeg;base64,"):
        raise ValueError("Vigane kaamerapildi vorming")

    encoded = data_url.split(",", 1)[1]
    return base64.b64decode(encoded, validate=True)


def sea_tulemus(value):
    """Salvesta uus kontrollitulemus ja anna sellele kordumatu ajaloo ID."""
    number = puhasta_number(value)
    st.session_state.tuvastatud = number
    st.session_state.kontrolli_id = uuid4().hex if number else ""
    return number


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
    st.session_state.kontrolli_id = ""
    st.session_state.camera_error = None
    st.session_state.camera_id += 1


st.session_state.setdefault("vaade", "kaamera")
st.session_state.setdefault("pending_image", None)
st.session_state.setdefault("tuvastatud", "")
st.session_state.setdefault("kontrolli_id", "")
st.session_state.setdefault("camera_id", 0)
st.session_state.setdefault("camera_error", None)
if st.session_state.tuvastatud and not st.session_state.kontrolli_id:
    st.session_state.kontrolli_id = uuid4().hex

# Puhasta ajaloost kõik numbrid, mis on vahepeal lubatud loendisse lisatud.
kuva_loata_ajalugu(key="loata_ajalugu_sync")


@st.dialog(
    "Kontrolli tulemust",
    width="small",
    dismissible=False,
    icon=":material/license:",
)
def tulemuse_popup():
    number = st.session_state.tuvastatud

    if number:
        st.title(number, text_alignment="center")
        if on_lubatud(number):
            st.success("LUBA ON OLEMAS", icon=":material/check_circle:")
        else:
            st.error("LUBA PUUDUB", icon=":material/cancel:")
            kuva_loata_ajalugu(
                key=f"loata_ajalugu_{st.session_state.kontrolli_id}",
                number=number,
                event_id=st.session_state.kontrolli_id,
                show=True,
            )
    else:
        st.warning(
            "Numbrit ei õnnestunud lugeda. Sisesta see käsitsi.",
            icon=":material/edit:",
        )

    st.write("Vajadusel paranda numbrit ja kontrolli kohe uuesti.")

    with st.form("numbri_kontroll", border=False):
        muudetud_number = st.text_input(
            "Registreerimisnumber",
            key="number_input",
            max_chars=12,
            icon=":material/license:",
        )
        kontrolli = st.form_submit_button(
            "Kontrolli uuesti",
            key="popup_submit",
            type="primary",
            icon=":material/search:",
            width="stretch",
        )
        uus = st.form_submit_button(
            "Alusta algusest",
            key="popup_restart",
            icon=":material/photo_camera:",
            width="stretch",
        )

    if kontrolli:
        puhastatud = puhasta_number(muudetud_number)
        if not puhastatud:
            st.warning("Sisesta registrinumber.", icon=":material/warning:")
        else:
            sea_tulemus(puhastatud)
            st.rerun()

    if uus:
        alusta_algusest()
        st.rerun()


if st.session_state.vaade == "kaamera":
    st.title("Reg nr kontroll", text_alignment="center")
    with st.container(horizontal_alignment="center"):
        st.write("Suuna kaamera numbrimärgile ja vajuta pildistamise nuppu.")

    camera_key = f"kaamera_{st.session_state.camera_id}"
    TAGAKAAMERA(
        key=camera_key,
        data={"preferred_facing_mode": "environment"},
        on_captured_change=lambda: pilt_tehtud(camera_key),
        width="stretch",
    )

    if st.session_state.camera_error:
        st.error(st.session_state.camera_error, icon=":material/error:")

    with st.form("kasitsi_kontroll", border=True):
        st.subheader("Kontrolli käsitsi")
        kasitsi_number = st.text_input(
            "Registreerimisnumber",
            key="manual_number",
            max_chars=12,
            placeholder="Näiteks 264DBK",
            autocomplete="off",
            icon=":material/license:",
        )
        kasitsi_submit = st.form_submit_button(
            "Kontrolli",
            key="kasitsi_submit",
            type="primary",
            icon=":material/search:",
            width="stretch",
        )

    if kasitsi_submit:
        puhastatud = puhasta_number(kasitsi_number)
        if not puhastatud:
            st.warning("Sisesta registrinumber.", icon=":material/warning:")
        else:
            sea_tulemus(puhastatud)
            st.session_state.pop("number_input", None)
            st.session_state.number_input = puhastatud
            st.session_state.vaade = "tulemus"
            st.rerun()

elif st.session_state.vaade == "tootlemine":
    st.title("Loen numbrit…", text_alignment="center")
    try:
        with st.spinner("Töötlen pilti…"):
            number = loe_number(st.session_state.pending_image)
    except Exception:
        number = ""
    finally:
        st.session_state.pending_image = None

    number = sea_tulemus(number)
    st.session_state.pop("number_input", None)
    st.session_state.number_input = number
    st.session_state.vaade = "tulemus"
    st.rerun()

else:
    st.title("Reg nr kontroll", text_alignment="center")
    tulemuse_popup()

