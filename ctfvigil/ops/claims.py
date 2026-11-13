"""
ctfvigil/ops/claims.py
~~~~~~~~~~~~~~~~~~~~~~
Challenge claiming, ownership, and solve state management.

Responsibilities:
    - Track active claims (!claim <challenge>) to prevent duplicate effort across teammates.
    - Release claims (!unclaim <challenge>) when stepping away or getting stuck.
    - Provide team status overview (!status) summarizing active assignments and solve counts.
    - Mark challenges as solved (!solve <challenge>) with solver attribution.
    - Persist claim mappings in Redis (ctfvigil:claims:<guild_id>:<challenge_slug>).
"""

from __future__ import annotations

# Future implementation will handle claim assignment, release, and status aggregation

