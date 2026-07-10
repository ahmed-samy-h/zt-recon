# 📝 TECHNICAL WRITEUP & ARCHITECTURE REPORT: ZT-RECON

### **Project Status: Active Development, Educational & Practical Application**

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
- **Service & OS Fingerprinting:** استخراج إصدارات الخدمات وأنظمة التشغيل (`-sV -O`).

### 2️⃣ Subdomain Discovery & Liveness Filtering *(جديد)*

- **Passive Enumeration:** سحب كل الـ subdomains من سجلات Certificate Transparency عبر `crt.sh` — من غير أي probing مباشر للهدف في المرحلة دي.
- **Liveness Filtering:** فحص كل subdomain اتكشف بـ HTTP/HTTPS request متوازي (Thread Pool)، وإرجاع بس اللي بيرد فعلياً (status code + server header)، زي فلسفة أدوات `httpx`.
- **الحفظ قبل الإرسال للـ AI:** بيتحفظلك ملفين منفصلين — `*_subdomains_all.txt` (كل حاجة اتكشفت) و `*_subdomains_alive.txt` (الشغالة بس) — عشان تراجعهم بنفسك قبل ما تتبعت للـ AI.

### 3️⃣ Web Layer & OWASP Top 10 Active Scan Suite *(جديد بالكامل)*

لو الهدف فاتح منفذ ويب (80/443)، بيحصل الآتي بالتوالي:

- **Passive Reconnaissance:** سحب HTTP Headers، فحص Security Misconfigurations (`CSP`, `HSTS`, `X-Frame-Options`)، وقراءة أول جزء من الـ HTML Source Code والـ Allowed Methods.
- **Active Execution Suite** (الموديول الجديد `exploit_suite.py`):
  - **SQLMap:** `--forms --batch --level=1 --risk=1` لاكتشاف حقن SQL في النماذج (OWASP A03 - Injection).
  - **Dirsearch:** Brute-force للمسارات لاكتشاف ملفات/مسارات حساسة متروكة (OWASP A01/A05 - Broken Access Control / Security Misconfiguration).
  - **Nuclei:** تشغيل ضد آلاف الـ Templates المرتبطة بـ CVEs وتصنيفات OWASP لاكتشاف الثغرات الحرجة الفورية (XSS, SSRF, misconfig, إلخ).
  - كل أداة بتشتغل جوا `try/except` مستقلة — لو أداة فشلت أو مش متثبتة، الباقي يكمل عادي، ومفيش توقف كامل للفحص.
  - كل مخرجات الأدوات بتتحفظ Raw على الديسك (`owasp/sqlmap/`, `owasp/dirsearch/`, `owasp/nuclei/`) + ملخص JSON موحد (`combined_summary.json`) قبل ما يتبعتوا للـ AI.

### 4️⃣ AI Orchestration Engine

البيانات المجمّعة من Nmap + Subdomain Enum + Web Analyzer + SQLMap/Dirsearch/Nuclei بتتنضف وتتمرر لنموذج **`openai/gpt-oss-120b`** عبر **Groq API** بالـ Streaming.

> **تحديث مهم:** Groq عمل deprecate لـ `llama-3.3-70b-versatile` (اللي كان مستخدم قبل كده) في 17 يونيو 2026. البديل الرسمي المقترح للمهام دي هو `openai/gpt-oss-120b` (الافتراضي دلوقتي)، وتقدر تجرب `moonshotai/kimi-k2-instruct-0905` لو محتاج جودة تحليل أعلى على حساب سرعة أقل، عن طريق `--model`.

التقرير بيتطلع بصيغتين:
- **Streaming حي في التيرمينال** (Markdown منسق برموز 🚨🌐🕳️🛠️📋🔒).
- **ملف HTML منسق** بستايل "Zero Trace" (خلفية سودة، نيون أخضر، Grid خفيف) بيتحفظ في `./reports/`.

---

## ⚡ Extra Features

- **Session Management & State Persistence:** ملف كاش JSON منفصل لكل هدف بـ MD5 hashing في `/tmp/.zt_sessions/`، مع كتابة Atomic تمنع تلف الملف لو الأداة اتقفلت فجأة. لو الفحص وقف، بيكمل من آخر نقطة (Ports → Infra → Subdomains → Web → OWASP Suite) من غير إعادة كل حاجة.
- **Rate Limiting & Throttling:** `--delay` بيتحكم في الفاصل الزمني بين كل مرحلة ومرحلة (Nmap phases, Subdomain probing, OWASP tools) لمحاكاة سلوك بشري وتخطي الـ Rate Limiters.
- **Bulk Scanning:** ملف نصي فيه مئات الأهداف عبر `-f` / `--file`، وكل هدف بجلسته المستقلة.
- **Interactive CLI Dashboard:** واجهة Rich بالكامل، مع ASCII Banner ديناميكي (`pyfiglet`) بيطبع اسم الأداة أول ما تشتغل.
- **Compliance Mapping:** الـ AI بيتم توجيهه (Prompt Engineering) لربط كل ثغرة بـ OWASP Top 10 و NIST CSF/CIS.
- **Selective Scanning:** `--no-subdomains` و `--no-owasp` لتعطيل أي مرحلة مش محتاجها في فحص معين.

---

# 🚀 ZT-RECON: Installation & Usage Guide

## 📋 المتطلبات الأساسية

- توزيعة دبيان (Ubuntu / Kali Linux).
- صلاحيات Root/Sudo.
- مفتاح API مجاني من منصة **Groq Cloud Console**.

## 🔑 الخطوة 1: الحصول على Groq API Key

1. ادخل على Groq Cloud Console وسجّل حساب.
2. من القائمة الجانبية: **API Keys → Create API Key**.
3. انسخ المفتاح (يبدأ بـ `gsk_`) واحتفظ بيه.

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
- يثبت `nmap`, `sqlmap`, `dirsearch`, و مكتبات بايثون (`rich`, `groq`, `markdown`, `dnspython`, `pyfiglet`).
- يحمّل ويفعّل **Nuclei v3.3.8** + أكتر من 4000 قالب OWASP.
- يربط الأداة بـ Symbolic Link عالمي: `zt-recon`.

## 🔐 الخطوة 4: إعداد مفتاح الذكاء الاصطناعي

أول تشغيل، الأداة هتطلب المفتاح وتحفظه بشكل ثابت في `/opt/zt-recon/.groq_api_key` (بصلاحيات 600) — مش هتتسأل تاني حتى مع تغيير اليوزر أو استخدام sudo.

## 🎯 الخطوة 5: أوامر الاستخدام

```bash
# فحص هدف واحد (كل المراحل: Network + Subdomains + Web + OWASP Suite + AI)
sudo zt-recon -t example.com

# فحص متخفي مع تأخير بين المراحل
sudo zt-recon -t example.com --delay 2.5

# فحص دفعة أهداف
sudo zt-recon -f /path/to/targets.txt

# استخدام موديل تحليل مختلف
sudo zt-recon -t example.com --model moonshotai/kimi-k2-instruct-0905

# تخطي فحص الـ Subdomains أو ترسانة OWASP لو مش لازمة
sudo zt-recon -t example.com --no-subdomains --no-owasp
```

## 📊 الخطوة 6: استلام التقرير النهائي

- تقرير حي Streaming في التيرمينال بالأقسام: 🚨 CRITICAL FINDINGS، 🌐 WEB LAYER، 🕳️ VULNERABILITY DETAILS، 🛠️ VERIFICATION COMMANDS، 📋 COMPLIANCE MAPPING، 🔒 REMEDIATION.
- ملف HTML منسق بستايل Zero Trace محفوظ في `./reports/<target>_report.html`.

---

## 🧩 اللي لسه ممكن يتطور (Next Steps)

- تفعيل خيار nuclei templates مخصصة (`-tags` / `-severity`) بدل التشغيل الافتراضي بكل القوالب.
- إضافة parsing أعمق لمخرجات sqlmap (قراءة الـ session files بتاعته بدل الـ stdout بس).
- دعم export التقرير كـ PDF جنب HTML.
- تفعيل multi-threading على مستوى الأهداف نفسها في Bulk Scanning (مش بس داخل subdomain probing).
