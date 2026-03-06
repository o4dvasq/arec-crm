# SharePoint Migration Discussion

**Date:** 2026-02-25
**Source:** [Notion](https://www.notion.so/3128c54f8b2c808b84e6f33f5aa9011a)
**Attendees:** Oscar Vasquez, Stacey, Juan (dropped early)

## Summary

Knowledge-sharing call with Stacey about her organization's migration from Citrix ShareFile to SharePoint. Oscar is evaluating a similar move from Egnyte/Ignite and wanted lessons learned.

**Migration Experience:** Stacey's migration started between Christmas and New Year's and is still not complete months later. She described the execution as "an absolute failure" — primarily because Ali (their IT lead) didn't follow the planned approach of starting with a test subject migration, working out bugs, then proceeding systematically. Despite the rocky implementation, Stacey is pleased with the end result and says it was worth it.

**Key Lessons for AREC:** The biggest technical gotcha: SharePoint has character limits on file paths, and Microsoft automatically consumes characters with its own path prefix (SharePoint/files/documents/...). Stacey's team had to reorganize file names post-migration across over a million records. Oscar should address file naming conventions before any migration begins. The team spent June through October reorganizing their file structure before the migration — "don't migrate a pile of dog poop from one platform to another." Total data: ~9-10 TB (7.85 TB in one person's personal folder alone).

**SharePoint Benefits:** Native Windows Explorer integration (no separate client app like ShareFile/Ignite), automatic OneDrive backup of personal folders, real-time document collaboration eliminating version-control email chains, seamless save/share from any Microsoft app, Teams integration for collaborative documents, and cross-platform consistency across tablets and laptops.

**Workflow Insights:** Stacey's team uses SharePoint primarily through Teams and Windows Explorer (not browser-based SharePoint pages). The loan originations team at AREC is already building browser-based SharePoint pages with dashboards and role-based views. Stacey's best practice: collaborative working documents live in SharePoint; only finalized "platinum versions" go to Ignite for auditors.

**AI Integration:** Stacey is transitioning from Claude/ChatGPT to Copilot for the cohesive Microsoft interface. Oscar shared his advanced use case: using Copilot to consolidate a year's worth of IC meeting transcripts, then feeding that into Claude to extract lending standards and best practices — creating an institutional knowledge database for evaluating new deals.

**AREC Context:** Oscar noted AREC isn't "broken" on Ignite currently, but sees benefits in driving real-time collaboration and reducing friction. There's apparently a conversion program that runs data from Ignite to SharePoint, which would make AREC's migration smoother than Stacey's ShareFile experience.

## Key Decisions

- No decisions — informational call for Oscar's planning

## Action Items

- [ ] **Oscar** — Address file naming conventions / character limits before any migration
- [ ] **Oscar/Juan** — Schedule follow-up technical discussion with Stacey's team

## Open Questions

- Timeline for AREC's potential Ignite → SharePoint migration
- Scope: full migration vs. phased approach starting with specific teams
- Ignite-to-SharePoint conversion tool capabilities and limitations
