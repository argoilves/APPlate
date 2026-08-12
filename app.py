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

# Autocapture options
auto = st.checkbox("Autocapture (pildistab automaatselt)", value=False)
delay = st.number_input("Autocapture viive sekundites", min_value=1, max_value=10, value=2)

html = """
<div style="text-align:center">
  <video id="video" autoplay playsinline style="width:100%;height:auto;border-radius:8px"></video>
  <div style="position:relative;width:100%;display:flex;justify-content:center;margin-top:8px;">
    <div id="overlay" style="width:80%;aspect-ratio:4/1;border:3px solid rgba(76,175,80,0.9);border-radius:6px;pointer-events:none;position:absolute"></div>
  </div>
  <div style="margin-top:8px">
    <button id="capture" style="padding:8px 16px;background:#4CAF50;border:none;color:white;border-radius:6px">Capture</button>
    <button id="stop" style="padding:8px 12px;margin-left:8px;border-radius:6px">Stop</button>
  </div>
  <div id="msg" style="margin-top:8px;color:#666;font-size:13px">Aseta numbrimärk rohelise raamiga ja vajuta "Capture".</div>
</div>
<script>
const video = document.getElementById('video');
const captureBtn = document.getElementById('capture');
const stopBtn = document.getElementById('stop');
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
stopBtn.onclick = ()=>{ if(stream){ stream.getTracks().forEach(t=>t.stop()); video.srcObject=null; document.getElementById('msg').innerText='Kaamera peatatud.' } }

const auto = %s;
if(auto){ setTimeout(()=>{ doCapture(); }, %d); }
</script>
""" % ("true" if auto else "false", int(delay*1000))

result = components.html(html, height=520)

if result:
    data_url = result
    if data_url.startswith('data:image'):
        header, b64 = data_url.split(',', 1)
        data = base64.b64decode(b64)
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
            finally:
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
