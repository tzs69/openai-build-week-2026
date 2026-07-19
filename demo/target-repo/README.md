# Merge Marshal Demo API

This intentionally small Python API is the curated target repository for the Merge Marshal MVP.

Its starting state supports three planned changes:

- Rename `UserResponse.user_id` to `actor_id`.
- Add response caching that consumes the canonical identity field.
- Add structured logging to the independent payment endpoint.

Run the starting tests from this directory:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The current verified architecture is stored only in `.graph/graph.json`.
