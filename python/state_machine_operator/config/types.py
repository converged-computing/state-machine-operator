import re

import state_machine_operator.defaults as defaults


class Rule:
    """
    A rule wraps an action with additional metadata
    """

    def __init__(self, rule):
        self._rule = rule
        self.disabled = False
        self.action = Action(rule)
        self.validate()

    def should_trigger(self, value):
        """
        Check if "when" is relevant to be run now, return True/False
        to say to run or not.
        """
        # This ensures we check backoff, etc.
        if not self.action.should_trigger():
            return False

        # No when is set, so we just continue assuming there is no when
        if self.when is None:
            return self.action.perform()

        # If the value is None, and the trigger is undefined
        if value is None and self.when == "undefined":
            return self.action.perform()

        # The value is None, and we can't act on it
        if value is None:
            return False

        # If we have a direct value, we check for equality
        number = (int, float)
        if isinstance(self.when, number) and value != self.when:
            return False
        if isinstance(self.when, number) and value == self.when:
            return self.action.perform()

        # Otherwise, parse for inequality
        match = re.search(
            r"(?P<inequality>[<>]=?)\s*(?P<comparator>-?\d+(\.\d*)?)", self.when
        ).groupdict()

        # This could technically be a float value
        comparator = float(match["comparator"])
        inequality = match["inequality"]
        assert inequality in {"<", ">", "<=", ">=", "==", "="}

        # Evaluate! Not sure there is a better way than this :)
        should_trigger = False
        if inequality == "<":
            should_trigger = value < comparator
        elif inequality == "<=":
            should_trigger = value <= comparator
        elif inequality == ">":
            should_trigger = value > comparator
        elif inequality == ">=":
            should_trigger = value >= comparator
        elif inequality in ["==", "="]:
            should_trigger = value == comparator
        else:
            raise ValueError(f"Invalid comparator {comparator} for rule when")

        # Perform the action if trigger is warranted, alert caller
        if should_trigger:
            self.action.perform()
            return True
        return False

    def check_when(self):
        """
        Ensure we have a valid inequality before running anything!
        """
        # If a number, we require greater than == 0
        if isinstance(self.when, int) and self.when >= 0:
            return

        # Check running the function with a value, should not raise error
        try:
            self.should_trigger(10)
        except Exception as err:
            raise ValueError(f"when: for rule {self} is not valid: {err}")

    @property
    def when(self):
        return self._rule.get("when")

    def validate(self):
        """
        Validate the rule and associated action
        """
        # Is the action name valid?
        # all actions is the combination of workflow and state machine actions
        if self.action.name not in defaults.all_actions:
            raise ValueError(f"Event has invalid action name {self.action.name}")

        # Ensure we have a valid number or inequality
        self.check_when()


class Action:
    """
    An action holds a metric name, when, and an action.
    """

    def __init__(self, action):
        self._action = action

        # We parse this because the value will change
        # and we don't want to destroy the original setting
        self.parse_frequency()

    def parse_frequency(self):
        """
        Parse the action frequency, which by default, is to run it indefinitely.
        it once. An additional backoff period (number of periods to skip)
        can also be provided.
        """
        self.repetitions = self._action.get("repetitions")

        # Backoff between repetitions (this is global setting)
        # Setting to None indicates backoff is not active
        self.backoff = self._action.get("backoff")

        # Counter between repetitions
        self.backoff_counter = 0

    def should_trigger(self):
        """
        Return True or False to indicate performing an action.
        """
        # If we are out of repetitions, no matter what, we don't run
        if self.finished:
            return False

        # The action is flagged to have some total backoff periods between repetitions
        if self.backoff is not None and self.backoff >= 0:
            return False

        # We don't have any repetitions left
        if self.repetitions is not None and self.repetitions <= 0:
            return False
        return True

    def perform(self):
        """
        Return True or False to indicate performing an action.
        """
        # The action is flagged to have some total backoff periods between repetitions
        if self.backoff is not None and self.backoff >= 0:
            self.perform_backoff()

        # If we get here, backoff is not set (None) and repetitions > 0
        if self.repetitions is not None:
            self.repetitions -= 1

    def perform_backoff(self):
        """
        Perform backoff (going through the logic of checking the
        period we are on, and deciding to run or not, and decrementing
        counters) to return a boolean if we should run the action or not.
        """
        # But we are still going through a period
        if self.backoff_counter > 0:
            self.backoff_counter -= 1

        # The backoff counter has expired - it is zero here
        # reset the counter to the original value
        if self.backoff_counter == 0:
            self.backoff_counter = self.backoff

        # Decrement repetitions
        if self.repetitions is not None:
            self.repetitions -= 1

    @property
    def name(self):
        return self._action["action"]

    @property
    def min_completions(self):
        return self._action.get("minCompletions")

    @property
    def max_size(self):
        return self._action.get("maxSize")

    @property
    def min_size(self):
        return self._action.get("minSize")

    @property
    def metric(self):
        return self._action["metric"]

    @property
    def finished(self):
        """
        An action is finished when it has no more repetitions
        It should never go below zero, in practice.
        """
        return self.repetitions is not None and self.repetitions <= 0
