# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from idf_component_manager.version_solver.helper import parse_constraint


def test_parse_union_of_multiple_unequal():
    assert parse_constraint('!=5.0.2,!=5.1.3,!=5.2.1')


def test_union_of_multiple_unequal():
    a = parse_constraint('!=5.0.2')
    b = parse_constraint('!=5.1.3')
    c = parse_constraint('!=5.2.1')

    d = a.intersect(b).intersect(c)

    assert str(d) == '<5.0.2 || >5.0.2,<5.1.3 || >5.1.3,<5.2.1 || >5.2.1'
    assert d.ranges[0] == parse_constraint('<5.0.2')
    assert d.ranges[1] == parse_constraint('>5.0.2,<5.1.3')
    assert d.ranges[2] == parse_constraint('>5.1.3,<5.2.1')
    assert d.ranges[3] == parse_constraint('>5.2.1')
