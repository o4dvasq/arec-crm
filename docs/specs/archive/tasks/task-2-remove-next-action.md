# Task 2: Remove Next Action field from all prospect records

## File
`crm/prospects.md`

## What to do

Delete every line that matches `- **Next Action:**` from the file. This field appears once per prospect record (~50+ records). Some have trailing whitespace, some have no space after the colon — match all variants.

## Rules

- Remove the entire line (not just the value)
- Do NOT touch any other fields: Stage, Target, Committed, Primary Contact, Closing, Urgency, Assigned To, Notes, Last Touch
- Do NOT remove blank lines between prospect records
- Do NOT change any other content

## Pattern to match and delete

All of these forms should be deleted:
```
- **Next Action:**
- **Next Action:**
- **Next Action:** some text here
```

## Verification

After the edit, confirm:
- Zero lines in the file contain `Next Action`
- The total number of prospect headings (lines starting with `###`) is unchanged
- Each prospect record still has all other fields intact
