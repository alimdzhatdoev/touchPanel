from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget


class SplashWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("SplashWidget")

        title = QLabel("Touch Panel Studio")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 28px; font-weight: 600;")

        subtitle = QLabel("Загрузка…")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 16px; color: #666;")

        self.progress = QProgressBar()
        # Неопределённый режим: на части тем Windows выглядит как «застывший» кусок — это норма.
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(18)

        layout = QVBoxLayout()
        layout.setContentsMargins(48, 48, 48, 48)
        layout.setSpacing(18)
        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(10)
        layout.addWidget(self.progress)
        layout.addStretch(2)
        self.setLayout(layout)

