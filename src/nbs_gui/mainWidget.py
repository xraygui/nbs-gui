from qtpy.QtWidgets import QTabWidget
from importlib.metadata import entry_points
from .settings import SETTINGS


class TabViewer(QTabWidget):
    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model
        self._tab_order = []
        self._entry_point_map = {}

        self.setTabPosition(QTabWidget.North)
        self.setMovable(True)

        config = SETTINGS.gui_config

        tabs_to_include = config.get("gui", {}).get("tabs", {}).get("include", [])
        tabs_to_exclude = config.get("gui", {}).get("tabs", {}).get("exclude", [])

        explicit_inclusion = len(tabs_to_include) > 0
        self.tab_dict = {}
        tabs = entry_points(group="nbs_gui.tabs")
        for tab_entry_point in tabs:
            if explicit_inclusion:
                if tab_entry_point.name not in tabs_to_include:
                    continue
                print(f"Loading {tab_entry_point.name} from EntryPoint")
                tab = tab_entry_point.load()
                if callable(tab):
                    tab_widget = tab(model)
                    self.tab_dict[tab_entry_point.name] = tab_widget
                    self._entry_point_map[tab_entry_point.name] = tab_entry_point
                else:
                    print("Tab was not callable")
            elif tab_entry_point.name not in tabs_to_exclude:
                print(f"Loading {tab_entry_point.name} from EntryPoint")
                tab = tab_entry_point.load()
                if callable(tab):
                    tab_widget = tab(model)
                    print(f"Tab {tab_entry_point.name} loaded")
                    self.tab_dict[tab_entry_point.name] = tab_widget
                    tabs_to_include.append(tab_entry_point.name)
                    self._entry_point_map[tab_entry_point.name] = tab_entry_point
                else:
                    print("Tab was not callable")
        print("All Tabs Loaded")
        for tab_name in tabs_to_include:
            if tab_name in self.tab_dict:
                tab_widget = self.tab_dict[tab_name]
                self.addTab(tab_widget, tab_widget.name)
                self._tab_order.append(tab_name)
        print("All Tabs Added")

    def reload_tabs(self, model):
        """
        Reload reloadable tabs in place using the provided model.

        Parameters
        ----------
        model : ViewerModel
            Application model containing the refreshed beamline.
        """
        self.model = model
        latest_entries = {ep.name: ep for ep in entry_points(group="nbs_gui.tabs")}
        for tab_name in list(self._tab_order):
            widget = self.tab_dict.get(tab_name)
            if widget is None:
                continue
            if not getattr(widget, "reloadable", False):
                continue
            if hasattr(widget, "teardown"):
                try:
                    widget.teardown()
                except Exception as exc:
                    print(f"Teardown failed for {tab_name}: {exc}")
            tab_index = self.indexOf(widget)
            self.removeTab(tab_index)
            widget.setParent(None)
            widget.deleteLater()
            entry_point = latest_entries.get(tab_name) or self._entry_point_map.get(
                tab_name
            )
            if entry_point is None:
                print(f"No entry point for reloadable tab {tab_name}")
                self.tab_dict.pop(tab_name, None)
                continue
            try:
                tab_factory = entry_point.load()
                if callable(tab_factory):
                    new_widget = tab_factory(model)
                    self.tab_dict[tab_name] = new_widget
                    self._entry_point_map[tab_name] = entry_point
                    self.insertTab(tab_index, new_widget, new_widget.name)
                else:
                    print(f"Entry point for {tab_name} not callable on reload")
                    self.tab_dict.pop(tab_name, None)
            except Exception as exc:
                print(f"Reload failed for tab {tab_name}: {exc}")
