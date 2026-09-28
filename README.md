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

## 🚀 Version 2: Operator Incident Input & Real Learning Loop

Version 2 upgrades the Incident Response Agent from a static demonstration of 12 predefined synthetic incidents to a **live, bi-directional incident management console** where operators can submit real, arbitrary microservice incidents.

### 🧠 Shared Organizational Memory Model (Hackathon Architecture)
For this hackathon prototype, the application operates as an internal incident-response system for **one simulated organization**:
* **Shared Hindsight Memory Bank**: All browser sessions and operators share the single organizational memory bank (`incident-response-bank`).
* **Continuous Knowledge Accumulation**: Any incident submitted by an operator—once reasoned and diagnosed by Groq—is consolidated and retained into this shared memory layer. Future recurring or structurally similar incidents from any engineer or service immediately benefit from this recalled knowledge.
* **No Authentication / Multi-Tenancy**: To keep the prototype lightweight and focused on agentic memory capabilities, user authentication and multi-tenant isolation are intentionally omitted.
* **Not Local Storage**: Incidents are **never** stored only in browser `localStorage` or fake frontend memory. Everything flows through the real Hindsight Cloud API (`api.hindsight.vectorize.io`).

```
┌────────────────────────────────────────┐     ┌────────────────────────────────────────┐
│   12 Synthetic Seed Incidents (Demo)   │     │      Operator-Submitted Incidents      │
│     (Pre-loaded failure families)      │     │      (Arbitrary live/manual alerts)    │
└───────────────────┬────────────────────┘     └───────────────────┬────────────────────┘
                    │                                              │
                    ▼                                              ▼
    ┌──────────────────────────────────────────────────────────────────────────────────┐
    │              Shared Organizational Hindsight Memory Bank                         │
    │                      (incident-response-bank)                                    │
    └──────────────────────────────────────┬───────────────────────────────────────────┘
                                           │
                                           ▼
            ┌──────────────────────────────────────────────────────────────┐
            │        Future Real-Time Incident Recall & Adaptation         │
            │   🧠 Recalled from memory  |  🧬 Pattern adapted from memory  │
            └──────────────────────────────────────────────────────────────┘
```

### 📋 Distinguishing Data Tiers

| Tier | Source / Storage | Purpose | Modifiability |
| :--- | :--- | :--- | :--- |
| **Demo Seed Dataset** | `data/incidents.json` | 12 fixed benchmark incidents across 5 failure families | Read-only static seed data |
| **Persistent Hindsight Memory** | Hindsight Cloud Bank | Biomimetic long-term memory containing facts, observations, and verified remediations | Dynamically updated via `retain()` |
| **User-Submitted Incidents** | Web Form / API (`/api/handle_incident`) | Real operator incident submissions; auto-assigned collision-free `USER-<timestamp>-<rand>` IDs | Diagnosed live & retained into Hindsight memory |

---

## 🎬 Operator Workflow & Usage

### 1. Manual Incident Analysis via Web UI
In the web dashboard, use the **"Analyze New Incident"** form on the left:
1. **Service** *(Required)*: The affected service (e.g. `billing-processor`).
2. **Error Signature** *(Required)*: The runtime exception or alert string (e.g. `KafkaRebalanceException: partition assignment stalled`).
3. **Symptoms** *(Required)*: Observed symptoms and impact (e.g. `Consumer lag spiked to 250k messages, invoices stuck in pending state`).
4. **Timestamp** *(Optional)*: ISO timestamp; if omitted, the backend generates the current UTC timestamp.
5. Click **"⚡ Analyze Incident"**:
   - The backend generates a collision-free ID: `USER-<timestamp>-<rand>`.
   - The agent executes Hindsight `recall()`.
   - **First Occurrence**: Classified as novel (`🔍 New diagnosis`), Groq diagnoses root cause and remediation, and Hindsight auto-retains it.
   - **Recurrence**: Subsequent submissions of the same incident are resolved instantly via memory (`🧠 Recalled from memory`) in milliseconds!
   - **Cross-Service Variant**: Submissions of the same failure pattern in another service (e.g. `inventory-sync-service`) are recognized and adapted (`🧬 Pattern adapted from memory`).

### 2. Quick-Fill Shortcuts
The UI includes quick-fill buttons (`Novel Incident`, `Repeat (Memory)`, `Cross-Service`) to demonstrate the live 3-stage learning loop in seconds.

---

## 🎬 Running the Application

### Option A: Interactive Web UI Dashboard
Launch the web server:
```bash
python demo/app.py
```
Open [http://localhost:8080](http://localhost:8080) in your browser:
- Submit manual incidents using the **"Analyze New Incident"** form.
- Click **"▶ Run Guided Demo Sequence"** to walk through the 5-event live demonstration.
- Or click any alert in the **Synthetic Telemetry Feed**.

### Option B: Automated CLI Demo Narrative
Run the complete 5-event demonstration in your terminal:
```bash
python agent/run_demo.py
```

---

## 📊 Synthetic Failure Families

The repository includes 12 realistic seed incidents across 5 core failure families (`data/incidents.json`):
1. **Database Connection Pool Exhaustion**: Traffic surges exhausting DB pools (`payments-api`, `orders-api`).
2. **Memory Leak / OOM Crash**: Monotonic heap growth causing container cgroup kill (`auth-service`, `analytics-worker`).
3. **Misconfigured Environment Variables**: Missing secrets and deployment drift causing CrashLoopBackOff (`notifications-worker`, `billing-service`).
4. **Downstream Cascading Timeouts**: Upstream dependency latency exhausting worker sockets (`api-gateway`, `order-fulfillment-api`).
5. **Disk Space Exhaustion**: Broken log rotation or unpurged temp files causing node eviction (`audit-logger`, `legacy-sync-worker`).

---

## 🔒 Security & Best Practices
- All API keys (`HINDSIGHT_API_KEY`, `GROQ_API_KEY`) remain strictly on the backend and are never sent to or exposed in frontend code.
- `.env` is listed in `.gitignore` to prevent credential exposure.
- Client sessions and connection pools are managed via clean context managers.
