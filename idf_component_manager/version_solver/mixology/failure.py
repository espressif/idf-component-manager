# SPDX-FileCopyrightText: 2018 Sébastien Eustace
# SPDX-License-Identifier: MIT License
# SPDX-FileContributor: 2022-2025 Espressif Systems (Shanghai) CO LTD

import typing as t

from .incompatibility import Incompatibility
from .incompatibility_cause import ConflictCause


class SolverFailure(Exception):
    def __init__(self, incompatibility: Incompatibility) -> None:
        self._incompatibility = incompatibility

    @property
    def message(self):
        return str(self)

    def __str__(self):
        return _Writer(self._incompatibility).write()


class _Writer:
    def __init__(self, root: Incompatibility) -> None:
        self._root = root
        self._derivations: t.Dict[Incompatibility, int] = {}
        self._lines: t.List[t.Tuple[str, int]] = []
        self._line_numbers: t.Dict[Incompatibility, int] = {}

        self._count_derivations(self._root)

    def write(self):
        buffer = []

        if isinstance(self._root.cause, ConflictCause):
            buffer.append('Version solving failed:')

            # Collect all facts leading to the conflict from both sides of the cause (tree)
            buffer.extend(self._collect_facts(self._root.cause.conflict))
            buffer.extend(self._collect_facts(self._root.cause.other))

            self._visit(self._root, {})

            # Take message from the last line added by _visit
            # This is the reason for the failure
            if self._lines:
                buffer.append(f'Result: {self._lines[-1][0]}')
        else:
            buffer.append('Version solving failed.')

        return '\n'.join(buffer)

    def _collect_facts(self, incompatibility: Incompatibility) -> t.List[str]:
        prefix = '  ' * 2 + '- '

        if isinstance(incompatibility.cause, ConflictCause):
            return self._collect_facts(incompatibility.cause.conflict) + self._collect_facts(
                incompatibility.cause.other
            )
        else:
            return [f'{prefix}{incompatibility}']

    def _write(
        self, incompatibility: Incompatibility, message: str, numbered: bool = False
    ) -> None:
        if numbered:
            number = len(self._line_numbers) + 1
            self._line_numbers[incompatibility] = number
            self._lines.append((message, number))
        else:
            self._lines.append((message, None))

    def _visit(
        self,
        incompatibility: Incompatibility,
        conclusion: bool = False,
    ) -> None:
        numbered = conclusion or self._derivations[incompatibility] > 1
        conjunction = 'Because'
        incompatibility_string = str(incompatibility)

        cause: ConflictCause = incompatibility.cause
        details_for_cause = {}
        if isinstance(cause.conflict.cause, ConflictCause) and isinstance(
            cause.other.cause, ConflictCause
        ):
            conflict_line = self._line_numbers.get(cause.conflict)
            other_line = self._line_numbers.get(cause.other)

            if conflict_line is not None and other_line is not None:
                self._write(
                    incompatibility,
                    '{} {}, {}.'.format(
                        conjunction,
                        cause.conflict.and_to_string(
                            cause.other, details_for_cause, conflict_line, other_line
                        ),
                        incompatibility_string,
                    ),
                    numbered=numbered,
                )
            elif conflict_line is not None or other_line is not None:
                if conflict_line is not None:
                    with_line = cause.conflict
                    without_line = cause.other
                    line = conflict_line
                else:
                    with_line = cause.other
                    without_line = cause.conflict
                    line = other_line

                self._visit(without_line, details_for_cause)
                self._write(
                    incompatibility,
                    '{} {} ({}), {}.'.format(
                        conjunction, str(with_line), line, incompatibility_string
                    ),
                    numbered=numbered,
                )
            else:
                single_line_conflict = self._is_single_line(cause.conflict.cause)
                single_line_other = self._is_single_line(cause.other.cause)

                if single_line_other or single_line_conflict:
                    first = cause.conflict if single_line_other else cause.other
                    second = cause.other if single_line_other else cause.conflict
                    self._visit(first, details_for_cause)
                    self._visit(second, details_for_cause)
                    self._write(
                        incompatibility,
                        f'Thus, {incompatibility_string}.',
                        numbered=numbered,
                    )
                else:
                    self._visit(cause.conflict, {}, conclusion=True)
                    self._lines.append(('', None))

                    self._visit(cause.other, details_for_cause)

                    self._write(
                        incompatibility,
                        '{} {} ({}), {}'.format(
                            conjunction,
                            str(cause.conflict),
                            self._line_numbers[cause.conflict],
                            incompatibility_string,
                        ),
                        numbered=numbered,
                    )
        elif isinstance(cause.conflict.cause, ConflictCause) or isinstance(
            cause.other.cause, ConflictCause
        ):
            derived = (
                cause.conflict if isinstance(cause.conflict.cause, ConflictCause) else cause.other
            )
            ext = cause.other if isinstance(cause.conflict.cause, ConflictCause) else cause.conflict

            derived_line = self._line_numbers.get(derived)
            if derived_line is not None:
                self._write(
                    incompatibility,
                    '{} {}, {}.'.format(
                        conjunction,
                        ext.and_to_string(derived, details_for_cause, None, derived_line),
                        incompatibility_string,
                    ),
                    numbered=numbered,
                )
            elif self._is_collapsible(derived):
                derived_cause: ConflictCause = derived.cause
                if isinstance(derived_cause.conflict.cause, ConflictCause):
                    collapsed_derived = derived_cause.conflict
                else:
                    collapsed_derived = derived_cause.other

                if isinstance(derived_cause.conflict.cause, ConflictCause):
                    collapsed_ext = derived_cause.other
                else:
                    collapsed_ext = derived_cause.conflict

                details_for_cause = {}

                self._visit(collapsed_derived, details_for_cause)
                self._write(
                    incompatibility,
                    '{} {}, {}.'.format(
                        conjunction,
                        collapsed_ext.and_to_string(ext, details_for_cause, None, None),
                        incompatibility_string,
                    ),
                    numbered=numbered,
                )
            else:
                self._visit(derived, details_for_cause)
                self._write(
                    incompatibility,
                    f'{conjunction} {str(ext)}, {incompatibility_string}.',
                    numbered=numbered,
                )
        else:
            self._write(
                incompatibility,
                '{} {}, {}.'.format(
                    conjunction,
                    cause.conflict.and_to_string(cause.other, details_for_cause, None, None),
                    incompatibility_string,
                ),
                numbered=numbered,
            )

    def _is_collapsible(self, incompatibility: Incompatibility) -> bool:
        if self._derivations[incompatibility] > 1:
            return False

        cause: ConflictCause = incompatibility.cause
        if isinstance(cause.conflict.cause, ConflictCause) and isinstance(
            cause.other.cause, ConflictCause
        ):
            return False

        if not isinstance(cause.conflict.cause, ConflictCause) and not isinstance(
            cause.other.cause, ConflictCause
        ):
            return False

        complex = cause.conflict if isinstance(cause.conflict.cause, ConflictCause) else cause.other

        return complex not in self._line_numbers

    def _is_single_line(self, cause: ConflictCause) -> bool:
        return not isinstance(cause.conflict.cause, ConflictCause) and not isinstance(
            cause.other.cause, ConflictCause
        )

    def _count_derivations(self, incompatibility: Incompatibility) -> None:
        if incompatibility in self._derivations:
            self._derivations[incompatibility] += 1
        else:
            self._derivations[incompatibility] = 1
            cause = incompatibility.cause
            if isinstance(cause, ConflictCause):
                self._count_derivations(cause.conflict)
                self._count_derivations(cause.other)
