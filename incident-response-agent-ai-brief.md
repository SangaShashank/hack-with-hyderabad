# PROJECT BRIEF: Incident Response Agent (Hindsight Memory)
### For: AI coding assistants (Claude Code, Codex, Cursor, etc.) picking up this project cold

**Read this entire document before writing any code.** It contains the full context, decisions already made, and the build plan. Do not ask the human to re-explain what's below — everything needed to start is here. If something genuinely isn't covered, ask a single specific question rather than guessing.

---

## 1. What this project is

We are building an **Incident Response Agent** for a hackathon (Hack with Hyderabad 3.0, ~25,000 participants). The agent uses **Hindsight** (a memory system by Vectorize) to remember past production incidents and get faster/smarter at diagnosing recurring ones over time.

**Locked problem statement (do not change without asking):**
> "An on-call assistant for a microservices backend that remembers every past production incident — symptoms, root cause, and fix — so recurring failures get diagnosed instantly instead of from scratch, cutting mean-time-to-resolution."

**The core idea in one sentence:** When a new incident comes in, the agent checks memory first. If it recognizes the pattern, it instantly surfaces the past root cause and fix. If not, it reasons from scratch with an LLM, then *retains* the resolution so it recognizes it next time.

**Why this project exists (context, not to be repeated to the human unless asked):** This is a hackathon requiring all teams to build using Hindsight. Judging weights: Innovation 30%, Use of Hindsight Memory 25%, Technical Implementation 20%, UX 15%, Real-world Impact 10%. The memory mechanism (retain/recall) must be the central, visible mechanic — not a bolted-on feature.

---

## 2. Required technology

- **Memory layer:** Hindsight (Vectorize). Cloud instance at https://ui.hindsight.vectorize.io, or self-hosted open source (https://github.com/vectorize-io/hindsight). Docs: https://hindsight.vectorize.io/
- **LLM:** Groq recommended (fast, generous free tier) — https://groq.com. Recommended models: `openai/gpt-oss-120b` or `qwen/qwen3-32b`. **Must handle function-calling errors gracefully** — these models are known to occasionally fail tool calls; always wrap in try/catch with a fallback.
- **Promo code `MEMHACK99`** gives $50 in free Hindsight Cloud credits — apply it in the billing section after registering (human's job, not yours, unless asked to script it).
- Any coding agent/stack is fine otherwise — default to **Python** unless the human specifies otherwise, since it has the most mature SDK examples for this kind of agent work. Ask if unsure.

---

## 3. Data model

Each "incident" is a structured record:

```json
{
  "incident_id": "INC-0001",
  "service": "payments-api",
  "symptom": "500 errors spiking, latency > 5s",
  "error_signature": "ConnectionPoolTimeoutError: pool exhausted after 30000ms",
  "root_cause": "DB connection pool size too low for traffic spike during batch job",
  "fix_applied": "Increased pool size from 10 to 50, added circuit breaker",
  "timestamp": "2026-09-20T03:14:00Z"
}
```

### Failure families to implement (5 total, 2–3 variants each = 10–15 synthetic incidents)

1. **Database connection pool exhaustion** — under traffic spikes, in different services.
2. **Memory leak in a service** — gradual OOM crash, different services/root causes (unclosed connections, growing cache, etc.).
3. **Misconfigured environment variable** causing a crash loop right after deploy.
4. **Downstream API timeout cascading** into multiple dependent services.
5. **Disk space exhaustion** from unrotated logs (optional 5th family if time allows; 4 families is acceptable minimum).

Write these as realistic-looking stack traces / log lines / alert text — not placeholder strings. Realism matters more than volume. If you (the AI) are asked to generate this dataset, write it directly into a file like `data/incidents.json` or `.jsonl`, one incident per record, following the schema above, and vary service names realistically (e.g. `payments-api`, `orders-api`, `auth-service`, `notifications-worker`).

---

## 4. Core architecture

### Retain/Recall flow (this IS the product — implement carefully)

```
function handle_incident(new_incident):
    matches = hindsight.recall(query=new_incident.error_signature, context=new_incident.service)

    if matches is not empty and top_match.similarity is high enough:
        response = format_response(
            "Seen this before. Root cause: {match.root_cause}. Fix that worked: {match.fix_applied}.",
            confidence="high",
            source="memory"
        )
        return response   # THIS IS THE "FAST PATH" — the demo's key moment

    else:
        diagnosis = llm.reason_from_scratch(new_incident)   # "SLOW PATH"
        # Simulate the engineer confirming the real fix, or auto-accept the LLM's diagnosis:
        hindsight.retain(
            content=new_incident + diagnosis,
            metadata={"service": new_incident.service, "error_signature": new_incident.error_signature}
        )
        return diagnosis
```

**Important nuance to implement:** support a *partial match* case — a new incident that's similar but not identical to a past one (e.g. same failure family, different service). The agent should recognize the pattern and adapt the fix to the new context, not just parrot the old answer verbatim. This is a strong technical/innovation signal — prioritize it if time allows.

### Suggested project structure

```
/agent
  main.py              # orchestrates the retain/recall/LLM loop
  hindsight_client.py  # wraps Hindsight SDK calls (retain, recall)
  llm_client.py        # wraps Groq API calls, includes error handling/retries
  incidents.py         # loads synthetic dataset
/data
  incidents.json       # the synthetic dataset (see Section 3)
/demo
  app.py or index.html # simple interface — see Section 5
README.md
.env.example           # HINDSIGHT_API_KEY, GROQ_API_KEY placeholders
```

### Build order (do not skip steps — each should be verified working before the next)

1. Hard-code ONE incident, call `hindsight.retain()`, confirm it appears in the Hindsight Cloud dashboard.
2. Call `hindsight.recall()` for that same incident, confirm the record comes back.
3. Wire in the LLM: feed recalled memory into the prompt so the response explicitly references the past incident (not just raw retrieved data).
4. Add the "no match found" path: LLM reasons from scratch, then the result is retained.
5. Add the partial-match / pattern-adaptation case (Section 4 nuance above).
6. Load the full synthetic dataset (Section 3) and run through the planned demo sequence end-to-end (see Section 6).

---

## 5. Demo interface requirements

Keep it simple and clear over feature-rich. Minimum viable:

- An incident feed / input area (can be as simple as selecting from the synthetic dataset in order).
- The agent's response area, **clearly tagged** as either:
  - 🧠 "Recalled from memory" (fast path), or
  - 🔍 "New diagnosis" (slow path)
- A visible counter: "Incidents resolved instantly via memory: X" — this single UI element does a lot of work to make the memory story land visually for judges.

A single self-contained HTML file with a lightweight backend (or client-side only, if Hindsight/Groq calls can be proxied) is acceptable. A polished UI is not required — clarity is required.

---

## 6. The demo sequence to build toward

The prototype must be able to walk through this exact narrative live:

1. Feed Incident #1 (e.g., DB pool exhaustion in `payments-api`) — no memory exists yet, agent reasons from scratch (slower, visibly "thinking").
2. Feed Incident #2, a **different, unrelated** failure family — same slow path, more memory accumulates.
3. Feed Incident #3 — a **variant** of Incident #1's failure family but in a **different service** (e.g., `orders-api`). Agent should recall the pattern and adapt the fix, not just repeat verbatim.
4. Feed 2–3 more incidents rapidly, showing the "instantly resolved" counter climbing.

If you're asked to help write or refine this script, keep it to 2–5 minutes when narrated aloud — it doubles as the team's video script.

---

## 7. What NOT to do

- Do not build a generic chatbot wrapper with no real retain/recall calls — memory must be functionally load-bearing, not decorative.
- Do not skip the partial-match/pattern-adaptation case if time allows — it's a meaningful differentiator.
- Do not hard-code the "recalled" responses as fake/scripted output — the recall must actually query Hindsight and use its result.
- Do not integrate real production tools (Datadog, PagerDuty, etc.) — this is out of scope; the incidents are simulated/synthetic by design.

---

## 8. If you (the AI) get stuck

- Hindsight SDK/API questions: check https://hindsight.vectorize.io/ first; the Hindsight Community Slack (linked from their docs) is the human's fallback if documentation doesn't resolve it.
- Groq function-calling errors: add retries and a graceful fallback response rather than crashing.
- If a design decision isn't covered here (e.g., exact similarity threshold for a "match"), make a reasonable default choice, note it clearly in a code comment, and flag it to the human rather than blocking.

---

## 9. Definition of done for the prototype

- [ ] `retain()` and `recall()` both work against a live Hindsight instance (not mocked)
- [ ] Full demo sequence (Section 6) runs end-to-end without crashing
- [ ] Partial-match/pattern-adaptation case implemented (or clearly flagged as a stretch goal if time ran out)
- [ ] README explains the problem statement and how Hindsight memory is used
- [ ] Repo is clean enough to be made public

This prototype is one piece of a larger submission (article, video, social post are handled separately by the team) — your job is only the working, demoable code described above.
