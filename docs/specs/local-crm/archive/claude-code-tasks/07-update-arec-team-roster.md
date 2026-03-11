# Task 7: Update AREC Team Config with Full Roster

**Status:** DONE
**File:** `crm/config.md`
**Dependencies:** None

## What Changed

Replaced the 7-member team list with the full 15-member roster using `Short | Full Name` format.

```markdown
## AREC Team
- Tony | Tony Avila
- Oscar | Oscar Vasquez
- Truman | Truman Flynn
- Zach | Zach Reisner
- Nate | Nate Cichon
- Patrick | Patrick Fichtner
- Mike R | Mike Righetti
- Sahil | Sahil Jehti
- Jake | Jake Weintraub
- Kevin V | Kevin Van Gorder
- Jane | Jane Lumley
- Anthony | Anthony Albuquerque
- Ian | Ian Morgan
- James | James Walton
- Paige | Paige (Chief of Staff)
```

Previously only had: Tony Avila, Oscar Vasquez, Zach Reisner, James Walton, Anthony Albuquerque, Ian Morgan, Kevin Van Gorder.

Added: Truman, Nate, Patrick, Mike R, Sahil, Jake, Jane, Paige.

## Acceptance Criteria

```python
config = load_crm_config()
assert len(config['team']) == 15
assert len(config['team_map']) == 15
shorts = [m['short'] for m in config['team_map']]
assert 'Mike R' in shorts
assert 'Kevin V' in shorts
assert 'Truman' in shorts
```
