.PHONY: help harness-sync harness-check plans-check

help:
	@echo "  make harness-sync    # regenera los adaptadores desde la capa canonica"
	@echo "  make harness-check   # falla si un adaptador esta stale (corre en CI)"
	@echo "  make plans-check     # falla si un plan del roadmap no trae sus obligaciones"

# El harness de agentes: la capa canonica vive en harness/ y AGENTS.md.
# Todo lo demas se genera; nunca se edita a mano.
harness-sync:
	@python3 scripts/harness-sync.py

harness-check:
	@python3 scripts/harness-sync.py --check

plans-check:
	@python3 scripts/plans-check.py --check
