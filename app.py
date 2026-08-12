import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import io
import gc
import base64

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

# Näitame ainult ühte kaamera vaadet (allpool) — palun kasuta seda raamiga joondamiseks.

# Muutujad
pilt = None

# Custom in-page camera with overlay (uses getUserMedia). Captured image is automatically downloaded;
# then upload the downloaded image below using "Või lae pilt üles".
import streamlit.components.v1 as components

html = """
<div style="width:100%;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:flex-start;margin:0;padding:0;">
  <video id="video" autoplay playsinline style="width:100%;height:auto;max-height:33vh;border:none;display:block;"></video>
  <div style="margin-top:12px">
    <button id="capture" style="padding:12px 24px;background:#2196F3;border:none;color:white;border-radius:8px;font-size:18px">Pildista</button>
  </div>
  <div id="msg" style="margin-top:8px;color:#666;font-size:13px">Aseta numbrimärk raami sisse ja vajuta "Pildista".</div>
</div>
<script>
const video = document.getElementById('video');
const captureBtn = document.getElementById('capture');
let stream=null;
async function start(){
  try{
    stream = await navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'}});
    video.srcObject = stream;
  }catch(e){
    document.getElementById('msg').innerText = 'Kaamera ei ole kättesaadav.';
  }
}
start();

function sendImageDataUrl(dataUrl){
  window.parent.postMessage({isStreamlitMessage: true, type: 'streamlit:setComponentValue', value: dataUrl}, '*');
}

async function doCapture(){
  const canvas = document.createElement('canvas');
  const w = video.videoWidth;
  const h = video.videoHeight;
  const targetRatio = 4/1;
  let cw = w, ch = Math.round(w/targetRatio);
  if(ch > h){ ch = h; cw = Math.round(h*targetRatio); }
  const sx = Math.round((w - cw)/2);
  const sy = Math.round((h - ch)/2);
  canvas.width = cw; canvas.height = ch;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, sx, sy, cw, ch, 0, 0, cw, ch);
  const dataUrl = canvas.toDataURL('image/png');
  sendImageDataUrl(dataUrl);
  document.getElementById('msg').innerText = 'Pilt saadetud kontrolliks...';
}

captureBtn.onclick = doCapture;
</script>
"""

result = components.html(html, height=520)

# Normalize the returned value from the component
raw = result
st.write("DEBUG: result type =", type(raw), "value starts with =", str(raw)[:80] if raw else "None")

if isinstance(raw, (list, tuple)) and len(raw) > 0:
    raw = raw[0]
if isinstance(raw, dict):
    raw = raw.get('value', raw)
if isinstance(raw, bytes):
    try:
        raw = raw.decode('utf-8')
    except Exception:
        raw = str(raw)

data_url = None
raw_str = str(raw) if raw is not None else ""
st.write("DEBUG: after normalization, raw_str starts with =", raw_str[:80] if raw_str else "empty")

if 'data:image' in raw_str:
    idx = raw_str.find('data:image')
    data_url = raw_str[idx:]

if data_url:
    st.info('Pilt vastu võetud, töötlen...')
    with st.spinner('Töötlen pilti...'):
        try:
            header, b64 = data_url.split(',', 1)
            data = base64.b64decode(b64)
        except Exception:
            st.error('Pildi dekodeerimine ebaõnnestus. Proovi uuesti.')
            data = None

        if data is not None:
            size = len(data)
            max_bytes = 2 * 1024 * 1024  # 2 MB
            if size > max_bytes:
                st.error(f"Pilt liiga suur ({size/1024:.0f} KB). Maksimaalne lubatud suurus on 2 MB.")
            else:
                try:
                    pilt = io.BytesIO(data)
                    img = Image.open(pilt)
                    st.image(img, caption='Pilt, mis saadeti kaamerast', use_column_width=True)
                    tulemus = lugeja.readtext(np.array(img), detail=0)
                    tuvastatud = "".join(tulemus).replace(" ", "").upper()
                    st.write("Tuvastati:", tuvastatud)
                    if any(nr in tuvastatud for nr in lubatud):
                        st.success("LUBA OLEMAS")
                    else:
                        st.error("LUBA PUUDUB")
                except Exception as e:
                    st.error(f'Ootamatu viga töötlemisel: {e}')
                finally:
                    for name in ('pilt', 'data', 'img', 'tulemus', 'tuvastatud'):
                        try:
                            del locals()[name]
                        except Exception:
                            pass
                    gc.collect()
else:
    st.warning('Saadi ootamatu tulemus kaamerast; proovi uuesti.')
