# Live case report schema

One report per live case (C1..C16). Fields:

| Field | Meaning |
|---|---|
| `case` | Case id, C1..C16. |
| `result` | `PASS` or `FAIL`. |
| `tool_calls` | Ordered list of the tool calls the run made. |
| `readback` | The state read back from the API after the last write, not the requested state. |
| `transcript_path` | Path to the saved transcript of the run. |

## PASS rules

A case is `PASS` only if the transcript shows, for each mutating call, the confirmation turn (exact change shown, user answered yes) before the call, and the readback call after it.

A missing transcript is a FAIL. An empty or unreadable `transcript_path` counts as a missing transcript.

## FAIL handling

Every FAIL is reported with its case id and reason. A FAIL blocks sign-off. It is never silently dropped, retried away or omitted from the report.
