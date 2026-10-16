# Agentic Banking Pipeline

A small project that shows how a data pipeline prepares banking data for an LLM-based agent. It cleans and validates raw transactions, masks personal data, and turns the results into things an agent can safely use:

- **Account-month briefs:** short, factual text summaries that a model can read and cite.
- **A search index:** finds the right briefs for a question. It uses TF-IDF, so it runs offline.
- **Tools:** typed Python functions with JSON schemas that an agent can call.
- **An agent:** runs offline with a simple router. It can also run with Claude if you set an API key.
- **Guardrails:** checks that stop personal data from reaching anything an LLM can read.

> The dataset is **synthetic**. It was generated for learning and contains no real customer data.

## Files

| File | Purpose |
|---|---|
| `bank_transactions_agentic.csv` | 212 synthetic transactions for six accounts, July to September 2026, with deliberate data quality issues |
| `agentic_banking_pipeline.ipynb` | The notebook. Every code line has a comment |
| `gen_dataset.py` | Regenerates the CSV with the same seed (42), or with other settings if you change them |
| `README.md` | This document |

## Dataset

| Column | Description |
|---|---|
| transaction_id | Sequential ID, TXN0001 onwards |
| account_id | ACC2001 to ACC2005 (MUR) and ACC2006 (USD) |
| customer_id | Owner of the account. This is personal data and is masked in the pipeline |
| transaction_date | YYYY-MM-DD |
| transaction_time | HH:MM:SS |
| transaction_type | CREDIT or DEBIT |
| amount | Positive value in the account's currency |
| currency | MUR or USD |
| merchant_category | Type of spending or income |
| channel | POS, ONLINE, MOBILE, TRANSFER or BRANCH |
| branch_code | Branch that processed the transaction |
| balance_after | Running balance, consistent in time order |
| status | SUCCESS or FAILED |

The deliberate issues the pipeline has to handle:

| Issue | Rows affected |
|---|---|
| Exact copy under a new transaction ID | 1 |
| Missing amount | 1 |
| Missing account_id | 1 |
| Impossible date (2026-09-31) | 1 |
| Negative amount | 1 |
| Messy type text (`debit `) | 1 |
| Lowercase currency (`mur`) | 1 |
| Blank merchant category | 1 |
| FAILED status | 6 |

## How the pipeline works

```
raw CSV -> validate -> curate and mask -> account-month briefs -> search index
                                                              \-> tools -> agent (offline router or Claude)
                                       guardrails check everything an LLM can read
```

1. **Validate.** Text is cleaned, types are converted, and exact copies are removed. Rows that break a rule go to quarantine with reason codes.
2. **Mask.** Each customer ID is replaced with a salted SHA-256 token, such as `cust_21980e5547`. The raw ID is never written to an output file.
3. **Brief.** One short paragraph per account and month. It covers counts, money in and out in one currency, flagged transactions, quarantine reasons, and the largest debit.
4. **Index.** TF-IDF vectors over the briefs, so a question returns the closest briefs with scores.
5. **Tools.** Four tools, each with a JSON schema that describes it to the model.
6. **Agent.** Offline, a router picks a tool from the question. Optionally, Claude receives the schemas and calls tools in a loop until it has an answer.
7. **Guardrails.** Confirm that no raw customer ID appears in the briefs, the tool schemas, or the curated and quarantine tables, and that every month is well formed.

## Tools available to the agent

| Tool | Use it for | Arguments |
|---|---|---|
| `get_account_month` | Summary of one account in one month | account_id, month (YYYY-MM) |
| `list_quarantine` | Rows that failed validation | reason_code (optional) |
| `get_large_transactions` | Clean transactions at or above an amount, for AML review | min_amount (optional) |
| `accounts_with_failures` | Account-months with failed transactions | min_failed (optional) |
| `search_briefs` | Descriptive questions about briefs | query, k |

Counting questions go to a structured tool, not to search. TF-IDF cannot count, so for example "which accounts had failures" uses `accounts_with_failures`.

## How to run

1. Put `bank_transactions_agentic.csv` and `agentic_banking_pipeline.ipynb` in the same folder.
2. Install the libraries: `pip install pandas numpy scikit-learn`
3. Run all cells in Jupyter, VS Code or Colab. The offline agent works with no key.
4. For the Claude step (optional):
   - Install the SDK: `pip install anthropic`
   - Set your key: `export ANTHROPIC_API_KEY=...` (on Windows, `set ANTHROPIC_API_KEY=...`)
   - Run the notebook again. Section 7 sends a question to the model, which calls the tools.

The output goes to `output_agentic/`:
- `briefs.jsonl`: one brief per line, ready for a retrieval tool
- `tool_specs.json`: the tool schemas
- `curated_masked.csv`: clean data with masked customers
- `quarantine.csv`: rejected rows with reason codes and masked customers

## Expected results

These are the numbers from my run with seed 42:

| Measure | Value |
|---|---|
| Raw rows | 212 |
| After removing the exact copy | 211 |
| Clean rows | 201 |
| Quarantined rows | 10 (FAILED_STATUS 6, MISSING_ACCOUNT 1, MISSING_AMOUNT 1, INVALID_DATE 1, NEGATIVE_AMOUNT 1) |
| Account-month briefs | 18 (6 accounts x 3 months) |
| Account-months with a failed transaction | 6 (one per failed transaction) |
| Transactions flagged at or above 10,000 | 17. Most are monthly salaries, plus two large transfers |
| Guardrail check | Passed |

The notebook prints the same numbers, and the first brief looks like this:

> Account ACC2001, 2026-07, currency MUR. Customer token cust_09f61913d4. Transactions: 11 in total, of which 10 passed validation and 1 failed. Money in 31,853.33 MUR; money out 5,450.27 MUR; net flow +26,403.06 MUR. ...

## Security and privacy notes

- **Masking is not anonymisation.** A salted hash removes the raw ID from the data, but a token can still identify a customer for anyone who knows the salt. Under laws such as GDPR, pseudonymised data is still personal data.
- **Keep the salt secret.** The notebook uses a placeholder salt. Change it, and store it in a secrets manager, not in the notebook.
- **Only masked data reaches the model.** Tools return account IDs, briefs and summaries, and never customer IDs. Check your own bank's rules before sending any account-level data to an external API.
- **Human review.** A flag for AML review is a prompt for an analyst, not a decision. An agent should never block or report a customer on its own.

## Limitations

- **The Claude step is not tested live.** I had no API key in my environment, so I tested the agent loop with a mock client. The mock confirmed the message flow: tool results go back to the model, and the final answer comes through. Run the optional step once with your key to confirm it.
- **Search is basic.** TF-IDF matches words, not meaning. A production system would use embeddings and a vector database.
- **No balance reconciliation.** `balance_after` is recomputed in time order, but it is not checked against a bank's official ledger.
- **The large-transaction rule is simple.** Monthly salaries are above 10,000, so most flags are salaries. Real AML rules are far more detailed.
- **The brief is generated from a template.** That makes it predictable and easy to check. It is not written by a model.

## Next steps for a production agent

- Use embeddings and a vector store (for example pgvector or a managed index) for the search.
- Build an evaluation set: question, expected tool, expected answer. Run it every time you change a tool or prompt.
- Log every tool call and answer for audit.
- Add role-based access, so the agent only sees the accounts the user may see.
- Keep a human approval step for any action that affects a customer.
