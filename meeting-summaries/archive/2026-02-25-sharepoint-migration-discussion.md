# SharePoint Migration Discussion

**Date:** 2026-02-25
**Source:** [Notion](https://www.notion.so/3128c54f8b2c808b84e6f33f5aa9011a)
**Attendees:** Oscar Vasquez, Stacey, Juan (dropped early for technical discussion later)

## Summary

Oscar spoke with Stacey, who recently migrated her organization from Citrix ShareFile to SharePoint. The conversation was an information-gathering session for Oscar, who is evaluating a similar migration from Egnyte/Ignite to SharePoint for AREC.

Stacey's migration started between Christmas and New Year's and is still ongoing — she described the execution as "an absolute failure," largely because Ali (her IT lead) didn't follow the structured game plan she had outlined (pilot migration first, work out bugs, then systematically roll out). Despite the rough implementation, Stacey is pleased with the end result and says SharePoint is significantly better than both ShareFile and Ignite.

Key practical lessons: file naming conventions must be addressed before migration because SharePoint has character limits on file paths (Microsoft automatically consumes characters with its path prefix). Stacey's team had to reorganize over a million records post-migration to shorten file names. They had ~9-10 TB of data to migrate. The team reorganized their file structure from June to October before the migration to avoid moving a mess to a new platform.

Oscar shared his advanced AI workflow — using Copilot to consolidate all IC meeting transcripts from the past year, feeding that into Claude to extract lending standards and best practices, then using that institutional knowledge database to evaluate new deals. Stacey was impressed.

The call was meant to include a technical discussion with Juan, but that was deferred to later in the day.

## Key Decisions

- Oscar confirmed AREC's motivation is collaboration improvement, not fixing a broken system
- Technical discussion with Juan rescheduled for later the same day

## Action Items

- [ ] **Juan** — Schedule follow-up technical discussion with Oscar and Stacey
- [ ] **Oscar** — Address file naming conventions and path length limits before any migration planning

## Open Questions

- Is there a conversion program from Ignite to SharePoint (Stacey mentioned one exists)?
- What's the timeline/priority for AREC's potential migration?
- How does this fit with AREC's current Egnyte setup?
