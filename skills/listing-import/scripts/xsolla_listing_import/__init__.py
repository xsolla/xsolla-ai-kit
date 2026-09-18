"""Listing-to-shop mapping, coverage measurement and write planning.

Nothing is re-exported on purpose.  Import the module you mean, so a reader of a
traceback can see which family of rule fired.

What this package deliberately does NOT do: fetch a store page.  The extraction
step is the agent's, not this code's, for two reasons.  A hand-written HTML
parser for three storefronts rots the week any of them reships its markup, and
an agent reading a page is both better at it and able to say what it could not
find.  So the contract is the other way round: the agent produces a
``listing.json`` against the schema in ``listing_schema.py``, and everything
here is deterministic work over that document -- validate it, measure its
coverage, map it onto blocks, and emit the write plan.
"""
