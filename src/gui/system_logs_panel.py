"""
System Logs Panel
UI component that displays structured logs from SystemLogService in real time.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QFileDialog,
)
from PyQt6.QtGui import QColor
import csv
from datetime import datetime

from .system_log_service import system_log_service, SystemLogEntry


class SystemLogsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[SystemLogEntry] = []
        self._max_rows = 2000
        self._filter_type = "ALL"
        self.setup_ui()
        self._connect()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        header_layout = QHBoxLayout()
        title = QLabel("System Logs")
        title.setStyleSheet("font-weight: bold; font-size: 16px;")
        header_layout.addWidget(title)

        self.count_label = QLabel("0")
        self.count_label.setStyleSheet("padding-left: 6px; color: #aaa;")
        header_layout.addWidget(self.count_label)

        header_layout.addStretch()

        header_layout.addWidget(QLabel("Type:"))
        self.type_filter = QComboBox()
        self.type_filter.addItems(["ALL", "TRADING", "MESSAGE", "WARNING", "ERROR", "ATTENTION"])
        self.type_filter.currentTextChanged.connect(self._apply_filters)
        header_layout.addWidget(self.type_filter)

        header_layout.addWidget(QLabel("Search:"))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search logs...")
        self.search_box.setMaximumWidth(220)
        self.search_box.textChanged.connect(self._apply_filters)
        header_layout.addWidget(self.search_box)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_logs)
        header_layout.addWidget(clear_btn)

        export_btn = QPushButton("Export CSV")
        export_btn.clicked.connect(self._export_csv)
        header_layout.addWidget(export_btn)

        layout.addLayout(header_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Type", "User", "Strategy", "Portfolio", "Message"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

    def _connect(self):
        # Initialize with real stored entries (starts empty; no dummy data)
        for entry in system_log_service.get_entries():
            self._rows.append(entry)

        self._refresh_table()
        system_log_service.log_added.connect(self._on_log_added)
        system_log_service.logs_cleared.connect(self._on_logs_cleared)

    def _clear_logs(self):
        reply = QMessageBox.question(
            self,
            "Clear System Logs",
            "Clear all system logs?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            system_log_service.clear()

    def _on_logs_cleared(self):
        self._rows.clear()
        self._refresh_table()

    def _on_log_added(self, entry: SystemLogEntry):
        self._rows.append(entry)
        if len(self._rows) > self._max_rows:
            self._rows = self._rows[-self._max_rows :]
        self._refresh_table(auto_scroll=True)

    def _apply_filters(self):
        self._filter_type = self.type_filter.currentText()
        self._refresh_table()

    def _matches(self, entry: SystemLogEntry) -> bool:
        if self._filter_type != "ALL" and entry.log_type != self._filter_type:
            return False
        s = self.search_box.text().strip().lower()
        if not s:
            return True
        hay = " ".join([entry.timestamp, entry.log_type, entry.user, entry.strategy, entry.portfolio, entry.message]).lower()
        return s in hay

    def _refresh_table(self, auto_scroll: bool = False):
        filtered = [e for e in self._rows if self._matches(e)]
        self.count_label.setText(str(len(filtered)))

        self.table.setRowCount(len(filtered))
        for row, e in enumerate(filtered):
            self._set_item(row, 0, e.timestamp, e)
            self._set_item(row, 1, e.log_type, e)
            self._set_item(row, 2, e.user, e)
            self._set_item(row, 3, e.strategy, e)
            self._set_item(row, 4, e.portfolio, e)
            self._set_item(row, 5, e.message, e)

        if auto_scroll and len(filtered) > 0:
            self.table.scrollToBottom()

    def _export_csv(self):
        filtered = [e for e in self._rows if self._matches(e)]
        if not filtered:
            QMessageBox.information(self, "Export CSV", "No logs to export (current filter is empty).")
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"system_logs_{ts}.csv"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export System Logs to CSV",
            default_name,
            "CSV Files (*.csv)",
        )
        if not file_path:
            return

        headers = ["Timestamp", "Type", "User", "Strategy", "Portfolio", "Message"]
        try:
            # Use utf-8-sig to make Excel happy on Windows (adds BOM)
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(headers)
                for e in filtered:
                    w.writerow([e.timestamp, e.log_type, e.user, e.strategy, e.portfolio, e.message])

            QMessageBox.information(self, "Export CSV", f"Exported {len(filtered)} log rows.")
        except Exception as ex:
            QMessageBox.warning(self, "Export CSV", f"Failed to export CSV: {ex}")

    def _set_item(self, row: int, col: int, text: str, entry: SystemLogEntry):
        item = QTableWidgetItem(text or "")
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

        # Color-code Type column (and subtly tint row)
        if col == 1:
            if entry.log_type == "ERROR":
                item.setForeground(QColor("#f48771"))
            elif entry.log_type == "WARNING":
                item.setForeground(QColor("#dcdcaa"))
            elif entry.log_type == "TRADING":
                item.setForeground(QColor("#4ec9b0"))
            elif entry.log_type == "ATTENTION":
                item.setForeground(QColor("#c586c0"))
            else:
                item.setForeground(QColor("#d4d4d4"))

        self.table.setItem(row, col, item)


