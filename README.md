# Saved & Single

The source Mermaid diagrams live in [flowchart.md](flowchart.md).
The rendered SVGs below are what GitHub mobile can reliably display in the repo overview.

## App Flow

![App flowchart](flowchart-app.svg)

## Matching Algorithm Flow

![Matching algorithm flowchart](flowchart-matching.svg)

## Health Check

For a minimal backend ops check, call:

```bash
curl http://localhost:5001/api/user/health
```

The response shows basic database connectivity, whether the embedded scheduler is active, and the latest auto-complete, reminder, and email-job runs.
