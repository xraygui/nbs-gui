from bluesky_live.event import EmitterGroup, Event
from bluesky_queueserver import bind_plan_arguments
from qtpy.QtCore import Signal, QObject
import collections
import copy
import uuid


class QueueStagingModel(QObject):
    signal_item_selection_changed = Signal(object)
    signal_plan_queue_changed = Signal(object, object)

    def __init__(self, model, parent=None):
        super().__init__()
        self._plan_queue_items = []
        self._plan_queue_items_pos = {}
        self._selected_queue_item_uids = []
        self._map_column_labels_to_keys = {}
        self.run_engine_client = model
        self._allowed_plans = self.run_engine_client._allowed_plans

        # Initialize the default mapping
        self.set_map_param_labels_to_keys()

        self.events = EmitterGroup(
            source=self,
            plan_queue_changed=Event,
            allowed_devices_changed=Event,
            allowed_plans_changed=Event,
            queue_item_selection_changed=Event,
        )

    def load_plan_queue(self):
        """Update the position mapping and emit queue changed event."""
        self._plan_queue_items_pos = {
            item["item_uid"]: n
            for n, item in enumerate(self._plan_queue_items)
            if "item_uid" in item
        }

        # Deselect queue items that are not in the queue or are not part of the
        # contiguous selection. The selection will be cleared when the table is
        # reloaded, so save it in local variable.
        selected_uids = self.selected_queue_item_uids
        pos, uids = -1, []
        for uid in selected_uids:
            p = self.queue_item_uid_to_pos(uid)
            if p >= 0:
                if (pos < 0) or ((p >= 0) and (p == pos + 1)):
                    pos = p
                    uids.append(uid)
                else:
                    break
        self.selected_queue_item_uids = uids

        self.events.plan_queue_changed(
            plan_queue_items=self._plan_queue_items,
            selected_item_uids=self._selected_queue_item_uids,
        )

    def get_allowed_plan_names(self):
        """Get list of allowed plan names."""
        return list(self._allowed_plans.keys()) if self._allowed_plans else []

    def set_map_param_labels_to_keys(self, *, map_dict=None):
        """
        Set mapping between labels and item dictionary keys.

        Parameters
        ----------
        map_dict : dict or None
            Map dictionary or None to use the default dictionary
        """
        if (map_dict is not None) and not isinstance(map_dict, collections.abc.Mapping):
            raise ValueError(
                f"Incorrect type ('{type(map_dict)}') of the parameter 'map'. "
                "'None' or 'dict' is expected"
            )

        _default_map = {
            "": ("item_type",),
            "Name": ("name",),
            "Parameters": ("kwargs",),
            "USER": ("user",),
            "GROUP": ("user_group",),
            "STATUS": ("result", "exit_status"),
        }
        map_dict = map_dict if (map_dict is not None) else _default_map
        self._map_column_labels_to_keys = map_dict

    def get_bound_item_arguments(self, item):
        """Get bound arguments for an item."""
        item_args = item.get("args", [])
        item_kwargs = item.get("kwargs", {})
        item_type = item.get("item_type", None)
        item_name = item.get("name", None)

        try:
            if item_type == "plan":
                plan_parameters = self._allowed_plans.get(item_name, None)
                if plan_parameters is None:
                    raise RuntimeError(
                        f"Plan '{item_name}' is not in the list of allowed plans"
                    )
                bound_arguments = bind_plan_arguments(
                    plan_args=item_args,
                    plan_kwargs=item_kwargs,
                    plan_parameters=plan_parameters,
                )
                # If the arguments were bound successfully, then replace 'args' and 'kwargs'.
                item_args = []
                item_kwargs = bound_arguments.arguments
        except Exception:
            pass

        return item_args, item_kwargs

    def get_item_value_for_label(self, *, item, label, as_str=True):
        """
        Returns parameter value of the item for given label.

        Parameters
        ----------
        item : dict
            Dictionary containing item parameters
        label : str
            Label (e.g. table column name)
        as_str : boolean
            ``True`` - return string representation of the value, otherwise
            return the value

        Returns
        -------
        str
            column value represented as a string

        Raises
        ------
        KeyError
            label or parameter is not found in the dictionary
        """
        try:
            key_seq = self._map_column_labels_to_keys[label]
        except KeyError:
            raise KeyError(f"Label '{label}' is not found in the map dictionary")

        # Follow the path in the dictionary. 'KeyError' exception is raised if a
        # key does not exist
        try:
            value = item
            if (len(key_seq) == 1) and (key_seq[-1] in ("args", "kwargs")):
                # Special case: combine args and kwargs to be displayed in one column
                value = {
                    "args": value.get("args", []),
                    "kwargs": value.get("kwargs", {}),
                }
            else:
                for key in key_seq:
                    value = value[key]
        except KeyError:
            raise KeyError(
                f"Parameter with keys {key_seq} is not found in the item " "dictionary"
            )

        if as_str:
            key = key_seq[-1]

            s = ""
            if key in ("args", "kwargs"):
                value["args"], value["kwargs"] = self.get_bound_item_arguments(item)

                s_args, s_kwargs = "", ""
                if value["args"] and isinstance(
                    value["args"], collections.abc.Iterable
                ):
                    s_args = ", ".join(f"{v}" for v in value["args"])
                if value["kwargs"] and isinstance(
                    value["kwargs"], collections.abc.Mapping
                ):
                    s_kwargs = ", ".join(
                        f"{k}: {v}" for k, v in value["kwargs"].items()
                    )
                s = ", ".join([_ for _ in [s_args, s_kwargs] if _])

            elif key == "args":
                if value and isinstance(value, collections.abc.Iterable):
                    s = ", ".join(f"{v}" for v in value)

            elif key == "item_type":
                # Print capitalized first letter of the item type ('P' or 'I')
                s_tmp = str(value)
                if s_tmp:
                    s = s_tmp[0].upper()

            else:
                s = str(value)

        else:
            s = value

        return s

    # ============================================================================
    #                         Queue operations

    @property
    def selected_queue_item_uids(self):
        """Get selected queue item UIDs."""
        return self._selected_queue_item_uids

    @selected_queue_item_uids.setter
    def selected_queue_item_uids(self, item_uids):
        """Set selected queue item UIDs."""
        if self._selected_queue_item_uids != item_uids:
            self._selected_queue_item_uids = item_uids.copy()
            self.events.queue_item_selection_changed(selected_item_uids=item_uids)

    def queue_item_uid_to_pos(self, item_uid):
        """Convert item UID to position. Returns -1 if item was not found."""
        return self._plan_queue_items_pos.get(item_uid, -1)

    def queue_item_pos_to_uid(self, n_item):
        """Convert item position to UID."""
        try:
            item_uid = self._plan_queue_items[n_item]["item_uid"]
        except Exception:
            item_uid = ""
        return item_uid

    def queue_item_by_uid(self, item_uid):
        """
        Returns deep copy of the item based on item UID or None if the item was not found.

        Parameters
        ----------
        item_uid : str
            UID of an item. If ``item_uid=""`` then None will be returned

        Returns
        -------
        dict or None
            Dictionary of item parameters or ``None`` if the item was not found
        """
        if item_uid:
            sel_item_pos = self.queue_item_uid_to_pos(item_uid)
            if sel_item_pos >= 0:
                return copy.deepcopy(self._plan_queue_items[sel_item_pos])
        return None

    def _queue_items_move(self, *, sel_items, ref_item, position):
        """
        Move the batch of selected items above or below the reference item.

        Parameters
        ----------
        sel_items : list
            the list of selected item UIDs
        ref_item : str
            UID of the reference item
        position : str
            "before" - the items are moved above the target item, "after" - below the target item
        """
        supported_positions = ("before", "after")
        if position not in supported_positions:
            raise ValueError(
                f"Unsupported position: {position}, supported values: {supported_positions}"
            )

        if not sel_items or (ref_item in sel_items):
            return  # Nothing to do

        # Get positions of selected items and reference item
        sel_positions = [self.queue_item_uid_to_pos(uid) for uid in sel_items]
        ref_position = self.queue_item_uid_to_pos(ref_item)

        if ref_position < 0:
            return  # Reference item not found

        # Remove selected items from their current positions
        sel_positions.sort(reverse=True)  # Remove from highest to lowest
        items_to_move = []
        for pos in sel_positions:
            if pos >= 0:
                items_to_move.append(self._plan_queue_items.pop(pos))

        # Insert items at the target position
        if position == "before":
            insert_pos = ref_position
        else:  # after
            insert_pos = ref_position + 1

        # Adjust insert position based on how many items we removed before the insert position
        items_removed_before_insert = sum(
            1 for pos in sel_positions if pos < insert_pos
        )
        insert_pos -= items_removed_before_insert

        for item in reversed(items_to_move):
            self._plan_queue_items.insert(insert_pos, item)

        # Update the queue
        self.load_plan_queue()

        # Update selection to new positions
        new_sel_uids = [item["item_uid"] for item in items_to_move]
        self.selected_queue_item_uids = new_sel_uids

    def queue_items_move_up(self):
        """Move the selected batch of items up by one position."""
        n_items = len(self._plan_queue_items)
        n_sel_items = len(self.selected_queue_item_uids)
        if not n_items or not n_sel_items or (n_items - n_sel_items < 1):
            return

        item_uid = self.selected_queue_item_uids[0]
        n_item = self.queue_item_uid_to_pos(item_uid)
        if item_uid and (n_item > 0):
            n_item_above = n_item - 1
            item_uid_above = self.queue_item_pos_to_uid(n_item_above)
            self._queue_items_move(
                sel_items=self._selected_queue_item_uids,
                ref_item=item_uid_above,
                position="before",
            )

    def queue_items_move_down(self):
        """Move the selected batch of items down by one position."""
        n_items = len(self._plan_queue_items)
        n_sel_items = len(self.selected_queue_item_uids)
        if not n_items or not n_sel_items or (n_items - n_sel_items < 1):
            return

        item_uid = self.selected_queue_item_uids[-1]  # Use last selected item
        n_item = self.queue_item_uid_to_pos(item_uid)
        if item_uid and (0 <= n_item < n_items - 1):  # Check if we can move down
            n_item_below = n_item + 1  # Find item below the last selected item
            item_uid_below = self.queue_item_pos_to_uid(n_item_below)
            print(
                f"DEBUG: queue_items_move_down - n_item_below={n_item_below}, item_uid_below={item_uid_below}"
            )
            print(
                f"DEBUG: queue_items_move_down - selected_uids={self._selected_queue_item_uids}"
            )

            self._queue_items_move(
                sel_items=self._selected_queue_item_uids,
                ref_item=item_uid_below,
                position="after",  # Move selection after the item below
            )
        else:
            print(
                f"DEBUG: queue_items_move_down - cannot move down: item_uid={item_uid}, n_item={n_item}, n_items={n_items}"
            )

    def queue_items_move_in_place_of(self, uid_ref_item):
        """
        Move the selected batch of items in the queue so that the first item of the batch assumes
        the position of the reference item.
        """
        n_items = len(self._plan_queue_items)
        n_sel_items = len(self.selected_queue_item_uids)
        if not n_items or not n_sel_items or (n_items - n_sel_items < 1):
            return

        sel_item_uid_top = self.selected_queue_item_uids[0]
        sel_item_uid_bottom = self.selected_queue_item_uids[-1]
        n_item_top = self.queue_item_uid_to_pos(sel_item_uid_top)
        n_item_bottom = self.queue_item_uid_to_pos(sel_item_uid_bottom)
        n_item_to_replace = self.queue_item_uid_to_pos(uid_ref_item)

        if (n_item_to_replace < n_item_top) or (n_item_to_replace > n_item_bottom):
            position = "before" if (n_item_to_replace < n_item_top) else "after"
            self._queue_items_move(
                sel_items=self._selected_queue_item_uids,
                ref_item=uid_ref_item,
                position=position,
            )

    def queue_items_move_to_top(self):
        """Move the selected batch of items to the top of the queue."""
        if not self._plan_queue_items:
            return
        self.queue_items_move_in_place_of(self._plan_queue_items[0].get("item_uid", ""))

    def queue_items_move_to_bottom(self):
        """Move the selected batch of items to the bottom of the queue."""
        if not self._plan_queue_items:
            return
        self.queue_items_move_in_place_of(
            self._plan_queue_items[-1].get("item_uid", "")
        )

    def queue_items_remove(self):
        """Delete the selected batch of items from queue."""
        sel_item_uids = self.selected_queue_item_uids.copy()
        if sel_item_uids:
            # Find and set UID of an item that will be selected once the current item is removed
            sel_item_uid_top = sel_item_uids[0]
            sel_item_uid_bottom = sel_item_uids[-1]
            n_item_top = self.queue_item_uid_to_pos(sel_item_uid_top)
            n_item_bottom = self.queue_item_uid_to_pos(sel_item_uid_bottom)

            n_items = len(self._plan_queue_items)

            if n_items <= 1:
                n_sel_item_new = -1
            elif n_item_bottom < n_items - 1:
                n_sel_item_new = n_item_bottom + 1
            else:
                n_sel_item_new = n_item_top - 1

            sel_item_new_uid = self.queue_item_pos_to_uid(n_sel_item_new)
            if sel_item_new_uid:
                self.selected_queue_item_uids = [sel_item_new_uid]
            else:
                self.selected_queue_item_uids = []

            # Remove items from highest to lowest position
            sel_positions = [self.queue_item_uid_to_pos(uid) for uid in sel_item_uids]
            sel_positions.sort(reverse=True)
            for pos in sel_positions:
                if pos >= 0:
                    self._plan_queue_items.pop(pos)

            # Update the queue
            self.load_plan_queue()

    def queue_clear(self):
        """Clear the plan queue."""
        self._plan_queue_items.clear()
        self.selected_queue_item_uids = []
        self.load_plan_queue()

    def queue_item_copy_to_queue(self):
        """Copy currently selected item to queue."""
        sel_item_uids = self._selected_queue_item_uids
        sel_items = []
        for uid in sel_item_uids:
            pos = self.queue_item_uid_to_pos(uid)
            if uid and (pos >= 0):
                sel_items.append(copy.deepcopy(self._plan_queue_items[pos]))

        if sel_items:
            self.queue_item_add_batch(items=sel_items)

    def _create_queue_item(self, item):
        if hasattr(item, "to_dict") and callable(item.to_dict):
            item = item.to_dict()
        new_item = copy.deepcopy(item)
        new_item["item_uid"] = str(uuid.uuid4())

        # Add user information
        new_item["user"] = "GUI Client"
        new_item["user_group"] = "primary"
        return new_item

    def queue_item_add(self, *, item, params=None):
        """
        Add item to queue. The new item is inserted after the selected item or to the back of the queue
        in case no item is selected.

        Parameters
        ----------
        item : dict or BPlan
            Item to add to the queue
        params : dict, optional
            Optional parameters to override default behavior
        """
        # Convert BPlan or similar objects to dict

        if self._selected_queue_item_uids:
            # Insert after the last item in the selected batch
            sel_item_uid = self._selected_queue_item_uids[-1]
        else:
            # No selection: push to the back of the queue
            sel_item_uid = None

        queue_is_empty = not len(self._plan_queue_items)
        if not params:
            if queue_is_empty or not sel_item_uid:
                # Push to the back of the queue
                params = {}
            else:
                params = {"after_uid": sel_item_uid}

        # Create a copy of the item and assign a new UID
        new_item = self._create_queue_item(item)
        # Insert the item
        if "after_uid" in params:
            after_uid = params["after_uid"]
            after_pos = self.queue_item_uid_to_pos(after_uid)
            if after_pos >= 0:
                self._plan_queue_items.insert(after_pos + 1, new_item)
            else:
                self._plan_queue_items.append(new_item)
        else:
            self._plan_queue_items.append(new_item)

        # Update the queue
        self.load_plan_queue()

        # Set the new item as selected
        self.selected_queue_item_uids = [new_item["item_uid"]]

    def queue_item_update(self, *, item):
        """
        Update the existing plan in the queue.

        Parameters
        ----------
        item : dict
            Updated item with matching UID
        """
        item_uid = item.get("item_uid")
        if not item_uid:
            return

        pos = self.queue_item_uid_to_pos(item_uid)
        if pos >= 0:
            # Update the item
            self._plan_queue_items[pos] = copy.deepcopy(item)
            self.load_plan_queue()
            self.selected_queue_item_uids = [item_uid]

    def queue_item_add_batch(self, *, items, params=None):
        """
        Add a batch of items to queue.

        Parameters
        ----------
        items : list
            List of items to add
        params : dict, optional
            Optional parameters to override default behavior
        """
        if not items:
            return

        sel_item_uids = self.selected_queue_item_uids.copy()

        if sel_item_uids:
            # Insert after the last item in the selected batch
            sel_item_uid = sel_item_uids[-1]
        else:
            # No selection: push to the back of the queue
            sel_item_uid = None

        queue_is_empty = not len(self._plan_queue_items)
        if not params:
            if queue_is_empty or not sel_item_uid:
                # Push to the back of the queue
                params = {}
            else:
                params = {"after_uid": sel_item_uid}

        # Create copies of items and assign new UIDs
        new_items = []
        for item in items:
            new_item = self._create_queue_item(item)
            new_items.append(new_item)

        # Insert the items
        if "after_uid" in params:
            after_uid = params["after_uid"]
            after_pos = self.queue_item_uid_to_pos(after_uid)
            if after_pos >= 0:
                for i, item in enumerate(new_items):
                    self._plan_queue_items.insert(after_pos + 1 + i, item)
            else:
                self._plan_queue_items.extend(new_items)
        else:
            self._plan_queue_items.extend(new_items)

        # Update the queue
        self.load_plan_queue()

        # Set the new items as selected
        new_sel_uids = [item["item_uid"] for item in new_items]
        self.selected_queue_item_uids = new_sel_uids

    # ============================================================================
    #                         Staging-specific methods

    def add_plan(self, plan):
        """
        Add a plan to the staging area.

        Parameters
        ----------
        plan : dict
            Plan to add to staging
        """
        self.queue_item_add(item=plan)

    def remove_plans(self, indices):
        """
        Remove plans at the specified indices.

        Parameters
        ----------
        indices : list
            List of indices to remove
        """
        # Convert indices to UIDs
        uids_to_remove = []
        for idx in indices:
            if 0 <= idx < len(self._plan_queue_items):
                uid = self._plan_queue_items[idx].get("item_uid")
                if uid:
                    uids_to_remove.append(uid)

        # Set selection and remove
        if uids_to_remove:
            self.selected_queue_item_uids = uids_to_remove
            self.queue_items_remove()

    def duplicate_plan(self, index):
        """
        Duplicate the plan at the specified index.

        Parameters
        ----------
        index : int
            Index of plan to duplicate
        """
        if 0 <= index < len(self._plan_queue_items):
            plan = copy.deepcopy(self._plan_queue_items[index])
            # Remove the UID so a new one will be assigned
            plan.pop("item_uid", None)
            self.queue_item_add(item=plan)

    def clear_all(self):
        """Clear all staged plans."""
        self.queue_clear()

    def set_selection(self, indices):
        """
        Set the selection to the specified indices.

        Parameters
        ----------
        indices : list
            List of indices to select
        """
        uids_to_select = []
        for idx in indices:
            if 0 <= idx < len(self._plan_queue_items):
                uid = self._plan_queue_items[idx].get("item_uid")
                if uid:
                    uids_to_select.append(uid)

        self.selected_queue_item_uids = uids_to_select

    def clear_selection(self):
        """Clear the current selection."""
        self.selected_queue_item_uids = []

    @property
    def staged_plans(self):
        """Get the list of staged plans."""
        return self._plan_queue_items

    @property
    def selected_plan_indices(self):
        """Get the indices of selected plans."""
        indices = []
        for uid in self._selected_queue_item_uids:
            pos = self.queue_item_uid_to_pos(uid)
            if pos >= 0:
                indices.append(pos)
        return sorted(indices)

    @property
    def selected_plans(self):
        """Get the selected plans."""
        return [self._plan_queue_items[i] for i in self.selected_plan_indices]

    def get_plan_display_name(self, plan):
        """Get the display name for a plan."""
        return plan.get("name", "Unknown Plan")

    def get_plan_parameters_summary(self, plan):
        """Get a summary of plan parameters."""
        try:
            return self.get_item_value_for_label(item=plan, label="Parameters")
        except KeyError:
            return "No parameters"
