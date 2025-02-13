from qtpy.QtWidgets import QComboBox
from qtpy.QtCore import Qt


class ScrollingComboBox(QComboBox):
    """
    A QComboBox subclass that properly limits the number of visible items
    in the dropdown and adds scrolling.

    Parameters
    ----------
    max_visible_items : int, optional
        Maximum number of items to show before scrolling, by default 15
    parent : QWidget, optional
        Parent widget
    """

    def __init__(self, max_visible_items=15, parent=None):
        super().__init__(parent)
        self.max_visible_items = max_visible_items
        # Make editable but read-only to enable item limit
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        # Remove the frame around the line edit
        self.lineEdit().setFrame(False)
        self.setMaxVisibleItems(max_visible_items)

    def showPopup(self):
        """Override showPopup to ensure proper popup behavior"""
        # Get current text to restore selection
        current_text = self.currentText()

        # Show the popup
        super().showPopup()

        # Get the popup view
        popup = self.view()

        if popup:
            # Enable vertical scrollbar
            popup.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

            # Calculate height based on first item
            item_height = popup.visualRect(popup.model().index(0, 0)).height()
            popup_height = item_height * min(self.max_visible_items, self.count())

            # Set the popup height
            popup.setFixedHeight(popup_height)

            # Ensure selected item is visible
            index = self.findText(current_text)
            if index >= 0:
                popup.scrollTo(popup.model().index(index, 0))
