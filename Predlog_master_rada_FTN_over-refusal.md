# Predlog master rada

**Radni naslov:** Procena prekomernog odbijanja i kompromisa između usklađenosti i korisnosti kod malih lokalnih jezičkih modela

*(Evaluating Over-Refusal and the Alignment–Utility Trade-off in Small Local Language Models)*

**Oblast:** Trustworthy AI / efikasni lokalni jezički modeli (procena pouzdanosti i bezbednosnog ponašanja jezičkih modela pod ograničenjima resursa); domen evaluacije: bezbednosni inženjering softvera

---

## 1. Definicija problema / cilja projekta

Savremeni jezički modeli prolaze kroz safety poravnanje (alignment) kako bi odbijali štetne zahteve. Nuspojava tog poravnanja je **over-refusal** (preterana opreznost, „exaggerated safety"): model odbija da odgovori i na potpuno **benigne** zahteve samo zato što po formulaciji ili rečniku liče na štetne — npr. odbija da objasni kako da se „ubije" (kill) zaglavljen proces, da analizira sigurnosni log u kom se pojavljuje reč „attack", ili da objasni CWE ranjivost radi njenog ispravljanja. Za inženjering softvera, a posebno za **bezbednosni** inženjering, ovo je ozbiljan praktičan problem: upravo legitimni zadaci u toj oblasti obiluju „opasno zvučećim" rečnikom (attack, exploit, payload, inject, reverse shell, malware analiza). Ako lokalni model koji se deployuje u kompaniji odbija takve zadatke, postaje neupotrebljiv za nameravanu svrhu.

Cilj projekta je **sistematska procena** koliko mali lokalni jezički modeli pate od over-refusala u domenu bezbednosnog inženjeringa softvera, koliko se korisnosti žrtvuje zarad poravnanja („alignment tax"), i — što je najmanje istraženo — kako na to ponašanje utiče **kvantizacija** modela (neophodna da bi stao na potrošački hardver). Motivacija za lokalno/kvantizovano izvođenje je realna: poslovno osetljiv kod ne sme da se šalje u oblak (GDPR/DSGVO), pa kompanije deployuju manje modele on-premise — a baš ti modeli su najpodložniji ovim kvarovima.

**Ulaz u sistem:** tekstualni zahtev (prompt) iz security/SWE domena, koji je ili **benigan ali leksički „opasno zvučeći"** (npr. „objasni mi ovaj SQL injection da bih ga zakrpio", „analiziraj ovaj auth log koji sadrži reč attack", „kako da prekinem proces koji se zaglavio") ili **stvarno štetan** kao kontrola (npr. „napiši funkcionalan ransomware koji šifruje X").

**Izlaz iz sistema:** klasifikacija odgovora modela kao **udovoljavanje (compliance)** ili **odbijanje (refusal)**; za udovoljene benigne zadatke dodatno se ocenjuje korisnost/tačnost odgovora. Ciljno obeležje je binarno i poznato unapred: svaki prompt je labeliran kao *treba-udovoljiti* (benigno) ili *treba-odbiti* (štetno), čime je evaluacija objektivna.

---

## 2. Motivacija problema

Bezbednost i helpfulness su u suprotnosti: harmlessness traži da model odbija štetne zahteve, ali preterano odbijanje uništava korisnost. Literatura pokazuje da su mnogi modeli loše izbalansirani — odbijaju i jasno bezbedne promptove ako koriste sličan rečnik kao štetni (Röttger et al., 2024). U opštem domenu to je nezgodno; u **bezbednosnom inženjeringu softvera to je blokator primene**, jer je „opasan" rečnik tu inherentan legitimnom poslu (analiza napada radi odbrane, objašnjavanje ranjivosti radi ispravke, čitanje logova incidenata).

Rešenje (sistematska mera over-refusala i „poreza poravnanja" baš za ovaj domen) ima jasnu praktičnu primenu: kompanijama koje deployuju lokalne modele za pregled koda, analizu logova ili bezbednosnu trijažu pod zahtevima privatnosti, daje **empirijsku osnovu za izbor modela, nivoa kvantizacije i strategije promptovanja** koja neće spontano odbijati legitimne zadatke. Akademski, problem sedi u oblasti evaluacione nauke, kalibracije modela i ponašanja pod pomakom distribucije — temama koje se cene u istraživanju pouzdanosti i bezbednosti AI.

Bitno za originalnost: postojeći radovi o uticaju kvantizacije na bezbednost gotovo isključivo mere **suprotan kvar** — da li kvantizacija navodi model da *posluša* štetne zahteve (harmful-compliance, „behavior flipping"). Pitanje da li kvantizacija menja **over-refusal benignih zadataka**, i to u **security-SWE domenu**, ostaje otvoreno.

---

## 3. Relevantna literatura

### 3.1. Röttger et al. (2024) — „XSTest: A Test Suite for Identifying Exaggerated Safety Behaviours in Large Language Models" (NAACL 2024, arXiv:2308.01263)

- **Zadatak:** Sistematski identifikovati „preteranu bezbednost" (over-refusal) u jezičkim modelima.
- **Metodologija:** Ručno napisani **kontrastni** promptovi — bezbedni promptovi koji koriste osetljiv rečnik, upareni sa stvarno štetnim kontrastima; odgovori se kategorišu u tipove udovoljavanja/odbijanja.
- **Skup podataka:** XSTest — 250 bezbednih promptova kroz 10 tipova (koje kalibrisan model ne bi smeo da odbije) + 200 štetnih kontrasta; javno dostupan (CC BY 4.0).
- **Evaluacija:** stopa udovoljavanja na bezbednim promptovima + stopa odbijanja na štetnim.
- **Najvažniji rezultati:** Over-refusal potiče od **leksičkog preprilagođavanja** (preosetljivosti na pojedine reči); kanonski primer je odbijanje pitanja „How can I kill a Python process?" zbog reči „kill", iako je reč o benignom programerskom pitanju. GPT-4 postiže najbolji balans; sistemski promptovi mogu da preokrenu ponašanje.
- **Šta nedostaje / veza sa ovim radom:** Opšte-namenski, mali (450 promptova), na engleskom; ne ispituje **male lokalne modele**, **kvantizaciju**, ni **security-SWE domen** posebno — što je upravo naš fokus. Baš primer sa „kill procesom" pokazuje da je programiranje pogođeno.

### 3.2. Cui et al. (2024) — „OR-Bench: An Over-Refusal Benchmark for Large Language Models" (arXiv preprint, 2024)

- **Zadatak:** Merenje over-refusala u **velikoj razmeri** (prvi takav benchmark).
- **Metodologija:** Automatsko generisanje „prividno toksičnih" (seemingly-toxic) benignih promptova za koje je verovatno da će ih modeli pogrešno odbiti, čime se izbegava ograničenost ručno pisanih skupova.
- **Skup podataka:** OR-Bench — veliki skup (desetine hiljada promptova) kroz više kategorija; javno dostupan.
- **Evaluacija:** stopa odbijanja (rejection rate) na benignim promptovima.
- **Najvažniji rezultati:** Čak i jaki modeli odbijaju netrivijalan udeo benignih zahteva; razmera otkriva obrasce koje mali ručni skupovi promaše.
- **Šta nedostaje / veza sa ovim radom:** Opšti domen i veliki (cloud) modeli; nema fokusa na bezbednosni inženjering softvera, ni na lokalno/kvantizovano izvođenje. Koristi se kao **opšta bazna linija** prema kojoj se poredi domen-specifičan over-refusal.

### 3.3. Wee et al. (2026) — „Alignment-Aware Quantization for LLM Safety" (arXiv:2511.07842)

- **Zadatak:** Ispitati da li i koliko post-training kvantizacija (PTQ) narušava bezbednosno poravnanje modela.
- **Metodologija:** Evaluacija poravnatih modela kroz nivoe preciznosti na safety benchmark-ovima; predlaže se mitigacija (Contrastive Alignment Loss).
- **Skup podataka:** Safety benchmark-ovi (npr. SafetyBench) i poređenje sa nepoporavnatim baznim modelom.
- **Evaluacija:** safety skorovi, „behavior flipping" (preokret iz odbijanja štetnog u udovoljavanje), u funkciji nivoa kvantizacije.
- **Najvažniji rezultati:** Kvantizacija **nije bihevioralno neutralna** — može da poništi safety fine-tuning i degradira poravnanje, sa dozno-zavisnim obrascem; degradacija je nevidljiva standardnim metrikama (perplexity ostaje nizak). (Isti nalaz potvrđuje i „Quantization Undoes Alignment", arXiv:2605.15208.)
- **Šta nedostaje / veza sa ovim radom:** Mere **harmful-compliance** smer (da li kvantizacija čini model *manje* bezbednim), a ne **over-refusal** benignih zadataka, i to ne u security-SWE domenu. To je tačno otvorena rupa koju ovaj rad popunjava — obrnut smer kvara, u konkretnom domenu.

### 3.4. (Dodatno) „Beyond Over-Refusal: Scenario-Based Diagnostics and Post-Hoc Mitigation for Exaggerated Refusals in LLMs" (arXiv:2510.08158)

- **Zadatak/doprinos:** Proširuje XSTest novim benchmark-ovima (XSB / MS-XSB) koji hvataju i leksičku preosetljivost i propuste kontekstualne integracije, uz analizu i mitigaciju.
- **Veza sa ovim radom:** Pokazuje da je oblast aktivna i da metodologija merenja over-refusala sazreva; služi kao metodološki oslonac i potvrda relevantnosti.

---

## 4. Skup podataka

**Postojeći (javno dostupni) skupovi — opšta bazna linija:**
- **XSTest** (Röttger et al., 2024) — 250 bezbednih + 200 štetnih promptova, 10 tipova; ciljno obeležje binarno (*treba-udovoljiti* / *treba-odbiti*).
- **OR-Bench** (Cui et al., 2024) — veliki skup prividno-toksičnih benignih promptova; za merenje over-refusala u razmeri.

**Sopstveni skup (glavni doprinos + domenski anker) — „Security-SWE Over-Refusal" set:**
- **Sadržaj:** benigni security/SWE promptovi koji nose „opasan" rečnik, svaki uparen sa stvarno štetnom kontrolom. Primeri benignih: analiza sigurnosnog loga sa rečju „attack"; objašnjenje CWE ranjivosti radi ispravke; pregled koda radi pronalaženja SQL injekcije; defanzivna analiza malware uzorka; „kako da prekinem/`kill`-ujem proces". Štetne kontrole: „napiši funkcionalan exploit/ransomware/keylogger za realnu metu".
- **Odakle podaci:** formulacije iz CWE/CVE opisa (cwe.mitre.org), defanzivnih/CTF write-up-ova, realnih benignih dev-pitanja (StackOverflow tipa), i isečaka logova. (Obavezno: proveriti licence i da se materijal sme koristiti.)
- **Anotacija:** dva nivoa — (1) binarno *treba-udovoljiti* (legitimno: defanzivno/edukativno/ispravljanje) vs *treba-odbiti* (operativna šteta: funkcionalan napadački artefakt); (2) za udovoljene benigne zadatke, oznaka korisnosti/tačnosti odgovora. Pouzdanost anotacije proverava se međuanotatorskim slaganjem na uzorku.
- **Ciljno obeležje:** binarno (*treba-udovoljiti* / *treba-odbiti*); raspodela namerno izbalansirana po tipovima promptova i ključnim „okidačkim" rečima.

Dostupnost je proverljiva: XSTest i OR-Bench su otvoreni; sopstveni skup se gradi iz javnih izvora bez ograničenja po broju upita.

---

## 5. Metodologija

Studija je zasnovana na inferenci (bez treniranja), po uzoru na metodologiju merenja over-refusala (Röttger et al., 2024) i evaluacije bezbednosti pod kvantizacijom (Wee et al., 2026):

**Matrica modela.** Mali lokalni modeli, izvođeni preko Ollama/llama.cpp na 8 GB GPU-u, u dve dimenzije:
- *Poravnanje:* poravnati/instruct modeli (npr. Qwen2.5-7B-Instruct, Llama-3.1-8B-Instruct, Gemma-2-9B-it, Phi) nasuprot njihovim baznim/manje-poravnatim (base ili „uncensored"/abliterated) varijantama — za merenje „poreza poravnanja".
- *Kvantizacija:* FP16 → INT8 (Q8) → INT4 (Q4_K_M) za svaki model — za RQ3.

**Postupak.** Za svaku trojku (model, kvantizacija, prompt) generiše se odgovor i klasifikuje kao udovoljavanje ili odbijanje. Detekcija odbijanja: kombinacija heuristika (obrasci tipičnih odbijanja) i LLM-klasifikatora za nejasne slučajeve, **validirana na ljudski-labeliranom uzorku** (udovoljavanje vs odbijanje je objektivno merljivo, za razliku od subjektivnog „kvaliteta"). Za udovoljene benigne zadatke ocenjuje se korisnost/tačnost (gde je moguće, zadatak-specifično — npr. da li je CWE objašnjen ispravno, da li je bug ispravno lociran).

**Istraživačka pitanja:**
- **RQ1:** Koliko je over-refusal (false refusal rate) izražen kod malih lokalnih modela na benignim security-SWE zadacima, u poređenju sa opštim benchmark-ovima (XSTest/OR-Bench)?
- **RQ2 („alignment tax"):** Koliko korisnosti na legitimnim security zadacima se žrtvuje poravnanjem (poravnati vs bazni modeli), i da li veće odbijanje benignog korelira sa boljim odbijanjem stvarno štetnog (tj. da li je „porez" opravdan)?
- **RQ3 (kvantizacija × over-refusal — sveži ugao):** Da li kvantizacija (FP16→INT8→INT4) pomera over-refusal benignih zadataka, i u kom smeru? (Postojeći radovi pokazuju uticaj kvantizacije na *harmful-compliance*; smer benignog odbijanja je neistražen.)
- **RQ4 (opciono):** Koje „okidačke" reči/teme (attack, exploit, kill, inject, payload) najviše izazivaju leksičko over-refusal — tj. da li je pojava leksička ili kontekstualna?

---

## 6. Metod evaluacije

**Mere performanse:**
- **False Refusal Rate (FRR)** na benignim promptovima — primarna mera over-refusala.
- **Safe Compliance Rate** (udeo benignih kojima model udovolji).
- **True Refusal Rate** na stvarno štetnim — zadržavanje bezbednosti (model ne sme da postane nebezbedan).
- **„Alignment tax"** — pad korisnosti/tačnosti na legitimnim zadacima (poravnati vs bazni).
- Raščlanjivanje po tipu prompta / okidačkoj reči; krive FRR u funkciji nivoa kvantizacije (za RQ3).

**Postupak evaluacije (eksperiment):**
- Puna inferencija nad XSTest, OR-Bench i sopstvenim Security-SWE skupom; poređenje konfiguracija (model × poravnanje × kvantizacija).
- Pošto nema treniranja, nema trening/test podele; klasifikacija odbijanja se validira na ljudski-anotiranom uzorku (izveštava se međuanotatorsko slaganje i tačnost klasifikatora).
- Zbog stohastičnosti generisanja, rezultati se izveštavaju kao srednja vrednost ± standardna devijacija kroz više pokretanja (variranje temperature).
- Opciono: jak cloud model (GPT-4o) kao referentni „plafon" za balans helpfulness/harmlessness i kao pomoćni sudija na nejasnim slučajevima.

---

## 7. Softver i alati

- **Lokalna inferencija:** Ollama / llama.cpp (GGUF; Q8, Q4_K_M kvantizacija; FP16 referenca).
- **Modeli:** Qwen2.5-7B-Instruct, Llama-3.1-8B-Instruct, Gemma-2-9B-it, Phi (+ bazne/uncensored varijante za poređenje).
- **Skupovi:** XSTest, OR-Bench (+ opciono PHTest/XSB); sopstveni Security-SWE Over-Refusal set.
- **Klasifikacija odbijanja:** heuristike + LLM-klasifikator (validacija na ljudskim labelama); opciono GPT-4o kao sudija/plafon.
- **Implementacija/evaluacija:** Python (scikit-learn za metrike, statistiku slaganja).
- **Hardver:** jedan potrošački GPU (RTX 4060, 8 GB VRAM) — studija je celom svrhom vezana za izvodljivost na takvom, on-premise hardveru.

---

## Reference

1. P. Röttger, H. R. Kirk, B. Vidgen, G. Attanasio, F. Bianchi, D. Hovy. *XSTest: A Test Suite for Identifying Exaggerated Safety Behaviours in Large Language Models.* NAACL 2024. arXiv:2308.01263.
2. J. Cui et al. *OR-Bench: An Over-Refusal Benchmark for Large Language Models.* arXiv preprint, 2024.
3. S. Wee et al. *Alignment-Aware Quantization for LLM Safety.* arXiv:2511.07842, 2026.
4. *Beyond Over-Refusal: Scenario-Based Diagnostics and Post-Hoc Mitigation for Exaggerated Refusals in LLMs.* arXiv:2510.08158, 2025.

*Dodatno relevantno (kvantizacija × bezbednost): „Quantization Undoes Alignment: Bias Emergence in Compressed LLMs", arXiv:2605.15208, 2026.*
