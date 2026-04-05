# RESULTS

This repository includes the required benchmark questions, seeded reference SQL, and an automated benchmark runner in `run_benchmark.py`.

## Local Execution Status

The following steps were executed successfully in this environment:

- `python setup_database.py`
- `python seed_memory.py`
- FastAPI import and smoke-test of `/health`

The live 20-question Gemini benchmark was **not executed locally** because `GOOGLE_API_KEY` was not available in this environment at implementation time. This is documented intentionally rather than guessed. Once a Gemini key is added, run:

```bash
python run_benchmark.py
```

That command will send the benchmark questions through the real `/chat` endpoint and overwrite this file with the generated SQL, pass/fail status, and result summaries.

## Prepared Benchmark Set

The project is pre-seeded with these 20 benchmark questions:

1. How many patients do we have?
2. List all doctors and their specializations
3. Show me appointments for last month
4. Which doctor has the most appointments?
5. What is the total revenue?
6. Show revenue by doctor
7. How many cancelled appointments last quarter?
8. Top 5 patients by spending
9. Average treatment cost by specialization
10. Show monthly appointment count for the past 6 months
11. Which city has the most patients?
12. List patients who visited more than 3 times
13. Show unpaid invoices
14. What percentage of appointments are no-shows?
15. Show the busiest day of the week for appointments
16. Revenue trend by month
17. Average appointment duration by doctor
18. List patients with overdue invoices
19. Compare revenue between departments
20. Show patient registration trend by month

## Known Constraint

- Because invoices are linked to patients rather than appointments or doctors, doctor and department revenue questions are modeled using treatment costs joined through completed appointments. This is the most defensible interpretation of the provided schema.
