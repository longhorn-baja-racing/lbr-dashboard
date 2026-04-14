from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QTableWidget, QTableWidgetItem
)
from PyQt6.QtCore import Qt


class RightPanel(QWidget):
    """Right panel widget for the dashboard, shows a graph and CSV data table."""

    def __init__(self) -> None:
        super().__init__()

        # --- Matplotlib graph ---
        self._fig = Figure(facecolor="#3a3a3a")
        self._canvas = FigureCanvasQTAgg(self._fig)
        self._ax = self._fig.add_subplot(111)
        self._style_axes()

        # --- Table ---
        self.table = QTableWidget()
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #2a2a2a;
                color: #ffffff;
                gridline-color: #555555;
            }
            QHeaderView::section {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #555555;
            }
        """)

        # --- Vertical splitter: graph on top, table on bottom ---
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self._canvas)
        splitter.addWidget(self.table)
        splitter.setSizes([350, 350])
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #555555;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)
        self.setLayout(layout)

        self.setStyleSheet("background-color: #3a3a3a; color: #ffffff;")

        # Internal data store: {column_name: [float, ...]}
        self._column_data: dict[str, list] = {}
        self._headers: list[str] = []

    def _style_axes(self) -> None:
        self._ax.set_facecolor("#2a2a2a")
        self._ax.tick_params(colors="#cccccc")
        self._ax.xaxis.label.set_color("#cccccc")
        self._ax.yaxis.label.set_color("#cccccc")
        self._ax.set_title("Select a column to plot", color="#aaaaaa", pad=8)
        for spine in self._ax.spines.values():
            spine.set_edgecolor("#555555")
        self._fig.tight_layout()
        self._canvas.draw()

    def set_data(self, headers: list[str], rows: list[list[str]]) -> None:
        """Populate the table and build internal column data for graphing."""
        self._headers = headers
        self._column_data = {}

        for i, header in enumerate(headers):
            values = []
            for row in rows:
                if i < len(row):
                    try:
                        values.append(float(row[i]))
                    except ValueError:
                        values.append(None)
            self._column_data[header] = values

        # Populate table
        self.table.setColumnCount(len(headers))
        self.table.setRowCount(len(rows))
        self.table.setHorizontalHeaderLabels(headers)

        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                self.table.setItem(r, c, QTableWidgetItem(value))
    
    def highlight_column(self, column_index):

        if column_index < 0:
            return

        self.table.clearSelection()
        self.table.selectColumn(column_index)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectColumns)

        # Reset graph
        self._ax.clear()
        self._style_axes()

    def plot_column(self, column_name: str) -> None:
        """Plot the named column as a line graph."""
        values = self._column_data.get(column_name)
        if values is None:
            return

        # Use timestamp_ms as x-axis if available, else sample index
        x_label = "Sample"
        if "timestamp_ms" in self._column_data and column_name != "timestamp_ms":
            x = self._column_data["timestamp_ms"]
            x_label = "Time (ms)"
        else:
            x = list(range(len(values)))

        # Filter out None pairs
        pairs = [(xi, yi) for xi, yi in zip(x, values) if xi is not None and yi is not None]
        if not pairs:
            return
        xs, ys = zip(*pairs)

        self._ax.clear()
        self._style_axes()
        self._ax.plot(xs, ys, color="#00aaff", linewidth=2, marker="o", markersize=3)
        self._ax.set_title(column_name, color="#ffffff", pad=8)
        self._ax.set_xlabel(x_label, color="#cccccc")
        self._ax.set_ylabel(column_name, color="#cccccc")
        self._fig.tight_layout()
        self._canvas.draw()
