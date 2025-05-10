"""Regex finite state machine implementation"""

from __future__ import annotations
from abc import ABC, abstractmethod


class State(ABC):
    """Abstract base class for all states in the finite state machine.
    States represent different parts of a regex pattern and define how to match characters."""
    @abstractmethod
    def __init__(self) -> None:
        pass

    @abstractmethod
    def check_self(self, char: str) -> bool:
        """Checks if this state can accept the given character.
        
        Args:
            char: The character to check
            
        Returns:
            True if this state accepts the character, False otherwise
        """
        pass

    def check_next(self, next_char: str) -> State | Exception:
        """Finds the next state that can handle the given character.
        
        Args:
            next_char: The character to match
            
        Returns:
            The next state if found
            
        Raises:
            NotImplementedError: If no next state can handle the character
        """
        for state in self.next_states:
            if state.check_self(next_char):
                return state
        raise NotImplementedError("rejected string")


class StartState(State):
    """Initial state of the FSM that doesn't match any character itself."""
    def __init__(self):
        self.next_states = []

    def check_self(self, char):
        return False


class TerminationState(State):
    """Final state of the FSM indicating successful pattern match."""
    def __init__(self) -> None:
        self.next_states = []

    def check_self(self, char: str) -> bool:
        return False


class DotState(State):
    """State for the dot operator (.) that matches any single character."""
    def __init__(self):
        self.next_states = []

    def check_self(self, char: str):
        return True


class AsciiState(State):
    """State that matches a specific character like 'a' or '1'."""
    def __init__(self, symbol: str) -> None:
        self.next_states = []
        self.curr_sym = symbol

    def check_self(self, curr_char: str) -> bool:
        return self.curr_sym == curr_char


class CharacterClassState(State):
    """State for character classes like [a-z0-9] that match any character in the specified set."""
    def __init__(self, class_spec: str):
        """Initialize with a character class specification.
        
        Args:
            class_spec: String like 'a-z0-9' or '^0-9' (negated)
        """
        self.next_states = []
        self.char_ranges = []
        self.individual_chars = set()
        self.negated = False

        #мб видалю
        if class_spec and class_spec[0] == '^':
            self.negated = True
            class_spec = class_spec[1:]

        i = 0
        while i < len(class_spec):
            if i + 2 < len(class_spec) and class_spec[i+1] == '-':
                self.char_ranges.append((class_spec[i], class_spec[i+2]))
                i += 3
            else:
                self.individual_chars.add(class_spec[i])
                i += 1

    def check_self(self, char: str) -> bool:
        """
        Check if the character matches this class
        
        For negated classes (^), returns True if the character
        is NOT in the class.
        """
        in_class = any(ord(start) <= ord(char) <= ord(end) for\
                       start, end in self.char_ranges)
        if not in_class:
            in_class = char in self.individual_chars

        return not in_class if self.negated else in_class


class StarState(State):
    """
    State for * operator that allows zero or more repetitions
    of the previous state
    """
    def __init__(self, checking_state: State):
        """
        Initialize with the state that should be repeated.
        
        Args:
            checking_state: The state to repeat (zero or more times)
        """
        self.next_states = []
        self.checking_state = checking_state

    def check_self(self, char):
        return self.checking_state.check_self(char)


class PlusState(State):
    """
    State for + operator that allows one or more repetitions of the previous state
    """
    def __init__(self, checking_state: State):
        """
        Initialize with the state that should be repeated.
        
        Args:
            checking_state: The state to repeat (one or more times)
        """
        self.next_states = []
        self.checking_state = checking_state

    def check_self(self, char):
        return self.checking_state.check_self(char)


class RegexFSM:
    """
    Finite State Machine that compiles and matches regular expressions
    """
    def __init__(self, regex_expr: str) -> None:
        """
        Compile a regular expression into a finite state machine
        
        Args:
            regex_expr: The regular expression to compile
            
        Raises:
            ValueError: If the regex is invalid
        """
        self.start_state = StartState()

        if not regex_expr:
            raise ValueError("Empty regex pattern")

        if regex_expr == '*' or regex_expr[0] == '*':
            raise ValueError("'*' cannot be used without a preceding character")

        if regex_expr == '+' or regex_expr[0] == '+':
            raise ValueError("'+' cannot be used without a preceding character")

        i = 0
        states = []

        while i < len(regex_expr):
            char = regex_expr[i]

            if char == '*' and states:
                prev_state = states[-1]
                star_state = StarState(prev_state)
                parent = states[-2] if len(states) >= 2 else self.start_state
                parent.next_states = [s for s in parent.next_states if s != prev_state]
                parent.next_states.append(star_state)

                star_state.next_states.append(star_state)
                states[-1] = star_state

            elif char == '+' and states:
                prev_state = states[-1]
                plus_state = PlusState(prev_state)
                parent = states[-2] if len(states) >= 2 else self.start_state
                parent.next_states = [s for s in parent.next_states if s != prev_state]
                parent.next_states.append(plus_state)

                plus_state.next_states.append(plus_state)
                states[-1] = plus_state

            elif char == '[':
                j = i + 1
                while j < len(regex_expr) and regex_expr[j] != ']':
                    j += 1

                if j >= len(regex_expr):
                    raise ValueError("Unclosed character class")

                class_spec = regex_expr[i+1:j]
                class_state = CharacterClassState(class_spec)

                parent = states[-1] if states else self.start_state
                parent.next_states.append(class_state)
                states.append(class_state)

                i = j + 1
                continue

            else:
                new_state = DotState() if char == '.' else AsciiState(char)

                parent = states[-1] if states else self.start_state
                parent.next_states.append(new_state)
                states.append(new_state)

            i += 1

        term_state = TerminationState()
        if states:
            states[-1].next_states.append(term_state)
        else:
            self.start_state.next_states.append(term_state)

    def check_string(self, input_str: str) -> bool:
        """Check if the input string matches the regex pattern.
        
        Args:
            input_str: The string to match against the pattern
            
        Returns:
            True if the string matches the pattern, False otherwise
        """
        if input_str is None:
            raise ValueError("Input string is required")

        current = {self.start_state}
        current = self._add_epsilon_transitions(current)

        if not input_str:
            return self._can_terminate_without_input(current)

        for char in input_str:
            next_states = set()
            for state in current:
                for next_state in state.next_states:
                    if next_state.check_self(char):
                        next_states.add(next_state)

            if not next_states:
                return False

            current = self._add_epsilon_transitions(next_states)

        return self._can_terminate_without_input(current)

    def _add_epsilon_transitions(self, states):
        """Add states reachable through epsilon transitions (without consuming input).
        
        Args:
            states: Set of current states
            
        Returns:
            Extended set of states including epsilon-reachable states
        """
        res = set(states)
        worklist = list(states)
        visited = set()

        while worklist:
            state = worklist.pop(0)

            if state in visited:
                continue
            visited.add(state)

            if isinstance(state, StarState):
                for next_state in state.next_states:
                    if next_state == state and next_state not in res:
                        res.add(next_state)
                        if next_state not in visited:
                            worklist.append(next_state)

            for next_state in state.next_states:
                if isinstance(next_state, StarState) and next_state not in visited:
                    res.add(next_state)
                    worklist.append(next_state)

        return res

    def _can_terminate_without_input(self, states):
        """Check if any of the states can reach a termination state without consuming more input.
        
        Args:
            states: Set of current states
            
        Returns:
            True if a termination state is reachable, False otherwise
        """
        visited = set()
        queue = list(states)

        while queue:
            state = queue.pop(0)
            if state in visited:
                continue
            visited.add(state)

            if any(isinstance(s, TerminationState) for s in state.next_states):
                return True

            for next_state in state.next_states:
                if isinstance(next_state, StarState) and next_state not in visited:
                    queue.append(next_state)

        return False
