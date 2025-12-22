from importlib.metadata import entry_points


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

            for entry_point in entry_points(group="nbs_bl.time_estimators"):
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


class TimeEstimator:
    def __init__(self, model):
        self.model = model
        self.plan_time_dict = {}
        self.time_estimators = load_time_estimators()
        self._subscribe_to_time_estimation()

    def _subscribe_to_time_estimation(self):
        """Subscribe to the plan time estimation dictionary"""
        try:
            # Get the Redis dictionary for plan time estimation
            self.plan_time_dict = self.model.user_status.get_redis_dict(
                "PLAN_TIME_DICT"
            )
            if self.plan_time_dict:
                print("[QtRePlanQueue] Subscribed to plan time estimation dictionary")
            else:
                print(
                    "[QtRePlanQueue] Could not subscribe to plan time estimation dictionary"
                )
        except Exception as e:
            print(f"[QtRePlanQueue] Error subscribing to time estimation: {e}")

    def _calculate_time_estimate(self, plan_name, plan_args):
        """Calculate time estimate for a plan"""
        try:
            if not hasattr(self, "plan_time_dict") or self.plan_time_dict is None:
                return None

            # Get the estimation parameters for this plan
            estimation_params = self.plan_time_dict.get(plan_name)
            if not estimation_params:
                return None

            # Get the estimator function name
            estimator_name = estimation_params.get("estimator", "generic_estimate")
            if estimator_name not in self.time_estimators:
                return None

            # Calculate the estimate
            estimator_func = self.time_estimators[estimator_name]
            estimate = estimator_func(plan_name, plan_args, estimation_params)

            return estimate
        except Exception as e:
            print(f"[QtRePlanQueue] Error calculating time estimate: {e}")
            return None

    def format_time_estimate(self, estimate):
        """Format time estimate for display"""
        if estimate is None:
            return "--"

        if estimate < 60:
            return f"{estimate:.1f}s"
        elif estimate < 3600:
            return f"{estimate/60:.1f}m"
        else:
            return f"{estimate/3600:.1f}h"

    def calculate_plan_time(self, plan_item):
        if hasattr(plan_item, "to_dict"):
            plan_item = plan_item.to_dict()
        plan_name = plan_item.get("name")
        plan_args = {}
        plan_args.update(plan_item.get("kwargs", {}))
        if "args" in plan_item:
            plan_args["args"] = plan_item["args"]

        estimate = self._calculate_time_estimate(plan_name, plan_args)
        return estimate

    def calculate_queue_time(self, plan_queue_items):
        total_estimate = 0
        valid_estimates = 0
        for item in plan_queue_items:
            estimate = self.calculate_plan_time(item)
            if estimate is not None:
                total_estimate += estimate
                valid_estimates += 1
        if valid_estimates > 0:
            return total_estimate
        else:
            return None
