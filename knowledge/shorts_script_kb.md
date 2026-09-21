# SHORTS SCRIPT KNOWLEDGE BASE (internet research se compiled, v2)
Writer + Critic dono ka training material. Har rule niche diye research sources
(retention-curve playbook 2026, hook-formula libraries, pacing studies) se aaya hai.

## 1. HOOK (0-3 second) — sabse high-leverage frame
- Pehli line = shock / galat-fehmi / nuksaan / contrarian. BOLNE ke liye 5-8 words.
- HOOK VISUAL BHI HAI: pehla frame hook-text card hota hai — 4-7 words on-screen,
  high-contrast. Verbal-only hook fail hota hai (sound-off viewers 60-80%).
- Hook me 3 cheezein: ANTICIPATION (nuksaan/result) + QUESTION-feel (curiosity gap)
  + PAYOFF-HINT ("aaj exactly yahi batayenge" implied, answer mat do).
- Proven formulas (Hindi, chhote):
  * "Yeh ek galti fasal kha jati hai" (mistake/warning)
  * "90% kisan yahi bhul karte hain" (negative-curiosity)
  * "X ka sach koi nahi batata" (contrarian)
  * "X me nuksaan? Ruk jao" (direct-stop)
- KABHI nahi: welcome / namaskar / dosto / kisan bhai / "aaj hum janenge" /
  "kya aap jante hain". Ye swipe karwa dete hain.
- Hook me topic ka core noun ho — viewer turant jaane kis baare me hai.
- Specific > generic: "20 kilo urea" > "khaad"; personal: "aapki fasal" > "fasal".

## 2. STRUCTURE (Hook → Agitation → Points → Payoff → CTA+Loop)
- beat0: hook (promise/warning) — answer mat do
- beat1-2: agitation — dard/nuksaan, stakes badhao. SOLUTION YAHAN MAT BATAO
  (curiosity gap hi retention hai; "avoid the preview" rule)
- beat3..N-2: solution ke chhote concrete steps — har beat me SIRF EK nayi baat
- beat N-2: payoff — hook ka promise poora (natija: upaj badhi/nuksaan ruka)
- last beat: CTA + LOOP — share+subscribe value se juda, aur aakhri line hook wali
  galti/cheez ka dobara zikr kare taaki video loop me natural lage
  (loop >100% retention = algorithm ka sabse strong signal)

## 3. PACING & INFORMATION DENSITY
- Ideal Shorts 25-45 sec. Words: 30s=70-110, 45s=110-150. Hmara target 100-140.
- Har beat = 5-9 words ki EK poori boli jaane wali line (2.5-4 sec speech).
- 12-15 beats → har 3-4 sec me naya visual+info (research: 2-3 sec me visual beat,
  5-8 sec me attention reset).
- INFORMATION DENSITY: har beat kuch NAYA de (fact/step/visual change).
  Do consecutive beats same baat repeat NA karein — flat middle = drop-off zone.
- Chhote vakya. "tum/aap" language. 8th-grade reading level. Koi AI-cliche nahi
  ("delve", "unlock", "game-changer", "dosto", "namaskar" forbidden).

## 4. VOICE-IMAGE SYNC (sabse zaroori quality rule)
- Har beat ka visual USI beat ke verb-phase se match ho.
- PHASES (kheti): sowing (bonai/beej) → growth (hari fasal/patti) →
  treatment (khaad/dawai/sinchai) → harvest (katai) → result (bhara godam/upaj).
- PHASE-LOGIC: "beej bone ka time" bola → sowing visual; "hari patti" boli →
  growth visual — harvest/paddy/carrot NAHI.
- vis = concrete dikhti cheez: field, haath, beej, paani, patti, bore, tractor,
  daana. Abstract (time, mistake, profit, stage) screen pe dikhta hi nahi.
- Pehla frame visually dense ho (hook card bhi dense: bold text + color blocks).

## 5. HINDI STYLE
- Bolchal ki Devanagari Hindi; gaon me boli jaane wali bhasha.
- Grammatical poori line — adhura tukda ("fasal ghatati") KABHI nahi.
- Numbers/dose sirf tab jab 100% pakka ho.
- English jargon nahi; "urea" chalta hai, "nitrogen level" nahi.

## 6. CTA (last 3-5 sec) + LOOP
- Share + subscribe dono bolo, value se jodo: "aisi jankari har kisan tak
  share karo, channel subscribe karo".
- CTA 6-12 words, warmth se. Payoff ke BAAD (emotion ke flow me), beech me nahi.
- Loop cue: CTA ke saath hook ki galti dobara yaad dilao
  ("wo pehli galti ab kabhi mat karna") — ending frame-1 se judi lage.

## 7. CRITIC CHECKLIST (score & fix)
1. hook 5-8 words, shock/nuksaan, no greeting, topic-noun present, on-screen 4-7 words
2. beat1-2 me solution leak NAHI (sirf dard/stakes)
3. har beat 5-9 words, poori grammatical line, nayi information
4. beats 12-15, total 100-140 words
5. phase-logic order sahi (sowing→growth→treatment→harvest→result)
6. har vis concrete + phase-match; q = concrete english nouns only
7. CTA me share+subscribe + loop cue (hook ka zikr)
8. forbidden phrases absent; koi angrezi jargon nahi
9. payoff hook ka promise close karta hai
10. har beat ka SEGMENT BRIEF poora hai (section 8) — search_q, gen_prompt, shot, motion

## 8. SEGMENT BRIEF — Script→Visual Agent contract
Script Agent ka MAIN kaam: har beat ko aisa "brief" banana ki Visual Agent bina
soche samjhe ki kaunsi image/video search karni hai ya kya generate karna hai.
Har beat me ye fields LAZMI hain:

- "t": boli jaane wali Hindi line (5-9 words)
- "vis": english scene description = SUBJECT + ACTION + SETTING
  (e.g. "farmer hands dropping urea granules into soil rows")
- "phase": sowing|growth|treatment|harvest|result|general
- "shot": closeup | hands | medium | wide | aerial
  (closeup/hands = detail/emotion; wide/aerial = context/scale)
- "motion": zoomin | zoomout | pan | static (render isi se movement deta hai)
- "search_q": [primary, fallback] — 2-4 word concrete english queries,
  phase-locked (sowing beat → "sowing seeds field" jaisa). Abstract KABHI nahi.
- "gen_prompt": AI image ke liye complete prompt:
  "realistic vertical 9:16 photo, {vis}, indian farm, natural daylight, no text"
- "overlay": on-screen 2-4 word text burst (stat/number/emotion) ya ""
  (e.g. "20 kg/acre", "पहली गलती") — sound-off viewers ke liye
- "imp": 1-3 (3 = hook/sabse important → exact-match AI-gen pehle)

EXAMPLE (wheat urea topic):
{"t":"पहली सिंचाई के बाद यूरिया डालो",
 "vis":"farmer sprinkling urea granules beside irrigated wheat rows",
 "phase":"treatment","shot":"hands","motion":"zoomin",
 "search_q":["fertilizer spreading field","farmer urea wheat"],
 "gen_prompt":"realistic vertical 9:16 photo, farmer sprinkling urea granules beside irrigated wheat rows, indian farm, natural daylight, no text",
 "overlay":"सिंचाई के बाद","imp":3}

Visual Agent isi brief se: imp>=2 → gen_prompt se AI image/video pehle;
warna search_q chain; har asset pe vision-QA; fail → agla route; sab fail → card.
