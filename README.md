# AetherFO — Simple Guide (F&O Prediction App)

Yeh app **Futures & Options (F&O)** ke liye live signal dikhati hai:  
kis price pe **BUY** karna hai, kis price pe **STOP LOSS (EXIT)** karna hai, aur kahan **TARGET / profit book** karna hai.

> Ye **100% accurate nahi** hai. Trading me risk hota hai. Pehle paper-trade / chhote size se samjho.

---

## Sabse pehle: screen pe words ka matlab

| Screen pe likha | Seedha matlab |
|-----------------|---------------|
| **BUY / ENTRY** | Is price ke aas-paas **nayi position lo** (option BUY) |
| **STOP LOSS (EXIT)** | Loss rokne ke liye yahan pe **position band / cut** karo. Matlab option ko **bech do (exit)** — nuksaan badhne se pehle nikal jao |
| **TARGET 1 / 2 / 3** | Profit book karne ke levels — yahan pe **partial ya full exit** |
| **BUY CE** | Call option kharido — market **upar** jaaye to profit |
| **BUY PE** | Put option kharido — market **niche** jaaye to bhi profit |
| **Confidence %** | Model kitna sure feel kar raha hai (0–100). Zyada % = stronger setup, **guarantee nahi** |

**“BACHAO” ab nahi dikhega.** Pehle confuse ho sakta tha. Ab clear hai: **STOP LOSS = EXIT / CUT**.

---

## Kaise use karein (bahut simple)

### Step 1 — App chalao

**Terminal 1 (Backend):**

```powershell
cd "c:\Users\nitin\Downloads\New folder work\backend"
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 (Frontend):**

```powershell
cd "c:\Users\nitin\Downloads\New folder work\frontend"
npm run dev
```

Browser kholo: **http://localhost:3000**  
Upar **LIVE** green dikhna chahiye.

> Pehli baar setup? Neeche “Pehli baar install” section dekho.

### Step 2 — Name search karo

1. Upar search box me type karo: `NIFTY`, `BANKNIFTY`, `RELIANCE`, `TCS`…
2. List se naam select karo
3. Chart + option chain + prediction usi symbol pe switch ho jayega

### Step 3 — Live Trade card padho

Upar bada card dikhega, jaise:

- Market **UP** bias → **BUY CE** + Entry / Stop Loss / Targets  
- Market **DOWN** bias → **BUY PE** (niche market me bhi profit possible) + Entry / Stop Loss / Targets  

**Example socho:**

1. **BUY CE Strike 24500** premium **100** pe kharido  
2. Premium **65** pe aa jaye → **STOP LOSS** → EXIT (cut)  
3. Premium **170** pe aa jaye → **TARGET** → profit book  

Spot levels (Entry / SL / T1/T2/T3) chart pe lines se bhi dikhte hain.

### Step 4 — Risk rule (must)

- Kabhi bhi **Stop Loss ignore mat karo**
- App tabhi signal accept karti hai jab **Risk:Reward kam se kam 1:2** ho (T1 pe)
- Confidence low / WAIT dikhe to **force trade mat lo**

---

## Yeh app kaise kaam karti hai?

```
Broker / Mock data  →  Redis (optional)  →  Quant Engine  →  WebSocket  →  Dashboard
     (prices)              (fast cache)     (PCR, Greeks,      (live)        (chart +
                                             ML score, RR)                    signals)
```

1. **Data aata hai** — spot price, volume, option chain (bid/ask, OI, IV)  
2. **Engine sochti hai** — PCR, Max Pain, VWAP, trend (EMA), RSI, OI buildup + ML score  
3. **Direction decide** — UP → CE, DOWN → PE  
4. **Levels banate hain** — Entry, Stop Loss, Target 1/2/3 (spot + option premium)  
5. **Filter** — weak / kharab RR wale signals discard  
6. **Screen pe live** — card + chart lines + signal feed  

---

## Data kahan se aata hai?

| Mode | Source | Kab use |
|------|--------|---------|
| **Mock (default)** | App khud realistic fake ticks banati hai | Seekhne / demo / coding ke liye — **API key nahi chahiye** |
| **Live broker** | DhanHQ / Fyers / Zerodha jaisa WebSocket (config se) | Asli market data ke liye |

Abhi default = **`BROKER=mock`**.  
Asli broker ke liye `backend/.env` me token + `BROKER=dhan` set karo (details neeche).

**Redis:** optional fast cache. Na ho to bhi app chalega (sirf warning aayegi).

---

## Kitne % sahi batati hai?

**Short answer:** Koi bhi app **guarantee %** nahi de sakti. Market random + news + event se move karti hai.

Is project me:

| Cheez | Sachayi |
|-------|---------|
| Confidence score (jaise 70%) | Model ka **self-score** — “kitna strong setup lag raha hai” |
| Accuracy guarantee | **Nahi** — 100% claim galat hoga |
| Demo (mock) mode | Synthetic data pe trained/heuristic blend — **real backtest accuracy nahi** |
| Realistic expectation | High-probability filter se **galat trades kam** karne ki koshish; phir bhi lose ho sakte ho |
| Honest range (rule of thumb) | Live labeled history ke bina claim mat karo. Paper trade karke **khud track** karo (jaise 100 trades me kitne hit) |

Confidence threshold default ~**55%+**. Usse kam = signal discard / WAIT.

> **Disclaimer:** Ye educational / analytics tool hai, SEBI-registered advice nahi. Apna capital risk pe.

---

## Screen pe kya-kya dikhta hai?

1. **Search** — symbol choose  
2. **Live Trade Indication** — Entry, Stop Loss (EXIT), Targets, CE/PE strike + premium plan  
3. **Chart** — live candles + Entry / SL / T1 / T2 / T3 lines  
4. **Option Chain** — CE/PE OI, LTP, IV, PCR, Max Pain, VWAP  
5. **Signal Feed** — recent setups (accepted + discarded reasons)

---

## Pehli baar install (Windows)

Python **3.12** use karo (3.14 se packages toot sakte hain).

```powershell
cd "c:\Users\nitin\Downloads\New folder work\backend"
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

```powershell
cd "c:\Users\nitin\Downloads\New folder work\frontend"
copy .env.local.example .env.local
npm install
```

Phir upar wale **Step 1** se dono servers chalao.

Check:

- Backend health: http://127.0.0.1:8000/health  
- App: http://localhost:3000  

---

## Settings (optional)

**`backend/.env`**

```env
BROKER=mock
UNDERLYING=NIFTY
MIN_RR_RATIO=2.0
CONFIDENCE_THRESHOLD=0.55
CORS_ORIGINS=["http://localhost:3000"]
PORT=8000
```

**`frontend/.env.local`**

```env
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/market
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Live broker (optional)

```env
BROKER=dhan
BROKER_CLIENT_ID=your_id
BROKER_ACCESS_TOKEN=your_token
BROKER_WS_URL=wss://api-feed.dhan.co
```

Restart backend. Packet format alag ho to `data_stream.py` me parser adjust karna pad sakta hai.

---

## Common problems

| Problem | Fix |
|---------|-----|
| RECONNECTING | Backend port 8000 pe chal raha hai? `.env.local` WS URL sahi hai? |
| pip fail (Python 3.14) | `py -3.12 -m venv .venv` se naya venv banao |
| Port busy | Backend `--port 8001` + frontend WS URL update |
| Redis warning | Ignore OK — optional hai |

---

## Folder structure (short)

```
backend/app/
  main.py                 API + live WebSocket
  data/data_stream.py     Market data in
  quant/quant_engine.py   Prediction + CE/PE + SL/Target
  instruments.py          Searchable symbol list
frontend/src/components/
  Dashboard.tsx
  LiveTradePlan.tsx       Entry / Stop Loss / Target card
  LiveChartComponent.tsx
  SymbolSearch.tsx
```

---

## Band kaise karein

Dono terminals me `Ctrl+C`.

---

## Ek line me yaad rakho

**Search → Signal padho → Entry pe BUY (CE ya PE) → Stop Loss pe EXIT → Target pe BOOK.**  
Confidence sirf guide hai — **apna risk manage karo.**
