<a name="readme-top"></a>

<div align="center">

# 🛡️ CHECKPOINT

### Git for AI Agent Actions

**A safety, observability, and transactional recovery layer for autonomous AI agents.**

Checkpoint sits between an AI agent and its execution environment, intercepting actions, evaluating risk, comparing intent with behavior, observing actual filesystem changes, and enabling human approval and recovery.

<br/>

![Python](https://img.shields.io/badge/Python-Backend-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-Frontend-000000?style=for-the-badge&logo=next.js)
![SQLite](https://img.shields.io/badge/SQLite-Persistence-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Powered by Solari](https://img.shields.io/badge/Powered%20by-Solari%20Sandbox-6C47FF?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

<br/>

> ## Give AI agents autonomy — without giving them unlimited trust.

</div>

---

# 👀 See Checkpoint in Action

<div align="center">

![Checkpoint Dashboard](checkpoint-dashboard.png)

</div>

*Checkpoint monitors agent actions in real time, evaluates risk, records checkpoints, detects intent/action mismatches, and enables human review and recovery.*

---

# ⚡ The Core Idea

Traditional systems often evaluate what an AI agent **intends to do**.

Checkpoint also observes what the agent **actually did**.

```mermaid
flowchart LR

    A["🤖 AI Agent"]

    A --> B["🛡️ Checkpoint"]

    B --> C["🧠 Pre-Action Risk Analysis"]

    C --> D{"Safe to Execute?"}

    D -->|No| E["🚫 BLOCK"]

    D -->|Yes| F["📸 Capture Filesystem State"]

    F --> G["🏖️ Execute in Solari Sandbox"]

    G --> H["🔍 Detect Actual Changes"]

    H --> I["🧠 Post-Action Risk Analysis"]

    I --> J{"Risk Detected?"}

    J -->|No| K["✅ COMPLETE"]

    J -->|Yes| L["⏸️ PAUSE"]

    L --> M["👤 Human Revi
