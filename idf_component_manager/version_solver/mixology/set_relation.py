# SPDX-FileCopyrightText: 2018 Sébastien Eustace
# SPDX-License-Identifier: MIT License
# SPDX-FileContributor: 2022 Espressif Systems (Shanghai) CO LTD


class SetRelation:
    """
    An enum of possible relationships between two sets.
    """

    SUBSET = 'subset'
    DISJOINT = 'disjoint'
    OVERLAPPING = 'overlapping'
