"""Domain layer: the shared vocabulary of the whole system.

Nothing in here does I/O (no database, no network, no files). Every other
layer imports from ``domain``; ``domain`` imports from nobody. Keeping this
layer pure is what makes the rest of the code easy to test.
"""
