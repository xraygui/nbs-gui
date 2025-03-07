from qtpy.QtWidgets import QTabWidget
import pkg_resources
from .settings import SETTINGS


class TabViewer(QTabWidget):
    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model

        self.setTabPosition(QTabWidget.North)
        self.setMovable(True)

        config = SETTINGS.gui_config

        tabs_to_include = config.get("gui", {}).get("tabs", {}).get("include", [])
        tabs_to_exclude = config.get("gui", {}).get("tabs", {}).get("exclude", [])

        explicit_inclusion = len(tabs_to_include) > 0
        self.tab_dict = {}
        tabs = pkg_resources.iter_entry_points("nbs_gui.tabs")
        for tab_entry_point in tabs:
            # Call the modifier function with model and self (as parent) to get the QWidget
            if explicit_inclusion:
                if tab_entry_point.name not in tabs_to_include:
                    continue
                print(f"Loading {tab_entry_point.name} from EntryPoint")
                tab = tab_entry_point.load()  # Load the modifier function
                if callable(tab):
                    tab_widget = tab(model)
                    self.tab_dict[tab_entry_point.name] = tab_widget
                else:
                    print("Tab was not callable")
            elif tab_entry_point.name not in tabs_to_exclude:
                print(f"Loading {tab_entry_point.name} from EntryPoint")
                tab = tab_entry_point.load()  # Load the modifier function
                if callable(tab):
                    tab_widget = tab(model)
                    print(f"Tab {tab_entry_point.name} loaded")
                    self.tab_dict[tab_entry_point.name] = tab_widget
                    tabs_to_include.append(tab_entry_point.name)
                else:
                    print("Tab was not callable")
        print("All Tabs Loaded")
        for tab_name in tabs_to_include:
            if tab_name in self.tab_dict:
                tab_widget = self.tab_dict[tab_name]
                self.addTab(tab_widget, tab_widget.name)
        print("All Tabs Added")
