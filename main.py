"""Entry point. Run with:  python main.py"""

from cvat_export.app import main


if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        print(
            "\n\nOperation cancelled by user."
        )

    except Exception as exc:
        print(
            "\n\nERROR:"
        )
        print(exc)
        raise
