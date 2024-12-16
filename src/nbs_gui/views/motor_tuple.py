from .switchable_motors import SwitchableMotorMonitor, SwitchableMotorControl


class MotorTupleMonitor(SwitchableMotorMonitor):
    """
    Monitor widget for a tuple of motors.
    Shows real motors with option to hide them.

    Parameters
    ----------
    model : MotorTupleModel
        The model representing the motor tuple
    parent_model : object
        Parent model for the widget
    """

    def __init__(self, model, parent_model, *args, **kwargs):
        super().__init__(
            title=model.label,
            model=model,
            parent_model=parent_model,
            pseudo_title="Motors",  # Main view title
            real_title="All Motors",  # Detailed view title
            *args,
            **kwargs,
        )


class MotorTupleControl(SwitchableMotorControl):
    """
    Control widget for a tuple of motors.
    Shows real motors with option to hide them.

    Parameters
    ----------
    model : MotorTupleModel
        The model representing the motor tuple
    parent_model : object
        Parent model for the widget
    """

    def __init__(self, model, parent_model, *args, **kwargs):
        super().__init__(
            title=model.label,
            model=model,
            parent_model=parent_model,
            pseudo_title="Motors",  # Main view title
            real_title="All Motors",  # Detailed view title
            *args,
            **kwargs,
        )
