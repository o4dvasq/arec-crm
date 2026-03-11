.PHONY: dashboard briefing inbox tests briefs kill

dashboard:          ## Launch Overwatch dashboard on :3001
	lsof -ti:3001 | xargs kill -9 2>/dev/null; python3 app/delivery/dashboard.py

briefing:           ## Run morning briefing
	python3 app/main.py

inbox:              ## Drain crm@avilacapllc.com shared mailbox
	python3 app/drain_inbox.py

tests:              ## Run test suite
	python3 -m pytest app/tests/

briefs:             ## Bulk refresh Stage 5 relationship briefs
	python3 scripts/refresh_interested_briefs.py

kill:               ## Kill whatever's running on :3001
	lsof -ti:3001 | xargs kill -9 2>/dev/null || true

help:               ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  make %-14s %s\n", $$1, $$2}'
