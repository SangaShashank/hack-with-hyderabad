# ⚡ Incident Response Agent with Hindsight Long-Term Memory

> **Hack with Hyderabad 3.0 Prototype**  
> *"An on-call assistant for a microservices backend that remembers every past production incident — symptoms, root cause, and fix — so recurring failures get diagnosed instantly instead of from scratch, cutting mean-time-to-resolution (MTTR)."*

---

## 🌟 The Core Mechanism

When production services fail, engineers spend hours diagnosing root causes from scratch—even when the identical failure happened last month in another service. 

This agent uses **Hindsight (by Vectorize)** as an active, biomimetic memory layer paired with **Groq LLMs (`openai/gpt-oss-120b`)** to eliminate redundant troubleshooting:

```
                            [Incoming Incident Alert]
                                       │
                                       ▼
                   ┌───────────────────────────────────────┐
                   │   Hindsight Memory Bank Recall Query  │
                   └───────────────────┬───────────────────┘
                                       │
                ┌──────────────────────┴──────────────────────┐
                ▼                                             ▼
       [ Memory Match Found ]                        [ No Match in Memory ]
                │                                             │
      ┌─────────┴─────────┐                                   │
      ▼                   ▼                                   ▼
 [Same Service]    [Different Service]                  [Slow Path]
  🧠 FAST PATH       🧬 PATTERN ADAPTATION          🔍 FIRST-PRINCIPLES LLM
  Instant Recall     Adapts Fix to New Context       Diagnoses from scratch
 (~1.0s MTTR)       (HikariCP, Canary, Circuit)      & Auto-Retains to Memory
```

---

## 🚀 Key Differentiators

1. **Bi-Directional Memory (Retain & Recall)**: Memory is functionally load-bearing. Novel failures diagnosed by the LLM are automatically consolidated and vectorized into Hindsight Cloud (`api.hindsight.vectorize.io`).
2. **Cross-Service Pattern Adaptation**: When a failure family (e.g. Database Connection Pool Exhaustion) previously seen in `payments-api` strikes `orders-api`, the agent does not parrot the old fix verbatim. It recognizes the structural pattern and adapts the remediation specifically for `orders-api`'s architecture.
3. **Dual Metric Tracking**: Visible real-time tracking of:
   - 🧠 **Incidents Resolved Instantly via Memory**
   - 🧬 **Cross-Service Patterns Adapted**
   - 🔍 **Novel Incidents Diagnosed & Retained**

---

## 📁 Project Architecture

```
├── agent/
│   ├── hindsight_client.py  # Wraps official hindsight-client SDK (retain, recall, session management)
│   ├── llm_client.py        # Groq client (openai/gpt-oss-120b) with model fallback & structured outputs
│   ├── main.py              # Orchestrates the Retain/Recall/LLM loop and pattern adaptation logic
│   ├── incidents.py         # Synthetic dataset loader & demo sequence manager
│   ├── run_demo.py          # Automated CLI walkthrough of the Section 6 Hackathon narrative
│   └── verify_step*.py      # Verified standalone test scripts for build order steps 1–5
├── data/
│   └── incidents.json       # 12 realistic incidents across 5 microservice failure families
├── demo/
│   ├── app.py               # Lightweight Python HTTP server hosting REST API endpoints
│   └── index.html           # Dark-mode dashboard with live telemetry feed & console
├── .env.example             # Template for API keys
└── README.md                # Project documentation
```

---

## 🛠️ Quick Start

### 1. Prerequisites
- Python 3.10+
- Hindsight Cloud API Key ([Hindsight UI](https://ui.hindsight.vectorize.io))
- Groq API Key ([Groq Console](https://groq.com))

### 2. Installation
```bash
git clone <repo-url>
cd jsss

# Install dependencies
pip install hindsight-client groq python-dotenv
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Fill in your API keys in `.env`:
```ini
HINDSIGHT_API_KEY=hsk_...
GROQ_API_KEY=gsk_...
HINDSIGHT_BASE_URL=https://api.hindsight.vectorize.io
HINDSIGHT_BANK_ID=incident-response-bank
```

---

## 🎬 Running the Demo

### Option A: Interactive Web UI Dashboard
Launch the web console:
```bash
python demo/app.py
```
Open [http://localhost:8080](http://localhost:8080) in your browser:
- Click **"▶ Run Guided Demo Sequence"** to watch the agent automatically walk through novel failures, pattern adaptation, and instant memory recall.
- Or select any individual alert from the **Synthetic Telemetry Feed** on the left.

### Option B: Automated CLI Demo Narrative
Run the complete Hackathon Section 6 narrative directly in your terminal:
```bash
python agent/run_demo.py
```

---

## 📊 Synthetic Failure Families

The repository includes 12 realistic incidents across 5 core failure families (`data/incidents.json`):
1. **Database Connection Pool Exhaustion**: Traffic surges exhausting DB pools (`payments-api`, `orders-api`).
2. **Memory Leak / OOM Crash**: Monotonic heap growth causing container cgroup kill (`auth-service`, `analytics-worker`).
3. **Misconfigured Environment Variables**: Missing secrets and deployment drift causing CrashLoopBackOff (`notifications-worker`, `billing-service`).
4. **Downstream Cascading Timeouts**: Upstream dependency latency exhausting worker sockets (`api-gateway`, `order-fulfillment-api`).
5. **Disk Space Exhaustion**: Broken log rotation or unpurged temp files causing node eviction (`audit-logger`, `legacy-sync-worker`).

---

## 🔒 Security & Best Practices
- All API keys are loaded strictly through environment variables.
- `.env` is listed in `.gitignore` to prevent credential exposure.
- Client sessions and connection pools are managed via clean context managers.
