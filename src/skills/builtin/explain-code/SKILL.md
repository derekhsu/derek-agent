---
name: explain-code
description: Explain code structure, data flow, and likely change impact before editing.
---

When the user asks you to explain, review, or understand code, first identify the main entry point, the core data flow, and the highest-risk dependencies.

Prefer a concise summary of:
- what the code is responsible for
- what inputs and outputs it handles
- what state it reads or mutates
- what callers or consumers are likely affected by changes

If the user asks for a change after the explanation, reuse this understanding to propose the smallest safe edit.
