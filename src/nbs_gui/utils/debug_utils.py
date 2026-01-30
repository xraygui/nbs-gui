"""
Utilities for collecting debugging information from a running nbs-gui process.

The functions in this module are intended to be called from GUI actions (e.g.
button clicks) and return formatted text for display.
"""

from __future__ import annotations

from datetime import datetime
import gc
import os
from typing import Iterable
from collections import Counter

from qtpy.QtCore import QCoreApplication, QTimer
from qtpy.QtWidgets import QApplication, QWidget


def _timestamp() -> str:
    """
    Generate a human-readable timestamp.

    Returns
    -------
    str
        Current local timestamp formatted as ``YYYY-mm-dd HH:MM:SS``.
    """

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def dump_timer_stats() -> str:
    """
    Dump statistics about Qt timers in the current application.

    Returns
    -------
    str
        Multi-line text summary of QTimer instances. Includes both:

        - Timers discoverable from the Qt object tree (children of the app)
        - Timers visible to Python GC (which may include un-parented timers)
    """

    app = QCoreApplication.instance()
    if app is None:
        return "QTimer Statistics:\n  No QApplication instance"

    timers_qt = app.findChildren(QTimer)
    active_qt = sum(1 for t in timers_qt if t.isActive())
    single_shot_qt = sum(1 for t in timers_qt if t.isSingleShot())
    repeating_qt = len(timers_qt) - single_shot_qt

    timers_gc = [
        obj for obj in gc.get_objects() if isinstance(obj, QTimer)
    ]
    active_gc = 0
    single_shot_gc = 0
    for t in timers_gc:
        try:
            if t.isActive():
                active_gc += 1
            if t.isSingleShot():
                single_shot_gc += 1
        except Exception:
            continue
    repeating_gc = len(timers_gc) - single_shot_gc

    return (
        "QTimer Statistics:\n"
        f"  Qt object-tree timers: {len(timers_qt)}\n"
        f"    Active: {active_qt}\n"
        f"    Single-shot: {single_shot_qt}\n"
        f"    Repeating: {repeating_qt}\n"
        f"  Python GC timers: {len(timers_gc)}\n"
        f"    Active: {active_gc}\n"
        f"    Single-shot: {single_shot_gc}\n"
        f"    Repeating: {repeating_gc}"
    )


def dump_widget_stats() -> str:
    """
    Dump statistics about live widgets in the current application.

    Returns
    -------
    str
        Multi-line text summary of QWidget instances using both Qt and Python
        perspectives.
    """

    app = QCoreApplication.instance()
    if app is None:
        return "Widget Statistics:\n  No QApplication instance"

    qapp = QApplication.instance()
    widgets_all = []
    if qapp is not None:
        try:
            widgets_all = list(qapp.allWidgets())
        except Exception:
            widgets_all = []

    widgets_qt_tree = app.findChildren(QWidget)
    widgets_gc = [
        obj for obj in gc.get_objects() if isinstance(obj, QWidget)
    ]

    return (
        "Widget Statistics:\n"
        f"  QApplication.allWidgets(): {len(widgets_all)}\n"
        f"  Qt object-tree widgets: {len(widgets_qt_tree)}\n"
        f"  Python GC widgets: {len(widgets_gc)}"
    )


def _top_type_counts(type_counts: dict[str, int], limit: int) -> list[tuple[str, int]]:
    """
    Return the highest-count types in a type-count mapping.

    Parameters
    ----------
    type_counts : dict[str, int]
        Mapping from type name to object count.
    limit : int
        Maximum number of items to return.

    Returns
    -------
    list[tuple[str, int]]
        Sorted list of type counts.
    """

    return sorted(type_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]


def _iter_interesting_objects(objs: Iterable[object]) -> dict[str, int]:
    """
    Count potentially interesting Python objects by type name.

    Parameters
    ----------
    objs : Iterable[object]
        Iterable of Python objects, typically from ``gc.get_objects()``.

    Returns
    -------
    dict[str, int]
        Mapping of type name to count for types that match common Qt/GUI patterns.
    """

    type_counts: dict[str, int] = {}
    for obj in objs:
        name = type(obj).__name__
        if (
            name.startswith("Q")
            or "Signal" in name
            or "Timer" in name
            or "Worker" in name
            or name.endswith("Model")
        ):
            type_counts[name] = type_counts.get(name, 0) + 1
    return type_counts


def dump_object_counts(limit: int = 25) -> str:
    """
    Dump Python object counts, focusing on Qt/GUI-related types.

    Parameters
    ----------
    limit : int, optional
        Maximum number of types to display. Default is 25.

    Returns
    -------
    str
        Multi-line text summary of counts derived from ``gc.get_objects()``.
    """

    gc.collect()
    type_counts = _iter_interesting_objects(gc.get_objects())
    top = _top_type_counts(type_counts, limit=limit)

    lines = [f"Python Object Counts (filtered, top {len(top)}):"]
    for type_name, count in top:
        lines.append(f"  {type_name}: {count}")
    return "\n".join(lines)


def dump_memory_stats() -> str:
    """
    Dump basic process memory statistics.

    Returns
    -------
    str
        Multi-line text summary of memory usage. Uses ``resource`` on Unix-like
        systems. If unavailable, returns a message explaining why.
    """

    try:
        import resource
    except Exception as exc:
        return f"Memory Statistics:\n  Unavailable ({exc})"

    usage = resource.getrusage(resource.RUSAGE_SELF)
    max_rss_mb = usage.ru_maxrss / 1024.0

    return "Memory Statistics:\n" f"  Max RSS: {max_rss_mb:.1f} MB"


def dump_process_info() -> str:
    """
    Dump basic process info.

    Returns
    -------
    str
        Multi-line text summary containing PID and Python version string.
    """

    import sys

    return (
        "Process Info:\n"
        f"  PID: {os.getpid()}\n"
        f"  Python: {sys.version.splitlines()[0]}"
    )


def dump_full_snapshot() -> str:
    """
    Generate a full diagnostic snapshot.

    Returns
    -------
    str
        A formatted, timestamped snapshot containing timer, widget, object and
        memory information.
    """

    parts = [
        f"=== Debug Snapshot: {_timestamp()} ===",
        dump_process_info(),
        dump_timer_stats(),
        dump_widget_stats(),
        dump_object_counts(),
        dump_memory_stats(),
        "=" * 40,
    ]
    return "\n\n".join(parts)


def _safe_repr(obj: object, max_len: int = 160) -> str:
    """
    Return a truncated repr for diagnostics.

    Parameters
    ----------
    obj : object
        Object to represent.
    max_len : int, optional
        Maximum length of returned representation. Default is 160.

    Returns
    -------
    str
        Truncated repr.
    """

    try:
        s = repr(obj)
    except Exception as exc:
        s = f"<repr failed: {exc}>"
    if len(s) > max_len:
        return s[: max_len - 3] + "..."
    return s


def _find_objects_by_type_name(type_name: str, limit: int = 5) -> list[object]:
    """
    Find a sample of live Python objects by their type name.

    Parameters
    ----------
    type_name : str
        Exact type name to match (e.g. ``GeneratorWorker``).
    limit : int, optional
        Maximum number of objects to return. Default is 5.

    Returns
    -------
    list[object]
        Sample objects.
    """

    gc.collect()
    found: list[object] = []
    for obj in gc.get_objects():
        if type(obj).__name__ == type_name:
            found.append(obj)
            if len(found) >= limit:
                break
    return found


def _find_all_objects_by_type_name(type_name: str) -> list[object]:
    """
    Find ALL live Python objects by their type name.

    Parameters
    ----------
    type_name : str
        Exact type name to match (e.g. ``GeneratorWorker``).

    Returns
    -------
    list[object]
        All matching objects, sorted by id (newest/highest first).
    """

    gc.collect()
    found: list[object] = []
    for obj in gc.get_objects():
        if type(obj).__name__ == type_name:
            found.append(obj)
    found.sort(key=id, reverse=True)
    return found


_previous_object_ids: dict[str, set[int]] = {}


def _find_closure_owner(cell) -> tuple[str, str] | None:
    """
    Find the function that owns a closure cell.

    Parameters
    ----------
    cell : cell
        A closure cell object.

    Returns
    -------
    tuple[str, str] | None
        A tuple of (function qualname, code filename:lineno) if found, else None.
    """

    import types

    for obj in gc.get_objects():
        if isinstance(obj, types.FunctionType):
            closure = obj.__closure__
            if closure is not None:
                try:
                    if any(c is cell for c in closure):
                        code = obj.__code__
                        location = f"{code.co_filename}:{code.co_firstlineno}"
                        return (obj.__qualname__, location)
                except Exception:
                    continue
    return None


def _trace_referrer_chain(
    obj: object,
    max_depth: int = 10,
    ignore_ids: set[int] | None = None,
) -> list[str]:
    """
    Trace the referrer chain from an object back to a meaningful anchor.

    Parameters
    ----------
    obj : object
        The object to trace referrers for.
    max_depth : int, optional
        Maximum depth to trace. Default is 10.
    ignore_ids : set[int] | None, optional
        Set of object ids to ignore in the chain.

    Returns
    -------
    list[str]
        List of strings describing the referrer chain.
    """

    import types

    if ignore_ids is None:
        ignore_ids = set()

    chain: list[str] = []
    current = obj
    visited: set[int] = set()

    for _ in range(max_depth):
        if id(current) in visited:
            chain.append("(cycle detected)")
            break
        visited.add(id(current))

        try:
            referrers = gc.get_referrers(current)
        except Exception:
            break

        meaningful_ref = None
        for ref in referrers:
            ref_id = id(ref)
            if ref_id in ignore_ids or ref_id in visited:
                continue
            if ref is chain or isinstance(ref, list) and any(r is current for r in ref[:10]):
                continue

            ref_type = type(ref).__name__

            if ref_type == "cell":
                owner = _find_closure_owner(ref)
                if owner:
                    qualname, location = owner
                    chain.append(f"closure in {qualname} ({location})")
                    return chain
                else:
                    chain.append("cell (unknown owner)")
                    meaningful_ref = ref
                    break

            if isinstance(ref, types.FrameType):
                continue

            if isinstance(ref, types.FunctionType):
                code = ref.__code__
                location = f"{code.co_filename}:{code.co_firstlineno}"
                chain.append(f"function {ref.__qualname__} ({location})")
                return chain

            if isinstance(ref, types.MethodType):
                func = ref.__func__
                code = func.__code__
                location = f"{code.co_filename}:{code.co_firstlineno}"
                self_type = type(ref.__self__).__name__
                chain.append(f"bound method {func.__qualname__} on {self_type} ({location})")
                return chain

            if hasattr(ref, "__class__") and not isinstance(
                ref, (dict, list, tuple, set, frozenset, str, bytes)
            ):
                cls_name = type(ref).__name__
                if cls_name not in ("cell", "frame", "code", "function", "method"):
                    module = getattr(type(ref), "__module__", "")
                    chain.append(f"instance of {module}.{cls_name}")
                    return chain

            if ref_type == "dict":
                for key, val in list(ref.items())[:100]:
                    if val is current and isinstance(key, str):
                        chain.append(f"dict['{key}']")
                        meaningful_ref = ref
                        break
                if meaningful_ref:
                    break

            if ref_type in ("list", "tuple"):
                chain.append(ref_type)
                meaningful_ref = ref
                break

        if meaningful_ref is None:
            break
        current = meaningful_ref

    if not chain:
        chain.append("(no clear referrer chain)")

    return chain


def dump_referrers_summary(type_name: str, sample: int = 3, ref_limit: int = 50) -> str:
    """
    Summarize what is retaining objects of a given type.

    This uses ``gc.get_referrers`` on a sample of the newest objects (by id)
    and traces referrer chains to find meaningful anchors like closures or
    class instances.

    Parameters
    ----------
    type_name : str
        Exact type name to inspect (e.g. ``GeneratorWorker`` or ``FunctionWorker``).
    sample : int, optional
        Number of objects of that type to sample. Default is 3.
    ref_limit : int, optional
        Maximum number of referrers inspected per sampled object. Default is 50.

    Returns
    -------
    str
        Multi-line summary.
    """

    global _previous_object_ids

    all_objs = _find_all_objects_by_type_name(type_name)
    total_count = len(all_objs)

    if total_count == 0:
        return f"Referrers Summary:\n  No objects found for type {type_name}"

    current_ids = {id(o) for o in all_objs}
    previous_ids = _previous_object_ids.get(type_name, set())

    new_ids = current_ids - previous_ids
    removed_count = len(previous_ids - current_ids)

    _previous_object_ids[type_name] = current_ids

    lines = [f"Referrers Summary for {type_name}:"]
    lines.append(f"  Total objects: {total_count}")
    if previous_ids:
        delta = total_count - len(previous_ids)
        delta_str = f"+{delta}" if delta >= 0 else str(delta)
        lines.append(
            f"  Change since last check: {delta_str} "
            f"(+{len(new_ids)} new, -{removed_count} removed)"
        )
    else:
        lines.append("  (first check, no previous baseline)")

    objs_to_sample = all_objs[:sample]
    lines.append(f"  Sampling {len(objs_to_sample)} newest objects (by id):")

    ignore_ids = {
        id(all_objs),
        id(objs_to_sample),
        id(lines),
        id(current_ids),
        id(new_ids),
    }

    for idx, obj in enumerate(objs_to_sample, start=1):
        obj_id = id(obj)
        is_new = obj_id in new_ids
        new_marker = " [NEW]" if is_new else ""
        lines.append(f"")
        lines.append(f"  [{idx}] {hex(obj_id)}{new_marker}")

        ignore_ids.add(obj_id)
        chain = _trace_referrer_chain(obj, max_depth=10, ignore_ids=ignore_ids)
        if chain:
            lines.append(f"      Retained by: {' -> '.join(chain)}")

        try:
            referrers = list(gc.get_referrers(obj))
        except Exception as exc:
            lines.append(f"      get_referrers failed: {exc}")
            continue

        filtered = [r for r in referrers if id(r) not in ignore_ids][:ref_limit]
        type_counts = Counter(type(r).__name__ for r in filtered)
        top_types = sorted(type_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:5]

        if top_types:
            type_summary = ", ".join(f"{t}:{c}" for t, c in top_types)
            lines.append(f"      Referrer types: {type_summary}")

        for r in filtered:
            if type(r).__name__ == "cell":
                owner = _find_closure_owner(r)
                if owner:
                    qualname, location = owner
                    lines.append(f"      Closure owner: {qualname}")
                    lines.append(f"        Location: {location}")
                break

    return "\n".join(lines)


def dump_referrers_aggregate(type_name: str, max_objects: int = 100) -> str:
    """
    Aggregate referrer patterns across all objects of a given type.

    This scans all objects and groups them by their retention site (typically
    the closure or class instance holding them).

    Parameters
    ----------
    type_name : str
        Exact type name to inspect (e.g. ``GeneratorWorker`` or ``FunctionWorker``).
    max_objects : int, optional
        Maximum number of objects to analyze. Default is 100.

    Returns
    -------
    str
        Multi-line summary showing aggregated retention patterns.
    """

    all_objs = _find_all_objects_by_type_name(type_name)
    total_count = len(all_objs)

    if total_count == 0:
        return f"Aggregate Referrers for {type_name}:\n  No objects found"

    objs_to_analyze = all_objs[:max_objects]
    retention_sites: dict[str, list[int]] = {}

    ignore_ids = {id(all_objs), id(objs_to_analyze), id(retention_sites)}

    for obj in objs_to_analyze:
        obj_id = id(obj)
        ignore_ids.add(obj_id)
        chain = _trace_referrer_chain(obj, max_depth=10, ignore_ids=ignore_ids)
        site_key = " -> ".join(chain) if chain else "(unknown)"
        if site_key not in retention_sites:
            retention_sites[site_key] = []
        retention_sites[site_key].append(obj_id)

    sorted_sites = sorted(retention_sites.items(), key=lambda kv: -len(kv[1]))

    lines = [f"Aggregate Referrers for {type_name}:"]
    lines.append(f"  Total objects: {total_count}")
    lines.append(f"  Analyzed: {len(objs_to_analyze)}")
    lines.append(f"  Unique retention sites: {len(retention_sites)}")
    lines.append("")
    lines.append("  Retention sites (by count):")

    for site, obj_ids in sorted_sites[:15]:
        lines.append(f"    {len(obj_ids):4d} objects: {site}")

    if len(sorted_sites) > 15:
        remaining = sum(len(ids) for _, ids in sorted_sites[15:])
        lines.append(f"    ... and {len(sorted_sites) - 15} more sites ({remaining} objects)")

    return "\n".join(lines)

