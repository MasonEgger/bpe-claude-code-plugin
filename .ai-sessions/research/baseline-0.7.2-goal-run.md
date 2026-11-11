# Baseline: The 0.7.2 Goal Run, Per-Step Mode

Measured from the session transcript and its subagent transcripts on 2026-11-10.
This is the "before" for the 0.7.3 batch-mode comparison (#51).

## Run Shape

- Plan: `.ai-sessions/fixes-0.7.2/plan.md`, 12 Task-shape steps across 6 sections; sections 3 and 6 declared `Tools: none`.
- Span: 2026-11-09 22:49 UTC to 2026-11-10 00:40 UTC, 111 minutes wall-clock end to end.
- Dispatches: 42 (12 implement, 14 validator, 4 fix, 12 finalize). 3.5 per step.
- Models as resolved at dispatch time: `claude-opus-4-8` for every executor dispatch and `claude-fable-5` for every validator dispatch, both from Mason's user-global `bpe.local.md` profile (the 2026-08-08 map), not the frontmatter aliases.
- Validator outcome: 4 warn verdicts out of 10 first-pass validations, every one fixed at iteration 2. 0 block verdicts. 0 red test runs.

## Subagent Cost by Dispatch Kind

| Kind | Dispatches | Minutes | Cache-read tokens | Cache-create tokens | Output tokens |
|---|---|---|---|---|---|
| implement | 12 | 30.6 | 31.9M | 2.9M | 431k |
| validator | 14 | 30.2 | 15.5M | 3.1M | 452k |
| fix | 4 | 4.2 | 3.5M | 0.6M | 67k |
| finalize | 12 | 23.7 | 25.7M | 3.0M | 337k |
| all subagents | 42 | 88.8 | 76.8M | 9.6M | 1.28M |

Per-dispatch means: 2.1 minutes, 39 assistant turns, 19 tool calls, 1.8M cache-read tokens.
Finalize alone is 27 percent of subagent wall-clock and 33 percent of subagent cache-read tokens: a fresh agent that re-reads the protocol, the plan, and the diff to write a session summary and commit work it never saw.

## Orchestrator Cost

The parent session over the same span: 283 assistant turns, 108.7M cache-read tokens, 1.4M cache-create tokens, 346k output tokens.
That is more cache-read than all 42 subagents together.
Each dispatch costs the orchestrator roughly 6.7 turns of its own (branch check, todo read, dispatch, SHA verification, status echo), and every turn re-reads the whole growing transcript.
Dispatch count, not subagent size, is the lever on orchestrator cost; this is the quantitative case for batch mode and the reason #53's checkpoint matters on long arcs.

## Per-Dispatch Table

| Start (UTC) | Agent | Dispatch | Min | Turns | Tools | Cache-read | Cache-create | Output |
|---|---|---|---|---|---|---|---|---|
| 22:49 | step-executor | Implement S1 Step 1 | 1.0 | 32 | 15 | 1,233,781 | 235,095 | 13,970 |
| 22:51 | validator | Validate S1 Step 1 | 1.1 | 22 | 10 | 719,320 | 172,055 | 15,912 |
| 22:52 | step-executor | Finalize S1 Step 1 | 1.6 | 39 | 18 | 1,734,377 | 225,471 | 23,112 |
| 22:55 | step-executor | Implement S1 Step 2 | 2.3 | 41 | 21 | 2,130,765 | 266,024 | 33,077 |
| 22:57 | validator | Validate S1 Step 2 | 3.2 | 32 | 17 | 1,244,838 | 248,374 | 52,006 |
| 23:01 | step-executor | Fix S1 Step 2 (iter 2) | 1.4 | 29 | 13 | 951,876 | 169,476 | 26,567 |
| 23:03 | validator | Re-validate S1 Step 2 | 2.1 | 33 | 16 | 1,216,685 | 207,601 | 32,065 |
| 23:05 | step-executor | Finalize S1 Step 2 | 2.8 | 41 | 20 | 1,990,767 | 275,058 | 37,460 |
| 23:09 | step-executor | Implement S2 Step 1 | 1.5 | 40 | 20 | 1,899,201 | 239,088 | 24,709 |
| 23:11 | validator | Validate S2 Step 1 | 1.9 | 28 | 15 | 1,066,554 | 222,899 | 23,894 |
| 23:13 | step-executor | Finalize S2 Step 1 | 1.2 | 31 | 15 | 1,221,182 | 206,537 | 17,665 |
| 23:15 | step-executor | Implement S2 Step 2 | 1.6 | 51 | 25 | 2,515,729 | 250,910 | 23,803 |
| 23:17 | validator | Validate S2 Step 2 | 3.1 | 31 | 15 | 1,235,862 | 226,250 | 47,138 |
| 23:20 | step-executor | Fix S2 Step 2 (iter 2) | 0.8 | 22 | 10 | 684,458 | 130,603 | 13,821 |
| 23:21 | validator | Re-validate S2 Step 2 | 1.4 | 25 | 13 | 879,929 | 194,669 | 24,235 |
| 23:23 | step-executor | Finalize S2 Step 2 | 2.3 | 54 | 25 | 2,875,793 | 265,336 | 32,871 |
| 23:27 | step-executor | Implement S3 Step 1 | 3.2 | 47 | 21 | 2,256,528 | 201,089 | 46,333 |
| 23:30 | step-executor | Finalize S3 Step 1 | 1.6 | 47 | 22 | 2,375,798 | 278,413 | 21,152 |
| 23:33 | step-executor | Implement S4 Step 1 | 1.8 | 47 | 22 | 2,278,678 | 212,562 | 22,773 |
| 23:35 | validator | Validate S4 Step 1 | 1.6 | 27 | 13 | 852,754 | 207,760 | 25,166 |
| 23:37 | step-executor | Finalize S4 Step 1 | 1.3 | 36 | 17 | 1,532,142 | 214,613 | 16,888 |
| 23:39 | step-executor | Implement S5 Step 1 | 2.3 | 51 | 28 | 2,783,498 | 264,595 | 27,761 |
| 23:42 | validator | Validate S5 Step 1 | 3.0 | 32 | 17 | 1,340,148 | 233,074 | 50,297 |
| 23:45 | step-executor | Fix S5 Step 1 (iter 2) | 0.7 | 22 | 12 | 674,441 | 155,466 | 12,016 |
| 23:46 | validator | Re-validate S5 Step 1 | 1.7 | 29 | 16 | 1,038,240 | 205,362 | 25,157 |
| 23:48 | step-executor | Finalize S5 Step 1 | 2.2 | 54 | 23 | 2,800,938 | 241,947 | 31,974 |
| 23:51 | step-executor | Implement S5 Step 2 | 5.2 | 66 | 30 | 4,077,522 | 264,644 | 67,181 |
| 23:57 | validator | Validate S5 Step 2 | 1.8 | 27 | 13 | 862,102 | 227,122 | 24,769 |
| 23:59 | step-executor | Finalize S5 Step 2 | 2.3 | 51 | 24 | 2,598,702 | 236,205 | 31,850 |
| 00:02 | step-executor | Implement S5 Step 3 | 3.9 | 77 | 34 | 4,837,808 | 263,974 | 53,096 |
| 00:07 | validator | Validate S5 Step 3 | 2.5 | 33 | 19 | 1,552,589 | 253,655 | 39,046 |
| 00:10 | step-executor | Finalize S5 Step 3 | 2.5 | 47 | 22 | 2,296,284 | 263,266 | 36,761 |
| 00:13 | step-executor | Implement S5 Step 4 | 4.0 | 59 | 27 | 3,968,962 | 286,344 | 55,247 |
| 00:18 | validator | Validate S5 Step 4 | 2.2 | 28 | 15 | 1,319,494 | 219,819 | 28,345 |
| 00:20 | step-executor | Finalize S5 Step 4 | 1.9 | 46 | 21 | 2,428,346 | 255,205 | 27,994 |
| 00:23 | step-executor | Implement S5 Step 5 | 3.2 | 62 | 31 | 3,414,014 | 239,686 | 43,997 |
| 00:27 | validator | Validate S5 Step 5 | 2.5 | 29 | 16 | 1,181,540 | 276,161 | 37,391 |
| 00:30 | step-executor | Fix S5 Step 5 (iter 2) | 1.3 | 28 | 12 | 1,164,783 | 151,208 | 14,587 |
| 00:31 | validator | Re-validate S5 Step 5 | 2.1 | 27 | 13 | 1,027,393 | 214,617 | 26,600 |
| 00:34 | step-executor | Finalize S5 Step 5 | 2.3 | 42 | 20 | 2,022,337 | 271,161 | 34,032 |
| 00:37 | step-executor | Implement S6 Step 1 | 0.6 | 22 | 12 | 612,218 | 149,380 | 9,912 |
| 00:38 | step-executor | Finalize S6 Step 1 | 1.7 | 40 | 18 | 1,869,112 | 249,372 | 24,809 |

## How It Was Measured

- Source: the parent transcript `~/.claude/projects/<project>/<session>.jsonl` and `<session>/subagents/agent-<id>.jsonl`.
- A dispatch is an `Agent` tool_use in the parent; its `toolUseResult.agentId` names the subagent transcript, and `resolvedModel` names the model.
- Minutes: first to last timestamp in the subagent transcript.
- Tokens: the sum of `usage` over the subagent's assistant entries (`cache_read_input_tokens`, `cache_creation_input_tokens`, `output_tokens`; uncached `input_tokens` were under 200 per dispatch and are omitted).
- Orchestrator tokens: the same sum over the parent's assistant entries inside the run span.
- Script: an ad hoc Python pass over the two transcript shapes; the 0.7.3 comparison should land it as `scripts/goal-run-report.py` so the after measurement uses the same arithmetic.

## What To Compare After Batch Mode

Same plan shape (Task steps, a mix of tooled and `Tools: none` sections), same profile, and report: dispatch count, subagent minutes, subagent cache-read tokens, orchestrator turns and cache-read tokens, and the validator's warn rate per first-pass validation.
A quality drop shows as a higher warn rate or any block verdict on the batch validator or the final sweep.
