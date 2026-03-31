from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from touch_panel_studio.app.bootstrap import bootstrap_app
from touch_panel_studio.core.branding import app_logo_path


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Touch Panel Studio")
    app.setOrganizationName("TouchPanel")

    logo = app_logo_path()
    if logo is not None:
        icon = QIcon(str(logo))
        app.setWindowIcon(icon)

    window = bootstrap_app()
    if logo is not None:
        window.setWindowIcon(icon)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

