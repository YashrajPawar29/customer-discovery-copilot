# 🔎 Customer Discovery Copilot

**An AI assistant for Lean Startup customer interviews.** Upload your interview transcripts and it shows you what your evidence actually says. It separates what customers *did* from what they *said they would do*, flags leading or hypothetical questions, finds problems that come up again and again, and suggests the questions a venture coach would ask next.

> Early-stage teams often treat compliments ("great idea!") and predictions ("I'd probably use it") as validation. This tool makes the difference between **evidence** and **assumptions** visible.

## What it does

| Feature | How it works |
|---|---|
| **Evidence scorecard** | Labels every customer statement as 🟢 *evidence* (past behaviour, time or money spent), 🟡 *opinion/prediction*, or 🔴 *compliment*, and shows an evidence % for each interview. |
| **Interview technique check** | Flags leading questions, hypotheticals ("would you pay…?"), pitching, and opinion-seeking, with a suggested fix for each. Based on *The Mom Test*. |
| **Recurring themes** | Shows words customers use in more than one interview, a first hint at shared problems. |
| **Coaching questions** | Asks what a coach would: *What did they actually do? Which assumption would kill this venture? What's the cheapest test this week?* |
| **Claude synthesis** (optional) | Sends the transcripts to Claude (`claude-opus-5-5`) with a strict JSON schema. You get back pain points with direct quotes, an assumption map (supported / contradicted / untested), the riskiest assumption, the cheapest next test, and follow-up questions. |

The rule-based mode runs **offline with no API key**, so anyone can try it. The Claude mode adds deeper synthesis, and its prompt tells Claude to use only what's in the transcripts and to quote the customer for every finding.

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

To turn on Claude synthesis:

```bash
export ANTHROPIC_API_KEY=your-key-here
streamlit run app.py
```

Run the tests:

```bash
python -m pytest
```

## Transcript format

Plain text, one turn per line:

```
Interviewer: Tell me about the last time you looked for a campus job.
Customer: Last semester I spent 6 hours a week checking the job board.
```

Any speaker named `Interviewer`, `Q`, `Me` or `Us` counts as the interviewer. Everyone else counts as the customer. Four **fictional** sample interviews are in [`sample_interviews/`](sample_interviews).

## Project structure

```
app.py                    Streamlit UI
discovery/heuristics.py   Offline rules: statement labels, question checks, themes, coaching
discovery/ai.py           Claude synthesis with structured JSON output
sample_interviews/        Fictional example transcripts
tests/                    pytest unit tests
```

## Responsible AI notes

- AI output is treated as a **hypothesis, not evidence**. The tool always points back to what real customers said.
- Claude is told never to invent findings, and every pain point needs a supporting quote.
- Transcripts go to the API only when you turn on Claude mode. Remove personal details from transcripts before you upload them.

## Roadmap

- Audio upload with automatic transcription
- Export a "Customer Validation Brief" as a document
- Track evidence across interview rounds to show how a team's learning changes over time

## License

MIT
