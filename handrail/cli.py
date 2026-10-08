"""Parse commands; the composition boundary owns application behavior."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path
from . import __version__
from .shared.errors import HandrailError


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def parse_states(items):
    states = {}
    for item in items:
        key, sep, value = item.partition("=")
        if not sep or key not in {"todo", "doing", "review", "done"} or not value:
            raise HandrailError("SETUP_STATE_INVALID", "Use --state review=ColumnName for ambiguous columns")
        states[key] = value
    return states


def parser():
    root = argparse.ArgumentParser(prog="handrail", description="Coordinate approved work through Herdr and Vikunja")
    root.add_argument("--repo", default=".")
    root.add_argument("--version", action="version", version="Handrail " + __version__)
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("locate", aliases=["skill-path"], help="Show exact installed skill, runtime and launcher paths")
    for name in ("doctor", "preflight", "config"):
        commands.add_parser(name)
    setup = commands.add_parser("setup")
    setup.add_argument("--name")
    setup.add_argument("--url")
    setup.add_argument("--allow-insecure-http", "--insecure", action="store_true", help="Allow this HTTP connection; does not disable TLS verification")
    setup.add_argument("--replace-token", action="store_true")
    init = commands.add_parser("init", help="Connect this repository; discover IDs, prepare columns and reuse settings")
    init.add_argument("--connection")
    init.add_argument("--url")
    target = init.add_mutually_exclusive_group()
    target.add_argument("--board", "--project", dest="project", help="Existing parent board name, link or ID")
    target.add_argument("--new-board", "--new-project", dest="new_project", help="Create a parent board with this name")
    init.add_argument("--confirm-board-selection", "--confirm-project-selection", dest="confirm_project_selection", action="store_true",
                      help="For noninteractive setup: attest that the user explicitly selected --board or --new-board; host execution approval does not count")
    init.add_argument("--view", help="Only needed when multiple Kanban views exist")
    endpoint = init.add_mutually_exclusive_group()
    endpoint.add_argument("--session")
    endpoint.add_argument("--socket")
    init.add_argument("--worktree-root")
    init.add_argument("--allow-insecure-http", "--insecure", action="store_true")
    init.add_argument("--state", action="append", default=[], help="Resolve ambiguous columns: state=column name or ID")
    board = commands.add_parser("board", help="Manage boards without starting implementation work").add_subparsers(dest="action", required=True)
    board.add_parser("list", help="List connected parent and descendant boards")
    add = board.add_parser("add", help="Add child boards beneath the connected parent")
    add.add_argument("names", nargs="+")
    add.add_argument("--reuse-existing", action="store_true")
    register = board.add_parser("register", help="Prepare and register an existing child board")
    register.add_argument("board")
    register.add_argument("--view")
    register.add_argument("--state", action="append", default=[])
    assign = board.add_parser("assign", help="Choose the board for a Work or a Plan's future Work cards")
    assign.add_argument("entity_id")
    assign.add_argument("--board", required=True)
    board.add_parser("history", help="Read local board and card administration history")
    prepare_work = board.add_parser("prepare-work", help="Prepare the default or assigned Work board")
    prepare_work.add_argument("work_id")
    default_board = board.add_parser("default", help="Register the user's default work board for future assignments")
    default_board.add_argument("board")
    default_board.add_argument("--reason", required=True)
    card = commands.add_parser("card", help="Manage card state on explicit user request").add_subparsers(dest="action", required=True)
    card.add_parser("types", help="Synchronize type labels on already managed card identities")
    listing = card.add_parser("list")
    listing.add_argument("--board")
    read_card = card.add_parser("read")
    read_card.add_argument("card")
    read_card.add_argument("--board")
    read_card.add_argument("--language", default="en")
    read_card.add_argument("--section", action="append")
    move = card.add_parser("move", help="Force a card state and hold automatic state sync")
    move.add_argument("card", help="Card link, ID, exact title or local Plan/Work ID")
    move.add_argument("--board")
    move.add_argument("--state", choices=("todo", "doing", "review", "done"), required=True)
    move.add_argument("--force", action="store_true", required=True)
    move.add_argument("--reason", required=True, help="The user's explicit request; no extra confirmation question is needed")
    move.add_argument("--operation-id")
    resume = card.add_parser("resume", help="Release a user override and queue the current workflow state")
    resume.add_argument("card")
    resume.add_argument("--board")
    resume.add_argument("--reason", required=True)
    reconcile = card.add_parser("resolve", help="Read and reconcile an uncertain card move without remote writes")
    reconcile.add_argument("operation_id")
    reconcile.add_argument("--evidence", required=True)
    resolver = commands.add_parser("setup-resolve", help="Record confirmed non-application of an interrupted setup write")
    resolver.add_argument("operation_id")
    resolver.add_argument("--evidence", required=True)
    bind = commands.add_parser("bind")
    bind.add_argument("--connection", required=True)
    bind.add_argument("--project", type=int, required=True)
    bind.add_argument("--view", type=int, required=True)
    bind.add_argument("--states-file", required=True)
    endpoint = bind.add_mutually_exclusive_group(required=True)
    endpoint.add_argument("--session")
    endpoint.add_argument("--socket")
    bind.add_argument("--worktree-root")
    bind.add_argument("--allow-inside-repository", action="store_true")
    status = commands.add_parser("status")
    status.add_argument("plan_id", nargs="?")
    history = commands.add_parser("history")
    history.add_argument("entity_id", nargs="?")
    sync = commands.add_parser("sync")
    sync.add_argument("--topic", choices=("board", "summary", "room.cleanup"))
    sync.add_argument("--resolve", help="Reconcile a board event after confirming the previous write did not apply")
    sync.add_argument("--evidence", help="Observed evidence for explicit board reconciliation")
    plan = commands.add_parser("plan").add_subparsers(dest="action", required=True)
    create = plan.add_parser("create")
    create.add_argument("--title", required=True)
    create.add_argument("--criteria-file", required=True)
    create.add_argument("--presentation-file", help="English and separate user-language card sections")
    create.add_argument("--operation-id")
    for name in ("approve", "verify", "submit-review", "accept", "complete", "reopen"):
        action = plan.add_parser(name)
        action.add_argument("plan_id")
        if name in ("approve", "accept", "complete"):
            action.add_argument("--approval", required=True)
        if name in ("accept", "complete"):
            action.add_argument("--summary-file", help="Prepared bilingual Summary content; coordinator supplies this from evidence")
        if name == "reopen":
            action.add_argument("--reason", required=True)
    cleanup = plan.add_parser("cleanup", help="Preview rooms or record the user's close/keep choice")
    cleanup.add_argument("plan_id")
    cleanup.add_argument("--choice", choices=("close", "keep"))
    cleanup.add_argument("--approval")
    cleanup.add_argument("--scope-token")
    cleanup.add_argument("--inspect", action="store_true")
    cleanup.add_argument("--reconcile", metavar="OBSERVATION_TOKEN")
    cleanup.add_argument("--evidence")
    cleanup.add_argument("--resume", action="store_true")
    instruction = commands.add_parser("instruction", help="Parent-board project guidance").add_subparsers(dest="action", required=True)
    listing = instruction.add_parser("list")
    listing.add_argument("--include-inactive", action="store_true")
    reading = instruction.add_parser("read")
    reading.add_argument("card_id", type=int)
    reading.add_argument("--language", default="en")
    reading.add_argument("--section", action="append")
    publishing = instruction.add_parser("publish")
    publishing.add_argument("--file", required=True)
    publishing.add_argument("--reason", required=True)
    publishing.add_argument("--operation-id")
    publishing.add_argument("--card", type=int)
    publishing.add_argument("--expected-hash")
    use_instruction = instruction.add_parser("use")
    use_instruction.add_argument("entity_id")
    use_instruction.add_argument("--phase", choices=("planning", "assignment", "review"), required=True)
    use_instruction.add_argument("--reason", required=True)
    deliver_instruction = instruction.add_parser("deliver")
    deliver_instruction.add_argument("work_id")
    deliver_instruction.add_argument("--reason", required=True)
    summary = commands.add_parser("summary", help="Publish and selectively read board-owned history").add_subparsers(dest="action", required=True)
    listing = summary.add_parser("list")
    listing.add_argument("--query")
    listing.add_argument("--include-stale", action="store_true")
    listing.add_argument("--issues", action="store_true", help="Find recorded Handrail execution issues on the connected board; not an automatic backlog")
    prepare = summary.add_parser("prepare")
    prepare.add_argument("plan_id")
    prepare.add_argument("--language", default="en")
    prepare.add_argument("--language-name")
    publish = summary.add_parser("publish")
    publish.add_argument("plan_id")
    publish.add_argument("--file", required=True)
    publish.add_argument("--reason", required=True)
    read = summary.add_parser("read")
    read.add_argument("card_id", type=int)
    read.add_argument("--language", default="agent")
    read.add_argument("--section", action="append")
    use = summary.add_parser("use")
    use.add_argument("entity_id")
    use.add_argument("card_id", type=int)
    use.add_argument("--section", action="append")
    use.add_argument("--reason", required=True)
    resolve = summary.add_parser("resolve")
    resolve.add_argument("operation_id")
    resolve.add_argument("--evidence", required=True)
    work = commands.add_parser("work").add_subparsers(dest="action", required=True)
    create = work.add_parser("create")
    create.add_argument("plan_id")
    create.add_argument("--title", required=True)
    create.add_argument("--criteria-file", required=True)
    create.add_argument("--presentation-file")
    create.add_argument("--operation-id")
    review = work.add_parser("review")
    review.add_argument("work_id")
    review.add_argument("--verdict", choices=("accept", "revise", "reject"), required=True)
    review.add_argument("--notes", required=True)
    complete = work.add_parser("complete")
    complete.add_argument("work_id")
    evidence = commands.add_parser("evidence")
    evidence.add_argument("entity_id")
    evidence.add_argument("--criterion", required=True)
    body = evidence.add_mutually_exclusive_group(required=True)
    body.add_argument("--text")
    body.add_argument("--file", help="JSON observation with status and text")
    evidence.add_argument("--revision")
    evidence.add_argument("--command-id")
    room = commands.add_parser("room").add_subparsers(dest="action", required=True)
    create = room.add_parser("create")
    create.add_argument("plan_id")
    adopt = room.add_parser("adopt")
    adopt.add_argument("plan_id")
    adopt.add_argument("workspace_id")
    adopt.add_argument("--evidence", required=True)
    adopt.add_argument("--origin-operation", required=True)
    adopt.add_argument("--owned-pane", action="append", default=[])
    close = room.add_parser("close")
    close.add_argument("room_id")
    worker = commands.add_parser("worker").add_subparsers(dest="action", required=True)
    start = worker.add_parser("start")
    start.add_argument("work_id")
    start.add_argument("--provider", choices=("codex", "cursor"))
    start.add_argument("--model")
    start.add_argument("--effort")
    start.add_argument("--instructions-file", required=True)
    start.add_argument("--operation-id")
    probe = worker.add_parser("probe", help="Run only in the assigned worker sandbox; no manager state access")
    probe.add_argument("--contract", required=True)
    submit = worker.add_parser("submit", help="Persist the worker's structured completion report")
    submit.add_argument("--contract", required=True)
    submit.add_argument("--report-file", required=True)
    for name in ("observe", "collect", "continue", "receive", "prompt", "keys", "recover", "integrate", "remove-worktree"):
        action = worker.add_parser(name)
        action.add_argument("attempt_id")
        if name in ("observe", "collect"):
            action.add_argument("--recent", action="store_true")
        if name == "prompt":
            action.add_argument("--instructions-file", required=True)
            action.add_argument("--message-id")
        if name == "keys":
            action.add_argument("--key", action="append", required=True)
            action.add_argument("--observation", required=True)
            action.add_argument("--reason", required=True)
            action.add_argument("--operation-id")
        if name == "recover":
            action.add_argument("--target", required=True)
            action.add_argument("--evidence", required=True)
    message = worker.add_parser("resolve-message")
    message.add_argument("operation_id")
    message.add_argument("--outcome", choices=("delivered", "not_delivered"), required=True)
    message.add_argument("--evidence", required=True)
    coordinator = commands.add_parser("coordinator", help="Record execution context and follow work to user Review").add_subparsers(dest="action", required=True)
    registration = coordinator.add_parser("register")
    registration.add_argument("--provider", choices=("codex", "cursor"), required=True)
    registration.add_argument("--model", required=True)
    registration.add_argument("--effort")
    registration.add_argument("--surface", choices=("CLI", "IDE"), default="CLI")
    registration.add_argument("--evidence", required=True)
    registration.add_argument("--session", help="Actual coordinator session identifier, when exposed by the host")
    tick = coordinator.add_parser("tick")
    tick.add_argument("plan_id")
    tick.add_argument("--owner", required=True)
    tick.add_argument("--interval", type=int, default=20)
    inbox = coordinator.add_parser("inbox")
    inbox.add_argument("plan_id", nargs="?")
    next_action = coordinator.add_parser("next")
    next_action.add_argument("plan_id")
    report = coordinator.add_parser("report")
    report.add_argument("plan_id")
    report.add_argument("--message", help="Actual message sent to the user; omit to preview the pending report")
    access = commands.add_parser("access", help="Propose narrow reusable host rules; keep intent separate").add_subparsers(dest="action", required=True)
    for name in ("plan", "apply", "revoke"):
        command_access = access.add_parser(name)
        command_access.add_argument("--provider", choices=("codex", "cursor"), required=True)
        command_access.add_argument("--group", action="append", required=True)
        if name in ("apply", "revoke"):
            command_access.add_argument("--approval", required=True)
    access.add_parser("metrics")
    metric = access.add_parser("record")
    metric.add_argument("--kind", choices=("host-approval", "user-choice", "wait"), required=True)
    metric.add_argument("--evidence", required=True)
    metric.add_argument("--category", choices=("intent", "board", "model", "host-execution", "acceptance", "cleanup"))
    metric.add_argument("--duration-ms", type=int)
    permissions = commands.add_parser("permissions").add_subparsers(dest="action", required=True)
    permissions.add_parser("list")
    grant = permissions.add_parser("grant")
    grant.add_argument("plan_id")
    grant.add_argument("--scope-file", required=True)
    grant.add_argument("--approval", required=True)
    grant.add_argument("--expires-at")
    grant.add_argument("--cycle", type=int, help="Earlier accepted cycle, for cleanup-only scope")
    revoke = permissions.add_parser("revoke")
    revoke.add_argument("grant_id")
    preview = permissions.add_parser("preview")
    preview.add_argument("plan_id")
    preview.add_argument("--action", dest="capability", required=True)
    preview.add_argument("--resources-file", required=True)
    command = commands.add_parser("command")
    command.add_argument("plan_id")
    command.add_argument("--argv-file", required=True)
    command.add_argument("--cwd", required=True)
    command.add_argument("--purpose", choices=("prepare", "verify"), required=True)
    command.add_argument("--operation-id")
    command.add_argument("--timeout", type=int, default=300)
    resolve = commands.add_parser("resolve-command", help="Record inspection of an interrupted command before a fresh run")
    resolve.add_argument("operation_id")
    resolve.add_argument("--evidence", required=True)
    return root


def dispatch(args):
    from .setup import settings, diagnostics
    if args.command == "worker" and args.action in ("probe", "submit"):
        from .agentroom.worker_io import probe, submit
        return probe(args.contract) if args.action == "probe" else submit(args.contract, load(args.report_file))
    if args.command in ("locate", "skill-path"):
        from .setup.installation import locate
        return locate()
    if args.command == "setup":
        return settings.connection_setup(args.name, args.url, args.allow_insecure_http, args.replace_token)
    if args.command in ("board", "card"):
        from .board.service import BoardService
        service = BoardService(args.repo)
        if args.command == "board":
            if args.action == "list":
                return service.list()
            if args.action == "add":
                return service.add(args.names, args.reuse_existing)
            if args.action == "register":
                return service.register(args.board, args.view, parse_states(args.state))
            if args.action == "assign":
                return service.assign(args.entity_id, args.board)
            if args.action == "prepare-work":
                return service.prepare_work(args.work_id)
            if args.action == "default":
                return service.set_default(args.board, args.reason)
            return service.history()
        from .board.cards import CardService
        cards = CardService(service)
        if args.action == "types":
            from .board.labels import synchronize_managed
            return synchronize_managed(service)
        if args.action == "list":
            return service.catalog.cards(args.board)
        if args.action == "read":
            from .board.format import select_sections
            _, snapshot, entity = service.catalog.card(args.card, args.board)
            return {"card_id": snapshot["task_id"], "entity_id": entity, "title": snapshot["title"],
                    **select_sections(snapshot["description"], args.language, args.section)}
        if args.action == "move":
            return cards.move(args.card, args.state, args.reason, args.force, args.board, args.operation_id)
        if args.action == "resume":
            return cards.resume(args.card, args.reason, args.board)
        return cards.resolve(args.operation_id, args.evidence)
    if args.command == "init":
        from .setup.onboarding import initialize
        states = parse_states(args.state)
        endpoint = {"session": args.session} if args.session else {"socket": args.socket} if args.socket else None
        return initialize(args.repo, args.connection, args.url, args.project, args.new_project,
                          args.view, endpoint, args.worktree_root, args.allow_insecure_http, states,
                          args.confirm_project_selection)
    if args.command == "setup-resolve":
        from .setup.onboarding import setup_store
        from .setup.provisioning import resolve
        return resolve(setup_store(), args.operation_id, args.evidence)
    if args.command == "bind":
        endpoint = {"session": args.session} if args.session else {"socket": args.socket}
        return settings.bind(args.repo, args.connection, args.project, args.view, load(args.states_file), endpoint,
                             args.worktree_root, args.allow_inside_repository)
    if args.command in ("doctor", "preflight"):
        return getattr(diagnostics, args.command)(args.repo)
    if args.command == "access":
        from .setup import access
        try:
            ctx = settings.context(args.repo)
        except HandrailError as exc:
            if exc.code != "PROJECT_NOT_BOUND" or args.action not in ("plan", "apply", "revoke") or set(args.group) != {"onboarding"}:
                raise
            identity, git = settings.project_identity(args.repo)
            from .shared.store import Store
            ctx = {"config": {"repo": str(git.root), "workspace_id": identity},
                   "store": Store(settings.data_root() / "projects" / identity / "state.sqlite3")}
        if args.action == "plan":
            return access.plan(ctx["config"], args.provider, args.group)
        if args.action in ("apply", "revoke"):
            return access.update_policy(ctx["store"], ctx["config"], args.provider, args.group, args.approval, args.action == "revoke")
        if args.action == "record":
            return access.record_metric(ctx["store"], args.kind, args.evidence, args.category, args.duration_ms)
        return access.metrics(ctx["store"])
    from .application import Application
    app = Application(args.repo)
    if args.command == "coordinator":
        if args.action == "register":
            from .agentroom.providers import register_coordinator
            return register_coordinator(app.store, args.provider, args.model, args.effort, args.surface, args.evidence, args.session)
        if args.action == "tick":
            return app.handoff().tick(args.plan_id, args.owner, args.interval)
        if args.action == "inbox":
            return app.handoff().inbox(args.plan_id)
        if args.action == "report":
            from .workflow.reporting import preview, acknowledge
            return acknowledge(app, args.plan_id, args.message) if args.message else preview(app, args.plan_id)
        return app.handoff().next_actions(args.plan_id)
    if args.command == "instruction":
        service = app.instructions()
        if args.action == "list":
            return service.list(args.include_inactive)
        if args.action == "read":
            return service.read(args.card_id, args.language, args.section)
        if args.action == "publish":
            return service.publish(load(args.file), args.reason, args.operation_id, args.card, args.expected_hash)
        if args.action == "deliver":
            return service.deliver(app, args.work_id, args.reason)
        return service.check(args.entity_id, args.phase, acknowledge=True, reason=args.reason)
    if args.command == "config":
        return app.config
    if args.command == "status":
        return app.status(args.plan_id)
    if args.command == "history":
        return app.workflow.history(args.entity_id)
    if args.command == "sync":
        if args.resolve:
            if not args.evidence or args.topic in ("room.cleanup", "summary"):
                raise HandrailError("EVIDENCE_REQUIRED", "Board reconciliation requires --evidence")
            return app.projection().resolve(args.resolve, args.evidence)
        return app.dispatch(args.topic)
    if args.command == "summary":
        service = app.summaries()
        if args.action == "list":
            return service.list(args.query, args.include_stale, args.issues)
        if args.action == "prepare":
            return service.prepare(args.plan_id, args.language, args.language_name)
        if args.action == "publish":
            return service.publish(args.plan_id, load(args.file), args.reason)
        if args.action == "read":
            return service.read(args.card_id, args.language, args.section)
        if args.action == "use":
            return service.use(args.entity_id, args.card_id, args.section, args.reason)
        return service.resolve(args.operation_id, args.evidence)
    if args.command == "plan":
        if args.action == "create":
            return app.create_plan(args.title, load(args.criteria_file), args.operation_id,
                                   load(args.presentation_file) if args.presentation_file else None)
        if args.action == "approve":
            return app.workflow.approve_plan(args.plan_id, args.approval)
        if args.action == "verify":
            return app.verify_plan(args.plan_id)
        if args.action == "submit-review":
            value = app.submit_review(args.plan_id)
            return {"plan": value, "delivery": app.advance_plan(args.plan_id)}
        if args.action in ("accept", "complete"):
            return app.accept(args.plan_id, args.approval, load(args.summary_file) if args.summary_file else None)
        if args.action == "cleanup":
            plan_id = app.summaries().plan_id(args.plan_id)
            if sum(bool(v) for v in (args.choice, args.inspect, args.reconcile, args.resume)) > 1:
                raise HandrailError("CLEANUP_ACTION_INVALID", "Choose one cleanup operation")
            if args.inspect:
                return app.cleanup().inspect(plan_id)
            if args.reconcile:
                return app.cleanup().reconcile(plan_id, args.reconcile, args.evidence)
            if args.resume:
                return app.cleanup().resume(plan_id)
            if not args.choice:
                return app.cleanup().preview(plan_id)
            return app.cleanup().choose(plan_id, args.choice, args.approval, args.scope_token)
        return app.reopen(args.plan_id, args.reason)
    if args.command == "work":
        if args.action == "create":
            return app.create_work(args.plan_id, args.title, load(args.criteria_file), args.operation_id,
                                   load(args.presentation_file) if args.presentation_file else None)
        if args.action == "review":
            return app.review(args.work_id, args.verdict, args.notes)
        value = app.complete_work(args.work_id)
        return {"work": value, "followthrough": app.advance_plan(value["plan_id"])}
    if args.command == "evidence":
        return app.record_evidence(args.entity_id, args.criterion, load(args.file) if args.file else args.text,
                                   args.revision, args.command_id)
    if args.command == "room":
        room = app.room()
        if args.action == "create":
            return room.create(args.plan_id)
        if args.action == "adopt":
            return room.adopt_room(args.plan_id, args.workspace_id, args.evidence,
                                   origin_operation_id=args.origin_operation, owned_panes=args.owned_pane)
        return room.close(args.room_id)
    if args.command == "worker":
        room = app.room()
        if args.action == "start":
            return app.start_worker(args.work_id, args.provider, args.model, Path(args.instructions_file).read_text(),
                              args.effort, args.operation_id)
        if args.action in ("observe", "collect"):
            observation = getattr(room, args.action)(args.attempt_id, args.recent)
            if args.action == "collect":
                return {"observation": observation, "submission": app.handoff().collect_submission(args.attempt_id),
                        "board": app.dispatch("board")}
            return observation
        if args.action == "continue":
            return app.handoff().continue_worker(args.attempt_id)
        if args.action == "receive":
            return {"submission": app.handoff().collect_submission(args.attempt_id), "board": app.dispatch("board")}
        if args.action == "prompt":
            return room.prompt(args.attempt_id, Path(args.instructions_file).read_text(), args.message_id)
        if args.action == "keys":
            return room.keys(args.attempt_id, args.key, args.observation, args.reason, args.operation_id)
        if args.action == "recover":
            return room.recover(args.attempt_id, args.target, args.evidence)
        if args.action == "resolve-message":
            return room.resolve_message(args.operation_id, args.outcome, args.evidence)
        if args.action == "remove-worktree":
            return room.remove_worktree(args.attempt_id)
        return room.integrate(args.attempt_id)
    if args.command == "permissions":
        from .authorization.service import Authorization
        auth = Authorization(app.store)
        if args.action == "grant":
            return auth.grant(args.plan_id, load(args.scope_file), args.approval, args.expires_at, args.cycle)
        if args.action == "revoke":
            return auth.revoke(args.grant_id)
        if args.action == "preview":
            return auth.preview(args.plan_id, args.capability, load(args.resources_file))
        return app.store.list("grant")
    if args.command == "command":
        from .agentroom.commands import run_command
        return run_command(app.ctx, args.plan_id, load(args.argv_file), args.cwd, args.purpose,
                           args.operation_id, args.timeout)
    if args.command == "resolve-command":
        from .agentroom.commands import resolve_command
        return resolve_command(app.ctx, args.operation_id, args.evidence)
    raise HandrailError("COMMAND_UNKNOWN", "Unknown command")


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    if not arguments:
        parser().print_help()
        return 0
    try:
        result = dispatch(parser().parse_args(arguments))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        from .shared.results import exit_status
        return exit_status(result)
    except HandrailError as exc:
        print(json.dumps(exc.as_dict(), ensure_ascii=False), file=sys.stderr)
        return 2 if exc.code in ("PROJECT_NOT_BOUND", "CONNECTION_REQUIRED", "SECRET_INPUT_REQUIRED") else 1
    except ImportError as exc:
        print(json.dumps({"error": "INSTALLATION_BROKEN", "actor": "handrail",
                          "boundary": "handrail/runtime", "module": exc.name,
                          "message": "An installed runtime dependency is missing or incompatible",
                          "next": "Install a verified fixed Handrail bundle, then resume the original command. Preserve saved setup and write intents; do not patch release or cache files."}), file=sys.stderr)
        return 1
    except OSError as exc:
        print(json.dumps({"error": "LOCAL_ACCESS_FAILED", "actor": "handrail", "errno": exc.errno,
                          "resource": exc.filename, "boundary": "host/filesystem",
                          "message": "Inspect this path and the host sandbox permissions"}), file=sys.stderr)
        return 1
    except (ValueError, TypeError, KeyError, sqlite3.Error) as exc:
        print(json.dumps({"error": "LOCAL_OPERATION_FAILED", "type": type(exc).__name__,
                          "message": "Inspect selected paths, input JSON and private configuration"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
