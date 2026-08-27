.PHONY: help plans-check ritmo

help:
	@echo "  make plans-check   # falla si un plan del roadmap no trae sus obligaciones"
	@echo "  make ritmo         # el ritmo real de los planes cerrados"
	@echo ""
	@echo "  Son atajos. Los scripts se pueden llamar directamente y es lo que hace CI:"
	@echo "    python3 scripts/plans-check.py --check"
	@echo "    python3 scripts/plan-time.py <slug>"

plans-check:
	@python3 scripts/plans-check.py --check

ritmo:
	@python3 scripts/plan-time.py --ritmo
