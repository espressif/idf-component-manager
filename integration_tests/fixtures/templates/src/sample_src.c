/*
 * SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
 *
 * SPDX-License-Identifier: Apache-2.0
 */
#include <stdio.h>
{% for header_file in header_files %}
#include "{{ header_file }}"
{%- endfor %}

void {{ func_name }}(void)
{

}
