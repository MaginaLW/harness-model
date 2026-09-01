"""Command-line interface for aiflow."""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from collections.abc import Sequence
from pathlib import Path

from aiflow import __version__
from aiflow.approval import approve_task
from aiflow.ask_service import answer_task
from aiflow.classification_service import classify_task
from aiflow.errors import AiflowError
from aiflow.escalation import ESCALATION_REASON_CODES, escalate_task, record_resolution
from aiflow.gate import evaluate_gate
from aiflow.observation_adapter import (
    parse_observation_mode,
    run_observation_file,
    serialize_observation_result,
)
from aiflow.review_service import (
    build_review_context,
    list_review_records,
    record_review,
    resolve_review_finding,
)
from aiflow.status_service import summarize_task
from aiflow.storage import atomic_write_json
from aiflow.task_service import (
    begin_task,
    close_task,
    evaluate_and_sync_verification_subject,
    freeze_task,
    recover_task,
    start_task,
)
from aiflow.verification_checks import validate_task_artifacts, validate_task_scope
from aiflow.verification_service import verify_task

DESCRIPTION = "Auditable AI code collaboration CLI"


def build_parser() -> ArgumentParser:
    """Build the stage-one command parser."""
    parser = ArgumentParser(prog="aiflow", description=DESCRIPTION)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    start = subparsers.add_parser("start", help="create or recover an AI Flow task")
    start.add_argument("--objective")
    start.add_argument("--allow", action="append", default=[])
    start.add_argument("--forbid-action", action="append", default=[])
    start.add_argument("--allow-detached", action="store_true")
    start.add_argument("--recover", metavar="TASK-ID")
    begin = subparsers.add_parser("begin", help="begin implementation or retry")
    begin.add_argument("task_id")
    begin.add_argument("--actor", required=True)
    begin.add_argument("--reason")
    close = subparsers.add_parser("close", help="record an externally completed merge")
    close.add_argument("task_id")
    close.add_argument("--result", required=True, choices=["merged"])
    close.add_argument("--merge-commit", required=True)
    close.add_argument("--actor", required=True)
    classify = subparsers.add_parser("classify", help="classify a task using the active Policy")
    classify.add_argument("task_id")
    classify.add_argument("--actor", required=True)
    freeze = subparsers.add_parser("freeze", help="validate and freeze a task specification")
    freeze.add_argument("task_id")
    freeze.add_argument("--actor", required=True)
    answer = subparsers.add_parser("answer", help="record an ASK selection and freeze its spec")
    answer.add_argument("task_id")
    answer.add_argument("--options-file", required=True, type=Path)
    answer.add_argument("--select", required=True)
    answer.add_argument("--actor", required=True)
    answer.add_argument("--reason", required=True)
    approve = subparsers.add_parser("approve", help="record a version-bound approval")
    approve.add_argument("task_id")
    approve.add_argument("--type", required=True, choices=["spec", "code", "action"])
    approve.add_argument("--actor", required=True)
    approve.add_argument("--reason", required=True)
    approve.add_argument("--action-file", type=Path)
    escalate = subparsers.add_parser("escalate", help="raise a task's governance route")
    escalate.add_argument("task_id")
    escalate.add_argument("--to", required=True, choices=["ASK", "REVIEW", "BLOCK"])
    escalate.add_argument("--reason-code", required=True, choices=sorted(ESCALATION_REASON_CODES))
    escalate.add_argument("--impact", required=True)
    escalate.add_argument("--next-step", required=True)
    escalate.add_argument("--actor", required=True)
    escalate.add_argument("--existing-work", default="preserve_and_reassess")
    resolve = subparsers.add_parser("resolve", help="record evidence for an escalation condition")
    resolve.add_argument("task_id")
    resolve.add_argument("--condition", required=True)
    resolve.add_argument("--evidence-ref", action="append", required=True)
    resolve.add_argument("--reason", required=True)
    resolve.add_argument("--actor", required=True)
    resolve.add_argument("--authorize-downgrade", action="store_true")
    review = subparsers.add_parser("review", help="manage structured staged reviews")
    review_commands = review.add_subparsers(dest="review_command", required=True)
    review_context = review_commands.add_parser(
        "context", help="build a deterministic minimal review context"
    )
    review_context.add_argument("task_id")
    review_context.add_argument("--stage", required=True, choices=["design", "implementation"])
    review_context.add_argument("--output", type=Path)
    review_record = review_commands.add_parser(
        "record", help="persist an immutable structured review"
    )
    review_record.add_argument("task_id")
    review_record.add_argument("--input", required=True, type=Path)
    review_record.add_argument("--actor", required=True)
    review_resolve = review_commands.add_parser(
        "resolve", help="append a finding-resolution revision"
    )
    review_resolve.add_argument("task_id")
    review_resolve.add_argument("--review", required=True)
    review_resolve.add_argument("--finding", required=True)
    review_resolve.add_argument("--reason", required=True)
    review_resolve.add_argument("--actor", required=True)
    review_show = review_commands.add_parser("show", help="show latest structured reviews")
    review_show.add_argument("task_id")
    review_show.add_argument("--stage", choices=["design", "implementation"])
    review_show.add_argument("--format", choices=["text", "json"], default="text")
    status = subparsers.add_parser("status", help="show a read-only task summary")
    status.add_argument("task_id")
    status.add_argument("--format", choices=["text", "json"], default="text")
    observe = subparsers.add_parser(
        "observe",
        help="apply or read-only evaluate one immutable observation",
        usage=("aiflow observe TASK-ID --input FILE --mode {apply,dry-run,ci} [--actor ACTOR]"),
    )
    observe.add_argument("task_id", nargs="?", metavar="TASK-ID", help="required explicit task ID")
    observe.add_argument(
        "--input", type=Path, metavar="FILE", help="required local UTF-8 observation JSON file"
    )
    observe.add_argument(
        "--mode",
        metavar="{apply,dry-run,ci}",
        help="required; apply writes task audit, dry-run and ci are read-only",
    )
    observe.add_argument(
        "--actor", metavar="ACTOR", help="required for apply; forbidden for dry-run and ci"
    )
    verify = subparsers.add_parser("verify", help="run controlled verification")
    verify.add_argument("task_id")
    verify.add_argument("--actor")
    verify_mode = verify.add_mutually_exclusive_group()
    verify_mode.add_argument("--check", action="append", default=[])
    verify_mode.add_argument("--finalize", action="store_true")
    verify_mode.add_argument("--abandon", action="store_true")
    verify.add_argument("--reason")
    verify.add_argument("--ci", action="store_true")
    verify.add_argument("--ci-run-dir", type=Path)
    verify.add_argument("--output", type=Path)
    gate = subparsers.add_parser("gate", help="evaluate the read-only merge gate")
    gate.add_argument("task_id")
    gate.add_argument("--evidence", type=Path)
    gate.add_argument("--format", choices=["text", "json"], default="text")
    validate = subparsers.add_parser("validate", help="validate governed task artifacts")
    validate.add_argument("task_id")
    scope = subparsers.add_parser("scope", help="validate the final task Git scope")
    scope.add_argument("task_id")
    sync = subparsers.add_parser("sync", help="synchronize an explicitly scoped task subject")
    sync.add_argument("task_id")
    sync.add_argument("--actor", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the root command without exposing unfinished business subcommands."""
    try:
        arguments = build_parser().parse_args(argv)
        if arguments.command == "start":
            if arguments.recover is not None:
                if arguments.objective is not None or arguments.allow or arguments.forbid_action:
                    raise AiflowError(
                        "Recovery cannot be combined with creation arguments",
                        code="START_INPUT_INVALID",
                    )
                start_result = recover_task(Path.cwd(), arguments.recover)
            else:
                start_result = start_task(
                    Path.cwd(),
                    objective=arguments.objective,
                    allowed_scope=arguments.allow,
                    forbidden_actions=arguments.forbid_action,
                    allow_detached=arguments.allow_detached,
                )
            print(start_result.task_id)
            print(start_result.task_directory.resolve())
        elif arguments.command == "begin":
            transition_result = begin_task(
                Path.cwd(),
                arguments.task_id,
                actor=arguments.actor,
                reason=arguments.reason,
            )
            print(f"{arguments.task_id} {transition_result.task['current_state']}")
        elif arguments.command == "close":
            transition_result = close_task(
                Path.cwd(),
                arguments.task_id,
                result=arguments.result,
                merge_commit=arguments.merge_commit,
                actor=arguments.actor,
            )
            print(f"{arguments.task_id} {transition_result.task['current_state']}")
        elif arguments.command == "classify":
            classification = classify_task(Path.cwd(), arguments.task_id, actor=arguments.actor)
            print(f"{arguments.task_id} {classification['effective_route']}")
        elif arguments.command == "freeze":
            freeze_result = freeze_task(Path.cwd(), arguments.task_id, actor=arguments.actor)
            print(f"{arguments.task_id} {freeze_result.task['current_state']}")
        elif arguments.command == "answer":
            answer_result = answer_task(
                Path.cwd(),
                arguments.task_id,
                options_file=arguments.options_file,
                selected_option_id=arguments.select,
                actor=arguments.actor,
                reason=arguments.reason,
            )
            print(f"{arguments.task_id} {answer_result.task['current_state']}")
            print("ASK option structure was validated; semantic exclusivity was not proven.")
        elif arguments.command == "approve":
            approval_result = approve_task(
                Path.cwd(),
                arguments.task_id,
                approval_type=arguments.type,
                actor=arguments.actor,
                reason=arguments.reason,
                action_file=arguments.action_file,
            )
            print(f"{arguments.task_id} {approval_result.task['current_state']}")
        elif arguments.command == "escalate":
            escalation_result = escalate_task(
                Path.cwd(),
                arguments.task_id,
                target_route=arguments.to,
                reason_code=arguments.reason_code,
                impact=arguments.impact,
                next_step=arguments.next_step,
                actor=arguments.actor,
                existing_work_disposition=arguments.existing_work,
            )
            print(f"{arguments.task_id} {escalation_result.task['current_state']}")
        elif arguments.command == "resolve":
            resolution_result = record_resolution(
                Path.cwd(),
                arguments.task_id,
                condition=arguments.condition,
                evidence_refs=arguments.evidence_ref,
                actor=arguments.actor,
                reason=arguments.reason,
                authorize_downgrade=arguments.authorize_downgrade,
            )
            print(f"{arguments.task_id} {resolution_result.task['current_state']}")
        elif arguments.command == "review":
            if arguments.review_command == "context":
                context = build_review_context(Path.cwd(), arguments.task_id, arguments.stage)
                if arguments.output is not None:
                    atomic_write_json(arguments.output, context)
                    print(str(arguments.output.resolve()))
                else:
                    print(json.dumps(context, ensure_ascii=False, sort_keys=True))
            elif arguments.review_command == "record":
                record_result = record_review(
                    Path.cwd(),
                    arguments.task_id,
                    input_path=arguments.input,
                    actor=arguments.actor,
                )
                print(
                    f"{arguments.task_id} {record_result.record['review_id']} "
                    f"r{int(record_result.record['revision']):04d}"
                )
            elif arguments.review_command == "resolve":
                finding_result = resolve_review_finding(
                    Path.cwd(),
                    arguments.task_id,
                    review_id=arguments.review,
                    finding_id=arguments.finding,
                    reason=arguments.reason,
                    actor=arguments.actor,
                )
                print(
                    f"{arguments.task_id} {finding_result.record['review_id']} "
                    f"r{int(finding_result.record['revision']):04d}"
                )
            elif arguments.review_command == "show":
                reviews = list_review_records(Path.cwd(), arguments.task_id, stage=arguments.stage)
                if arguments.format == "json":
                    print(
                        json.dumps(
                            {"task_id": arguments.task_id, "reviews": list(reviews)},
                            ensure_ascii=False,
                            sort_keys=True,
                        )
                    )
                else:
                    for record in reviews:
                        print(
                            f"{record['review_id']} r{int(record['revision']):04d} "
                            f"{record['review_stage']} {record['outcome']}"
                        )
        elif arguments.command == "status":
            summary = summarize_task(Path.cwd(), arguments.task_id)
            print(summary.to_json() if arguments.format == "json" else summary.to_text())
        elif arguments.command == "observe":
            if arguments.task_id is None or arguments.input is None or arguments.mode is None:
                raise AiflowError(
                    "Observation task, input and mode are required",
                    code="OBSERVATION_ADAPTER_INVALID",
                )
            observe_result = run_observation_file(
                Path.cwd(),
                arguments.task_id,
                arguments.input,
                mode=parse_observation_mode(arguments.mode),
                actor=arguments.actor,
            )
            print(
                json.dumps(
                    serialize_observation_result(observe_result),
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            return 0 if observe_result.decision.execution_allowed else 2
        elif arguments.command == "verify":
            verify_result = verify_task(
                Path.cwd(),
                arguments.task_id,
                actor=arguments.actor,
                check_ids=arguments.check,
                ci=arguments.ci,
                ci_run_dir=arguments.ci_run_dir,
                output=arguments.output,
                finalize=arguments.finalize,
                abandon=arguments.abandon,
                reason=arguments.reason,
            )
            print(
                f"{verify_result.task_id} {verify_result.state or 'CI'} {verify_result.conclusion}"
            )
        elif arguments.command == "gate":
            decision = evaluate_gate(
                Path.cwd(), arguments.task_id, evidence_path=arguments.evidence
            )
            print(decision.to_json() if arguments.format == "json" else decision.to_text())
            return 0 if decision.passed else 2
        elif arguments.command == "validate":
            validate_task_artifacts(Path.cwd(), arguments.task_id)
            print(f"{arguments.task_id} valid")
        elif arguments.command == "scope":
            validate_task_scope(Path.cwd(), arguments.task_id)
            print(f"{arguments.task_id} scope-valid")
        elif arguments.command == "sync":
            assessment = evaluate_and_sync_verification_subject(
                Path.cwd(), arguments.task_id, mode="final", actor=arguments.actor
            )
            print(f"{arguments.task_id} {assessment.subject_commit}")
    except AiflowError as error:
        print(error.message, file=sys.stderr)
        return 1
    return 0
