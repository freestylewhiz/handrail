# Handrail plugin

This package contains the Handrail v1 runtime and agent skill. It coordinates approved work through an existing Herdr service and projects cards/history to an existing Vikunja v2 server.

Use `handrail locate` to obtain the stable absolute launcher and verify the active version. Both Codex and Cursor use the managed release runtime; Codex cache is not the ordinary command path. The source repository provides architecture, philosophy, installation and workflow documentation. This is an alpha rebuild; v0.5 state is not automatically migrated.

Alpha.5 adds `plan complete`, `summary prepare/publish/list/read/use/resolve`, and consented `plan cleanup`. The coordinator synthesizes separate English/user-language narratives from evidence; Summary content/history stay on Vikunja. Worker assignments receive selected, version-pinned history.

Alpha.6 adds observed model selection, scoped approval rules, worker write readiness, durable completion handoff, coordinator tick/report, default work boards, rich bilingual cards, type labels and parent-board Instructions. Cleanup reconciles identity after Done. Requested settings do not prove host permission or IDE support. Tick requires an active coordinator; no background wakeup is installed.

The RC02 correction restores setup write diagnostics in a dedicated module and adds named internal-import checks to packaging. A build or successful installation does not establish runtime acceptance. Consult the source repository's status and installation report for the checks actually performed. If setup reports an internal installation defect, preserve its saved progress and install a corrected bundle; do not patch release or cache files during ordinary project setup.
