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
<div style="text-align:center">
  <div style="height:33vh;width:100%;max-width:420px;margin:0 auto;position:relative;">
    <video id="video" autoplay playsinline style="height:100%;width:auto;max-width:100%;display:block;border-radius:8px;margin:0 auto;"></video>
    <div id="overlay" style="width:80%;aspect-ratio:4/1;border:3px solid rgba(76,175,80,0.9);border-radius:6px;pointer-events:none;position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);"></div>
  </div>
  <div style="margin-top:12px">
    <button id="capture" style="padding:12px 20px;background:#2196F3;border:none;color:white;border-radius:8px;font-size:16px">Pildista</button>
  </div>
  <div id="msg" style="margin-top:8px;color:#666;font-size:13px">Aseta numbrimärk rohelise raamiga ja vajuta "Pildista".</div>
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

if result:
  raw = result
  # Normalize common wrappers
  if isinstance(raw, (list, tuple)) and len(raw) > 0:
    raw = raw[0]
  if isinstance(raw, dict):
    # Some Streamlit versions/components may wrap value in a dict
    raw = raw.get('value', raw)
  if isinstance(raw, bytes):
    try:
      raw = raw.decode('utf-8')
    except Exception:
      raw = str(raw)

  raw_str = str(raw)
  if 'data:image' in raw_str:
    # extract data URL from any surrounding text
    idx = raw_str.find('data:image')
    data_url = raw_str[idx:]
    if data_url.startswith('data:image'):
      try:
        header, b64 = data_url.split(',', 1)
      except ValueError:
        st.error('Saadi ootamatu kujul pildidata. Proovi uuesti.')
        data_url = None
    else:
      data_url = None
  else:
    data_url = None

  if data_url:
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
        for name in ('data', 'img', 'tulemus', 'tuvastatud'):
          try:
            del locals()[name]
          except Exception:
            pass
        pilt = None
        gc.collect()
  else:
    st.warning('Saadi ootamatu tulemus kaamerast; proovi uuesti.')
