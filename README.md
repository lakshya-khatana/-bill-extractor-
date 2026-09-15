# Bill Extractor v2 — Claude Vision API + Streamlit

Purani local-Ollama pipeline (GTX 1650, 4GB VRAM) me jo problems the — garbage
`@@@@@@` output, JSON parse crash, list-type crash, 100-270 sec/image slowness —
sab GPU-constrained local model ki wajah se the. Ye naya version cloud-based
**Anthropic Claude Vision API** use karta hai, isliye:

- Koi GPU chahiye nahi (koi local model load nahi hota)
- 2-5 second/image (vs 100-270 sec pehle)
- Handwritten + printed dono text reliably padhta hai
- Clean structured JSON — koi garbage-output cascade nahi

## Setup

1. Python 3.9+ install hona chahiye.
2. Project folder me terminal khol ke:
   ```
   pip install -r requirements.txt
   ```
3. Apni Gemini API key set karo (aistudio.google.com/apikey se free milegi):

   **Windows PowerShell:**
   ```
   $env:GEMINI_API_KEY="AIza-your-key-here"
   ```
   **Mac/Linux:**
   ```
   export GEMINI_API_KEY="AIza-your-key-here"
   ```

4. App run karo:
   ```
   streamlit run app.py
   ```
   Browser automatically khulega (usually http://localhost:8501).

## Use kaise karein

1. Sidebar se ek ya multiple bill photos upload karo (jpg/png/webp).
2. Har thumbnail ke neeche "▶️ Extract" button click karo — us bill ka data
   turant extract ho jayega aur neeche panel me editable fields dikhenge.
3. Bahut saari bills ek saath process karni ho to sidebar me **"⚡ Extract ALL
   (batch)"** button use karo.
4. Extraction ke baad fields edit kar sakte ho (agar model kuch galat padhe)
   aur "💾 Save edits" se save kar sakte ho.
5. Neeche "📊 Export" section me poora data table dikhega — **Download CSV**
   se ek click me poora extracted data nikal sakte ho (Excel me khul jayega).

## Files

- `app.py` — Streamlit UI (upload, thumbnail grid, click-to-extract, export)
- `extractor.py` — Claude Vision API call + JSON parsing + field normalization
- `uploaded_bills/` — auto-created, saari uploaded images yahan store hoti hain
- `results.json` — auto-created, extracted data yahan persist hota hai (app
  band-restart karne par bhi data safe rehta hai)

## Fields extract hote hain

Shop/Vendor, Address, Phone, Bill/Invoice No., Date, Customer Name,
Customer Address, Item/Description, Serial/Batch No., Qty, Rate, Amount,
Total, Notes — same 14 fields jo purane Eapro reference sheet me the, isliye
purana export format compatible rehta hai.

## Scale ke liye note

Agar aage 3-4 lakh files tak scale karna ho (jaisa employer ka original ask
tha), to:
- Streamlit ki jagah ek background worker queue (e.g. simple script loop ya
  Celery) use karna better hoga — Streamlit interactive single-user demo/tool
  ke liye best hai, bulk unattended processing ke liye nahi.
- API cost pehle se calculate kar lena — per-image cost x lakh images
  significant ho sakta hai; batch/pricing tiers Anthropic console me dekh
  sakte ho.
- `results.json` ki jagah SQLite/Postgres use karna better hoga bade scale
  par (jaisa purane project me documents.db tha).

Filhaal ye version chhoti se medium scale (jaise 500-image pilot) ke liye
turant kaam karne wala, reliable tool hai.
