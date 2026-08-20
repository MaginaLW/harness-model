"""Command-line interface for aiflow."""

from __future__ import annotations

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
from aiflow.status_service import summarize_task
from aiflow.task_service import begin_task, close_task, freeze_task, recover_task, start_task

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
    status = subparsers.add_parser("status", help="show a read-only task summary")
    status.add_argument("task_id")
    status.add_argument("--format", choices=["text", "json"], default="text")
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
        elif arguments.command == "status":
            summary = summarize_task(Path.cwd(), arguments.task_id)
            print(summary.to_json() if arguments.format == "json" else summary.to_text())
    except AiflowError as error:
        print(error.message, file=sys.stderr)
        return 1
    return 0
