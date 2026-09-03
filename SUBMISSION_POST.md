# LinkedIn / X post

I took on Solari's SWE internship challenge and built **Checkpoint — “Git for AI agent actions.”** 🚀

Autonomous agents are getting good at taking actions. The problem is what happens when they take the *wrong* action.

Checkpoint adds a control and recovery layer around agent execution:

• Action interception
• Deterministic risk scoring
• Intent vs. actual-action checks
• Pre-execution blocking
• Human approval gates
• Filesystem diffs
• Audit timeline
• Real sandbox snapshots + rollback

The demo:

An agent is asked to organize a project. It attempts to delete a sensitive file → **blocked before execution**.

It then performs a bulk deletion that slips past the static check → Checkpoint detects the damage from the filesystem diff → **pauses the action** → human rejects it → **Solari restores the previous snapshot**.

Architecture:

Agent → Checkpoint → Solari Sandbox → Execute → Diff → Risk → Allow/Pause/Block → Approval → Rollback

Built with Python, FastAPI, SQLite, Groq tool calling, and Solari Sandbox.

GitHub: [YOUR_PUBLIC_REPO]
Demo: [YOUR_DEMO_LINK]

Built for the Solari challenge.

@Harry Chow @Solari

#AI #Agents #AgentInfrastructure #Python #Solari #AIEngineering #BuildInPublic
