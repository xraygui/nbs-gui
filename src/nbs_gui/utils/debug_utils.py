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

from qtpy.QtCore import QCoreApplication, QTimer
from qtpy.QtWidgets import QWidget


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
        Multi-line text summary of QTimer instances discovered via
        ``QCoreApplication.instance().findChildren(QTimer)``.
    """

    app = QCoreApplication.instance()
    if app is None:
        return "QTimer Statistics:\n  No QApplication instance"

    timers = app.findChildren(QTimer)
    active = sum(1 for t in timers if t.isActive())
    single_shot = sum(1 for t in timers if t.isSingleShot())
    repeating = len(timers) - single_shot

    return (
        "QTimer Statistics:\n"
        f"  Total QTimer instances: {len(timers)}\n"
        f"  Active timers: {active}\n"
        f"  Single-shot timers: {single_shot}\n"
        f"  Repeating timers: {repeating}"
    )


def dump_widget_stats() -> str:
    """
    Dump statistics about live widgets in the current application.

    Returns
    -------
    str
        Multi-line text summary of QWidget instances discovered via
        ``QCoreApplication.instance().findChildren(QWidget)``.
    """

    app = QCoreApplication.instance()
    if app is None:
        return "Widget Statistics:\n  No QApplication instance"

    widgets = app.findChildren(QWidget)
    return "Widget Statistics:\n" f"  Total QWidget instances: {len(widgets)}"


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

