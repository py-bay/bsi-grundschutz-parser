"""Allow `python -m bsi_pipeline ...` as an alternative to the console script."""

from bsi_pipeline.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
