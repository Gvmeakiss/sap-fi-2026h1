import sys

from sap_s4hana_journal.cli import main


if __name__ == "__main__":
    if "--label" not in sys.argv:
        sys.argv.extend(["--label", "2026H1"])
    if "--output-dir" not in sys.argv:
        sys.argv.extend(["--output-dir", "output_2026H1"])
    if "--year" not in sys.argv:
        sys.argv.extend(["--year", "2026"])
    if "--date-from" not in sys.argv:
        sys.argv.extend(["--date-from", "20260101"])
    if "--date-to" not in sys.argv:
        sys.argv.extend(["--date-to", "20260630"])
    if "--client" not in sys.argv:
        sys.argv.extend(["--client", "800"])
    main()
