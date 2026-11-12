# main_plan_simple.py - Planning in a Support Agent

The simplest version of the **planning pattern**: the LLM first writes a plan, then each step is executed with tools, then a final answer is written.

There is no routing and no reflection here. The goal is to learn planning on its own.

## How it works

```
customer query
      |
      v
plan_chain (Gemini)        -> writes 1 to 3 short steps
      |
      v
for each step:
   run_step() (Gemini + tools)   -> runs the step, calls tools if needed
   result is saved and passed to the next step
      |
      v
final_chain (Gemini)       -> writes the reply from all step results
```

## Main parts

| Part | Job |
|---|---|
| `plan_chain` | Breaks the query into steps, one step per line |
| `run_step()` | Runs one step with a small tool-calling loop (max 5 rounds) |
| `get_order_status`, `request_refund` | Tools that read the fake order data |
| `final_chain` | Writes the final reply using only the step results |

## Example

Query: `Order 1234 late hai, refund do`

```
Plan:
1. Check the status of order 1234
2. Request a refund for order 1234 if allowed

Step 1 -> get_order_status("1234") -> Shipped
Step 2 -> sees step 1 result, calls request_refund("1234") -> not possible (Shipped)
Final  -> friendly reply explaining the refund cannot be made yet
```

The exact wording of the plan changes between runs, because the LLM writes it.

## Run

From the repo root, with the virtual environment active and `GEMINI_API_KEY` in `.env`:

```bash
python langchain_version/main_plan_simple.py
```

## Why planning helps

- Multi-step queries are split into clear steps.
- Later steps can use the results of earlier steps.
- The plan is visible before anything runs, so it is easy to inspect and debug.

## Limitations

- Extra LLM calls (about 5 for a simple query), so higher cost and latency.
- A bad plan gives bad results, and the plan is not checked or corrected.
- Steps run one after another, not in parallel.
- Simple one-step queries do not need a planner.

## Next steps

- Add routing so each step goes to a specialist agent (see `main_planning.py`).
- Re-plan when a step fails (LangGraph is a good fit).
