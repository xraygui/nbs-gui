import pkg_resources


def load_time_estimators():
    """Load time estimation functions from nbs_bl.plans.time_estimation"""
    try:
        from nbs_bl.plans.time_estimation import (
            generic_estimate,
            list_scan_estimate,
            grid_scan_estimate,
            list_grid_scan_estimate,
            fly_scan_estimate,
            gscan_estimate,
        )

        time_estimators = {
            "generic_estimate": generic_estimate,
            "list_scan_estimate": list_scan_estimate,
            "grid_scan_estimate": grid_scan_estimate,
            "list_grid_scan_estimate": list_grid_scan_estimate,
            "fly_scan_estimate": fly_scan_estimate,
            "gscan_estimate": gscan_estimate,
        }
        # Load additional estimators from entry points
        try:

            for entry_point in pkg_resources.iter_entry_points(
                "nbs_bl.time_estimators"
            ):
                estimator = entry_point.load()
                if callable(estimator):
                    time_estimators[entry_point.name] = estimator
                    print(
                        f"[load_time_estimators] Loaded time estimator {entry_point.name}"
                    )
        except Exception as e:
            print(
                f"[load_time_estimators] Error loading time estimators from entry points: {e}"
            )
        print("[load_time_estimators] Loaded time estimators")
    except ImportError as e:
        print(f"[load_time_estimators] Failed to load time estimators: {e}")
        time_estimators = {}
    return time_estimators
