# 📝 TECHNICAL WRITEUP & ARCHITECTURE REPORT: ZT-RECON

### **Project Status: Active Development, Educational & Practical Application — v2.1.0**

---

## 📢 Disclaimer & Context

> **"لسه في بداية الطريق، وبنطور يوماً بعد يوم. المشروع ده أداة أمنية (Practical Learning Tool) اتبنت بغرض التطبيق العملي وفهم أعمق لآليات اختبار الاختراق، بالإضافة لاستكشاف دمج الذكاء الاصطناعي مع أدوات الفحص الحقيقية وأتمتتها. الأداة مخصصة للاستخدام على أهداف مصرّح باختبارها فقط (Authorized Targets)."**

---

## 💡 The General Project Concept

**ZT-RECON (AI-Powered Automated Recon & Exploitation Orchestrator)** بيسد الفجوة بين أدوات الفحص التقليدية (Signature-based Tools) والتحليل الذكي المستند للسياق (Semantic AI Analysis).

بدل ما مختبر الاختراق يشغّل Nmap و SQLMap و Dirsearch و Nuclei يدوياً واحدة واحدة، ويجمع مخرجاتهم النصية ويقراها لساعات، الأداة بتنفذ **كل حاجة بأمر واحد من التيرمينال**، تجمع بين الفحص الميداني، تخطي الجدران النارية، اكتشاف الـ Subdomains، تشغيل ترسانة OWASP Top 10، والتحليل الفوري بالذكاء الاصطناعي.

---

## 🏗️ The Architecture & Data Flow

الأداة نظام Orchestration بيمر بأربع طبقات بالتوالي:

### 1️⃣ Network Layer & Firewall/WAF Evasion

- **Host Discovery:** فحص حياة الجهاز عبر `TCP SYN Ping` على منافذ مشهورة (`-PS22,80,443`) بدل الـ ICMP التقليدي.
- **Firewall & WAF Evasion Flags** (متطبقة فعلياً دلوقتي في `scanner.py`):
  - `-f` — Packet Fragmentation لتقطيع الحزم.
  - `--mtu 24` — تحديد حجم مخصص لوحدة النقل.
  - `--data-length 32` — حقن بيانات عشوائية لتغيير التوقيع الرقمي.

  > ملحوظة تقنية: بعض نسخ nmap بتتجاهل `-f` لما تتجمع مع `-O` (OS detection)، فالتخفي في مرحلة الـ OS fingerprinting ممكن يكون أضعف من مرحلة الـ port scan.
- **Configurable Port Range *(جديد)*:** الـ Port Scan افتراضيًا بيغطي بس الرينج `1-1024` (الـ Well-Known Ports — سريع ومناسب لفحص أولي سريع). لكن الرينج ده كان قبل كده **ثابت (hardcoded)** جوه `scanner.py`، يعني أي خدمة شغالة على بورت فوق 1024 (زي MySQL على `3306`، Redis على `6379`، PostgreSQL على `5432`، Elasticsearch على `9200`، MongoDB على `27017`، أو حتى admin panels شغالة على `8080`/`8443`) كانت بتتفوّت تمامًا ومش بتظهر خالص في نتيجة الفحص.
  - دلوقتي الرينج بقى **قابل للتخصيص بالكامل** عن طريق `--ports` (تقدر تدّيله أي syntax مقبول عند nmap، زي رينج أو قايمة أو مزيج بينهم)، أو تستخدم الاختصار الجاهز `--full-scan` اللي بيعمل فحص شامل لكل الـ 65535 بورت.
  - **Session Awareness:** رينج البورتات المستخدم بيتحفظ جوه الـ session state نفسه (`port_range`). لو رجعت شغّلت نفس الهدف تاني برينج مختلف عن اللي كان محفوظ (مثلاً كنت فاحص بـ `1-1024` وبعدين رجعت بـ `--full-scan`)، الأداة بتكتشف الاختلاف ده تلقائيًا وتلغي (invalidate) بيانات البورتات القديمة المحفوظة وتعيد الفحص من جديد بالرينج الجديد، بدل ما تفضل "عالقة" على نتيجة رينج قديم وهي بتـ resume الجلسة.
- **Service & OS Fingerprinting:** استخراج إصدارات الخدمات وأنظمة التشغيل (`-sV -O`).
- **Live Working Indicator *(جديد v2.0.0)*:** كل مرحلة من المراحل دي (host discovery / port scan / OS fingerprinting) دلوقتي بتظهر جواها animated spinner أحمر في التيرمينال (عبر `phase_status` في `banner.py`) طول ما هي شغّالة، عشان يبان واضح إن الأداة "حية" ومش متجمدة حتى لو الفحص واخد وقت طويل من غير أي output.
- **ASCII Banner Font *(اتغيّر في v2.1.0)*:** خط الـ ASCII banner اللي بيطبع اسم الأداة أول ما تشتغل اتغيّر لـ `Big Money-ne` (خط FIGlet رسمي موجود جوه مكتبة `pyfiglet` نفسها، فمفيش أي اعتماد على ملفات خطوط خارجية). لسه بنفس الأسلوب البصري الأحمر بتاع "Zero Trace".

### 2️⃣ Subdomain Discovery & Liveness Filtering

- **Passive Enumeration:** سحب كل الـ subdomains من سجلات Certificate Transparency عبر `crt.sh` — من غير أي probing مباشر للهدف في المرحلة دي.
- **Liveness Filtering:** فحص كل subdomain اتكشف بـ HTTP/HTTPS request متوازي (Thread Pool)، وإرجاع بس اللي بيرد فعلياً (status code + server header)، زي فلسفة أدوات `httpx`.
- **الحفظ قبل الإرسال للـ AI:** بيتحفظلك ملفين منفصلين — `*_subdomains_all.txt` (كل حاجة اتكشفت) و `*_subdomains_alive.txt` (الشغالة بس) — عشان تراجعهم بنفسك قبل ما تتبعت للـ AI.

### 3️⃣ Web Layer & OWASP Top 10 Active Scan Suite

لو الهدف فاتح منفذ ويب (80/443)، بيحصل الآتي بالتوالي:

- **Passive Reconnaissance:** سحب HTTP Headers، فحص Security Misconfigurations (`CSP`, `HSTS`, `X-Frame-Options`)، وقراءة أول جزء من الـ HTML Source Code والـ Allowed Methods.
- **Active Execution Suite** (الموديول `exploit_suite.py`):
  - **SQLMap:** `--forms --batch --level=1 --risk=1` لاكتشاف حقن SQL في النماذج (OWASP A03 - Injection).
    - **Deep Session Parsing *(جديد v2.0.0)*:** بدل ما نعتمد بس على `stdout` بتاع sqlmap (اللي بيبان في التيرمينال)، الأداة دلوقتي بتفتح فعليًا ملف الـ `log` اللي sqlmap بيكتبه جوه `--output-dir` لكل هدف، وتستخرج منه كل injection point بشكل منظم (Parameter, Place, Type, Title, Payload) عبر regex parsing. ده بيدي للـ AI تفاصيل أدق بكتير من مجرد سطر "is vulnerable" مقتطع من الـ stdout.
  - **Dirsearch:** Brute-force للمسارات لاكتشاف ملفات/مسارات حساسة متروكة (OWASP A01/A05 - Broken Access Control / Security Misconfiguration).
  - **Nuclei:** تشغيل ضد آلاف الـ Templates المرتبطة بـ CVEs وتصنيفات OWASP لاكتشاف الثغرات الحرجة الفورية (XSS, SSRF, misconfig, إلخ).
  - كل أداة بتشتغل جوا `try/except` مستقلة — لو أداة فشلت أو مش متثبتة، الباقي يكمل عادي، ومفيش توقف كامل للفحص.
  - كل مخرجات الأدوات بتتحفظ Raw على الديسك (`owasp/sqlmap/`, `owasp/dirsearch/`, `owasp/nuclei/`) + ملخص JSON موحد (`combined_summary.json`) قبل ما يتبعتوا للـ AI.

### 4️⃣ AI Orchestration Engine *(Provider اتغيّر مرتين: v2.0.0 ثم v2.1.0)*

البيانات المجمّعة من Nmap + Subdomain Enum + Web Analyzer + SQLMap/Dirsearch/Nuclei بتتنضف وتتمرر لموديل **Google AI Studio (Gemini)** بالـ Streaming.

> **تحديث v2.0.0 (تاريخي):** الأداة اتنقلت وقتها من Groq لـ Anthropic Claude.
>
> **تحديث v2.1.0 (الحالي):** الأداة اتنقلت تاني، هذه المرة من Anthropic Claude لـ **Google AI Studio (Gemini API)** عبر مكتبة `google-genai` الرسمية. السبب الأساسي: Google AI Studio بيوفر **free tier فعلي من غير كارت ائتمان**، وكمان **context window أكبر بكتير** بيستحمل براحة البرومبت الكبير اللي الأداة بتبعته (نتائج nmap + subdomains + web + SQLMap/Dirsearch/Nuclei مع بعض في رسالة واحدة)، خصوصًا مع `--full-scan` أو أهداف فيها subdomains كتير. الموديل الافتراضي دلوقتي هو **`gemini-flash-latest`** (متاح على الـ free tier، توازن قوي بين الجودة والسرعة). تقدر تستخدم `--model gemini-pro-latest` لو محتاج عمق تحليل أكبر (الموديل ده مش متاح على الـ free tier، محتاج billing مفعّل)، أو `--model gemini-flash-lite-latest` للفحوصات السريعة/الـ bulk scans الكبيرة (أعلى rate limit على الـ free tier). زي ما كان الحال مع Anthropic، الـ instructions لسه متفصلة في system instruction منفصل بدل حشرها في رسالة الـ user، والـ temperature لسه `0.2` عشان يقلل من احتمالية إن الموديل "يهلوس" ثغرات أو تفاصيل مش موجودة فعليًا في بيانات الفحص.
>
> ⚠️ **ملحوظة مهمة عن الـ free tier:** حدود الطلبات/التوكنز المجانية بتاعة جوجل بتتغيّر مع الوقت ومربوطة بالـ Google Cloud *project* مش بالـ API key نفسه. لو واجهت خطأ `429`/quota exhausted في فحص bulk كبير، راجع الحدود الحية بتاعتك على aistudio.google.com، أو قلل `--threads` وزوّد `--delay` شوية.
>
> **تحديث مصاحب في `main.py`:** لو استدعاء الـ AI فشل (مفتاح غلط، quota خلصت، rate limit، إلخ)، التقرير بقى بيوضّح ده صراحة بقسم `⚠️ AI Analysis Unavailable` بدل ما نص الخطأ الخام يترمي جوه التقرير كإنه finding عادي — بيانات الفحص الخام لسه بتتحفظ في كل الأحوال، وإعادة تشغيل نفس الهدف بترجع من الـ cache وتعيد بس خطوة الـ AI.

التقرير بيتطلع بثلاث صيغ دلوقتي:
- **Streaming حي في التيرمينال** (Markdown منسق برموز 🚨🌐🕳️🛠️📋🔒) — بيتعطّل تلقائيًا وقت الـ parallel bulk scanning (`--threads > 1`) عشان مايحصلش تداخل بين مخرجات أكتر من هدف في نفس الوقت.
- **ملف HTML** بستايل **"Zero Trace // Red Team"** الجديد *(اتغيّر بالكامل في v2.0.0)* — خلفية سودة، لون أحمر قوي بدل الأخضر النيون القديم، ولون فضي للعناصر المحايدة، مطابق لهوية المشروع البصرية (الـ brand mark)، بيتحفظ في `./reports/`.
- **ملف PDF *(جديد بالكامل v2.0.0)*** — نفس تصميم الـ HTML بالظبط، بيتولّد تلقائيًا جنب كل تقرير HTML عبر مكتبة `weasyprint`، وبيتقدر يتعطّل بـ `--no-pdf`.

---

## ⚡ Extra Features

- **Session Management & State Persistence:** ملف كاش JSON منفصل لكل هدف بـ MD5 hashing في `/tmp/.zt_sessions/`، مع كتابة Atomic تمنع تلف الملف لو الأداة اتقفلت فجأة. لو الفحص وقف، بيكمل من آخر نقطة (Ports → Infra → Subdomains → Web → OWASP Suite) من غير إعادة كل حاجة.
- **Rate Limiting & Throttling:** `--delay` بيتحكم في الفاصل الزمني بين كل مرحلة ومرحلة (Nmap phases, Subdomain probing, OWASP tools) لمحاكاة سلوك بشري وتخطي الـ Rate Limiters.
- **Bulk Scanning + Parallelism *(اتطوّر في v2.0.0)*:** ملف نصي فيه مئات الأهداف عبر `-f` / `--file`. دلوقتي تقدر كمان تحدد `--threads N` عشان تفحص عدة أهداف **في نفس الوقت فعليًا** (مش بس جوا subdomain probing زي قبل كده)، وكل thread بيبني له `NetworkScanner` و`AIEngine` مستقلين تمامًا عشان يتجنب أي تضارب بيانات (race conditions) بين الأهداف.
- **Interactive CLI Dashboard:** واجهة Rich بالكامل، مع ASCII Banner ديناميكي (`pyfiglet`) بيطبع اسم الأداة أول ما تشتغل، بالإضافة لـ Live Spinner أثناء كل مرحلة فحص طويلة.
- **Compliance Mapping:** الـ AI بيتم توجيهه (Prompt Engineering) لربط كل ثغرة بـ OWASP Top 10 و NIST CSF/CIS.
- **Selective Scanning:** `--no-subdomains`، `--no-owasp`، و `--no-pdf` *(جديد)* لتعطيل أي مرحلة أو مخرج مش محتاجه في فحص معين.
- **Configurable Port Coverage *(جديد)*:** `--ports` و `--full-scan` بيتحكموا في نطاق البورتات اللي بتتفحص، بدل الاقتصار على الرينج الافتراضي `1-1024` بس (تفاصيل كاملة في قسم الـ Flags تحت).

---

# 🚀 ZT-RECON: Installation & Usage Guide

## 📋 المتطلبات الأساسية

- توزيعة دبيان (Ubuntu / Kali Linux).
- صلاحيات Root/Sudo.
- مفتاح API **مجاني بالكامل** من منصة **Google AI Studio**.

## 🔑 الخطوة 1: الحصول على Google AI Studio API Key

1. ادخل على aistudio.google.com وسجّل دخول بحساب Google عادي (من غير كارت ائتمان).
2. من الصفحة الرئيسية: **Get API Key → Create API Key**.
3. انسخ المفتاح (بيبدأ عادةً بـ `AIza`) واحتفظ بيه.

## 🛠️ الخطوة 2: تحميل المشروع

```bash
git clone https://github.com/ahmed-samy-h/ZT-Recon.git
cd ZT-Recon
```

## 📦 الخطوة 3: التثبيت المؤتمت

```bash
chmod +x install.sh
sudo ./install.sh
```

السكربت هيعمل:
- ينشئ `/opt/zt-recon` ويثبت فيه المشروع.
- يثبت `nmap`, `sqlmap`, `dirsearch`، مكتبات بايثون (`rich`, `google-genai`, `markdown`, `dnspython`, `pyfiglet`, `weasyprint`)، بالإضافة لمكتبات النظام اللي محتاجها `weasyprint` لتصدير الـ PDF (`libpango`, `libcairo`, إلخ).
- يحمّل ويفعّل **Nuclei v3.3.8** + أكتر من 4000 قالب OWASP.
- يربط الأداة بـ Symbolic Link عالمي: `zt-recon`.

## 🔐 الخطوة 4: إعداد مفتاح الذكاء الاصطناعي

أول تشغيل، الأداة هتطلب مفتاح Google AI Studio وتحفظه بشكل ثابت في `/opt/zt-recon/.google_api_key` (بصلاحيات 600) — مش هتتسأل تاني حتى مع تغيير اليوزر أو استخدام sudo.

## 🎯 الخطوة 5: كل الـ Flags المتاحة في الأداة (Full CLI Reference)

قبل أوامر الاستخدام السريعة، خلّينا نوضح **كل flag موجود في الأداة دلوقتي**، بيعمل إيه بالظبط، وإمتى تستخدمه:

- **`-t` / `--target`**
  بتحدد هدف واحد بس (IP أو Domain) عشان تفحصه. ده الاستخدام الأساسي لو عندك هدف واحد بس تحت الاختبار.
  مثال: `sudo zt-recon -t example.com`

- **`-f` / `--file`**
  بدل ما تحدد هدف واحد، بتديله مسار ملف نصي فيه قايمة أهداف (كل هدف في سطر منفصل)، وبيفحصهم كلهم بالتتابع (أو بالتوازي لو ضفت `--threads`). مفيد جدًا في الـ Bulk Scanning لو عندك نطاق كامل (scope) فيه أكتر من دومين/IP.
  مثال: `sudo zt-recon -f targets.txt`

- **`--delay`**
  بتحدد قد إيه الأداة تستنى (بالثواني) بين كل مرحلة فحص والتانية (بين مراحل Nmap، وبين probing الـ subdomains، وبين أدوات الـ OWASP suite). الهدف منها **Rate Limiting** — تبطئة الفحص عمدًا عشان تحاكي سلوك بشري طبيعي وتتفادى إنك تتكشف أو تتحظر بواسطة أنظمة الحماية (WAF/IDS) اللي بتراقب معدل الطلبات. القيمة الافتراضية `2.0` ثانية.
  مثال: `sudo zt-recon -t example.com --delay 2.5`

- **`--model`**
  بتحدد أي موديل من موديلات Google AI Studio (Gemini) يتستخدم في مرحلة التحليل الذكي (AI Analysis). القيمة الافتراضية هي `gemini-flash-latest` (متاح على الـ free tier، توازن قوي بين الجودة والسرعة). البدائل المتاحة:
  - `gemini-pro-latest` — تحليل أعمق وأدق، بس أبطأ ومش متاح على الـ free tier (محتاج billing مفعّل)، مناسب للأهداف الحساسة أو المعقدة اللي محتاجة استنتاج دقيق جدًا.
  - `gemini-flash-lite-latest` — أسرع موديل وأعلى rate limit على الـ free tier، مناسب لفحوصات سريعة أو الـ bulk scans اللي فيها عدد كبير من الأهداف ومحتاج نتيجة سريعة بدون تعمق زيادة.
  مثال: `sudo zt-recon -t example.com --model gemini-pro-latest`

- **`--no-subdomains`**
  بيلغي مرحلة اكتشاف الـ Subdomains بالكامل (يعني `subdomain_enum.py` مش هيتشغل خالص). مفيد لو الهدف IP مش domain أصلاً (وقتها المرحلة دي هتتخطى تلقائيًا برضو)، أو لو محتاج تسرّع الفحص وموضوع الـ subdomains مش مهم في السياق ده.

- **`--no-owasp`**
  بيلغي ترسانة الفحص النشط بالكامل (SQLMap + Dirsearch + Nuclei). مفيد جدًا لو عايز **فحص سلبي/استطلاعي بس** (Recon فقط من غير أي محاولة استغلال فعلية)، أو لو الهدف حساس ومش عايز تعمل أي active scanning عليه دلوقتي، أو بس عايز تجرب سرعة باقي المراحل.

- **`--no-pdf`**
  بيلغي تصدير نسخة الـ PDF من التقرير، وبيسيب بس نسخة الـ HTML (اللي بتتولّد دايمًا مهما كانت باقي الخيارات). مفيد لو مش محتاج ملف PDF فعليًا وعايز توفر وقت التحويل (خصوصًا إن `weasyprint` بياخد وقت إضافي في التحويل من HTML لـ PDF).

- **`--report-dir`**
  بتحدد المسار (الفولدر) اللي هيتحفظ فيه ملفات التقرير (HTML و PDF). القيمة الافتراضية `./reports` (يعني فولدر `reports` جوه المكان اللي إنت شغّال منه الأمر). مفيد لو عايز تنظّم التقارير بتاعتك في مكان تاني، أو لو بتشتغل على أكتر من مشروع/عميل وعايز تفصل التقارير بينهم.
  مثال: `sudo zt-recon -t example.com --report-dir /home/user/client_x_reports`

- **`--ports` *(جديد)***
  بتحدد نطاق أو قايمة البورتات اللي هيتفحصوا، بنفس الـ syntax اللي nmap بتفهمه في خيار `-p`. القيمة الافتراضية `1-1024` (الـ Well-Known Ports بس — سريع). تقدر تحط:
  - رينج كامل: `--ports 1-65535` (فحص شامل لكل البورتات).
  - قايمة محددة: `--ports 22,80,443,3306,6379`.
  - مزيج من رينج + بورتات إضافية: `--ports "1-1024,3306,8080,8443,9200,27017"`.
  مهم تعرف إن رينج أوسع = وقت فحص أطول بكتير، فاختار حسب الوقت المتاح والهدف من الفحص.

- **`--full-scan` *(جديد)***
  اختصار جاهز وسريع بدل ما تكتب `--ports 1-65535` يدويًا في كل مرة. بيعمل فحص كامل لكل الـ 65535 بورت، فبيضمن إنك مش هتفوّت أي خدمة شغالة على بورت غير تقليدي (زي قواعد البيانات أو admin panels على بورتات عالية). أبطأ بكتير من الفحص الافتراضي، فاستخدمه لما تكون محتاج **تغطية كاملة** مش سرعة.
  > ملحوظة: لو استخدمت `--ports` و `--full-scan` مع بعض في نفس الأمر، الأداة بتدّي الأولوية لـ `--ports` لأنه الخيار الأكثر تحديدًا (explicit)، ويتم تجاهل `--full-scan`.

- **`--threads`**
  بتحدد عدد الأهداف اللي هيتفحصوا **بالتوازي فعليًا** وقت استخدام `-f` (بيانات متعددة). القيمة الافتراضية `1` يعني تسلسلي (هدف بعد هدف، زي السلوك الأصلي قبل v2.0.0). لو حطيت رقم أكبر من 1 (مع وجود أكتر من هدف في الملف)، الأداة هتفحص عدد الأهداف ده في نفس الوقت باستخدام `ThreadPoolExecutor`، وكل thread بيبني له نسخة مستقلة تمامًا من الـ Scanner والـ AI Engine (زي ما اتشرح في القسم التقني فوق) عشان يتفادى تضارب البيانات.
  > ملحوظة مهمة: زيادة `--threads` بتزوّد الحمل على شبكتك وعلى الهدف في نفس الوقت، وبتقلل فعليًا من تأثير الـ `--delay` بتاعك (لأن كذا هدف بيبعتوا طلبات في نفس اللحظة)، فاستخدمها بحذر لو الهدف فيه Rate Limiting أو WAF حساس.
  مثال: `sudo zt-recon -f targets.txt --threads 5`

### أمثلة استخدام مجمّعة

```bash
# فحص هدف واحد (كل المراحل: Network + Subdomains + Web + OWASP Suite + AI + HTML/PDF)
sudo zt-recon -t example.com

# فحص متخفي مع تأخير أطول بين المراحل
sudo zt-recon -t example.com --delay 2.5

# فحص دفعة أهداف (تسلسلي، الوضع الافتراضي)
sudo zt-recon -f /path/to/targets.txt

# فحص دفعة أهداف بالتوازي (5 أهداف في نفس الوقت)
sudo zt-recon -f /path/to/targets.txt --threads 5

# استخدام موديل تحليل مختلف (أعمق أو أسرع)
sudo zt-recon -t example.com --model gemini-pro-latest
sudo zt-recon -t example.com --model gemini-flash-lite-latest

# تخطي فحص الـ Subdomains أو ترسانة OWASP أو تصدير الـ PDF
sudo zt-recon -t example.com --no-subdomains --no-owasp --no-pdf

# فحص شامل لكل الـ 65535 بورت بدل الرينج الافتراضي السريع
sudo zt-recon -t example.com --full-scan

# رينج بورتات مخصص: السريع + بورتات قواعد بيانات وadmin panels شائعة
sudo zt-recon -t example.com --ports "1-1024,3306,5432,6379,8080,8443,9200,27017"

# تحديد فولدر مخصص لحفظ التقارير
sudo zt-recon -t example.com --report-dir /home/user/reports/client_x

# دمج أكتر من خيار مع بعض
sudo zt-recon -f targets.txt --threads 3 --full-scan --model gemini-pro-latest --report-dir ./client_reports
```

## 📊 الخطوة 6: استلام التقرير النهائي

- تقرير حي Streaming في التيرمينال بالأقسام: 🚨 CRITICAL FINDINGS، 🌐 WEB LAYER، 🕳️ VULNERABILITY DETAILS، 🛠️ VERIFICATION COMMANDS، 📋 COMPLIANCE MAPPING، 🔒 REMEDIATION.
- ملف HTML بستايل **Zero Trace // Red Team** محفوظ في `./reports/<target>_report.html`.
- ملف **PDF** مطابق لنفس التقرير محفوظ جنبه في `./reports/<target>_report.pdf`.

---

## 🔄 تحديث الأداة (Updating an Existing Install)

بما إن المشروع منشور على GitHub، أي حد نزّل الأداة قبل كده ومحتاج ياخد آخر تحديثات (زي التحديث لـ v2.0.0) يعمل ببساطة:

```bash
cd ZT-Recon          # ادخل نفس مجلد الـ clone اللي عندك
git pull origin main  # اسحب آخر تحديثات الكود من GitHub
chmod +x install.sh
sudo ./install.sh     # يعيد نسخ الملفات لـ /opt/zt-recon ويحدث مكتبات بايثون
```

أو ببساطة أكتر لو الـ repo فيه `update.sh` (سكربت بيعمل نفس الخطوتين دول تلقائيًا):

```bash
sudo ./update.sh
```

> ⚠️ **ملحوظة مهمة لأول تحديث لـ v2.1.0 تحديدًا:** الأداة اتنقلت من Anthropic Claude لـ Google AI Studio (Gemini)، واسم ملف حفظ المفتاح نفسه اتغيّر (`.anthropic_api_key` → `.google_api_key`). يعني أول تشغيل بعد التحديث، الأداة **هتطلب منك مفتاح Google AI Studio جديد** (`AIza...`، مجاني بالكامل من aistudio.google.com) حتى لو كان عندك مفتاح Anthropic قديم متخزن قبل كده — ده سلوك متوقع ومش خطأ، ومفتاح Anthropic القديم بيفضل موجود على الجهاز من غير استخدام، تقدر تمسحه يدويًا لو حابب.

> ⚠️ **ملحوظة تاريخية (أول تحديث لـ v2.0.0):** الأداة كانت اتنقلت وقتها من Groq لـ Anthropic، واسم ملف حفظ المفتاح اتغيّر (`.groq_api_key` → `.anthropic_api_key`). الملاحظة دي محفوظة هنا لتوثيق تاريخ تطور المشروع بس، مفيش أي تأثير عملي منها دلوقتي بعد الانتقال لـ v2.1.0.

---