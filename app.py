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

# Näitame ainult ühte kaamera vaadet (allpool) — palun kasuta seda raamiga joondamiseks.

# Muutujad
pilt = None

# Custom in-page camera with overlay (uses getUserMedia). Captured image is automatically downloaded;
# then upload the downloaded image below using "Või lae pilt üles".
import streamlit.components.v1 as components

components.html(
        """
        <div style="text-align:center">
            <video id="video" autoplay playsinline style="max-width:100%;border-radius:8px"></video>
            <div style="position:relative;width:100%;display:flex;justify-content:center;margin-top:8px;">
                <div id="overlay" style="width:80%;aspect-ratio:4/1;border:3px dashed #4CAF50;border-radius:6px;box-shadow:0 0 0 1000px rgba(0,0,0,0.25) inset;pointer-events:none"></div>
            </div>
            <div style="margin-top:8px">
                <button id="capture" style="padding:8px 16px;background:#4CAF50;border:none;color:white;border-radius:6px">Capture</button>
                <button id="stop" style="padding:8px 12px;margin-left:8px;border-radius:6px">Stop</button>
            </div>
            <div id="msg" style="margin-top:8px;color:#666;font-size:13px">Aseta numbrimärk rohelise kasti ja vajuta "Capture". Pilt salvestatakse seadmesse.</div>
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
                document.getElementById('msg').innerText = 'Kaamera ei ole kättesaadav. Kasuta üleslaadimist.';
            }
        }
        start();
        captureBtn.onclick = async ()=>{
            const canvas = document.createElement('canvas');
            const w = video.videoWidth;
            const h = video.videoHeight;
            // Calculate crop to center with plate-like aspect ratio (4:1) based on smaller dimension
            const targetRatio = 4/1;
            let cw = w, ch = Math.round(w/targetRatio);
            if(ch > h){ ch = h; cw = Math.round(h*targetRatio); }
            const sx = Math.round((w - cw)/2);
            const sy = Math.round((h - ch)/2);
            canvas.width = cw; canvas.height = ch;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, sx, sy, cw, ch, 0, 0, cw, ch);
            canvas.toBlob(function(blob){
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'capture.png';
                document.body.appendChild(a);
                a.click();
                a.remove();
                URL.revokeObjectURL(url);
                document.getElementById('msg').innerText = 'Pilt salvestatud. Palun lae see nüüd üles all oleva nupu abil.';
            }, 'image/png');
        };
        stopBtn.onclick = ()=>{ if(stream){ stream.getTracks().forEach(t=>t.stop()); video.srcObject=null; document.getElementById('msg').innerText='Kaamera peatatud.' } }
        </script>
        """,
        height=520,
)

# Faili üleslaadimine pildi töötlemiseks (pärast Capture'i salvestamist valige all laetud pilt)
pilt = st.file_uploader("Laadi salvestatud pilt üles kontrolliks", type=["png", "jpg", "jpeg"]) 

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
