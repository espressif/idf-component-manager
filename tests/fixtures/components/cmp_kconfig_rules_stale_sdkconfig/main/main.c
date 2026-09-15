/*
 * SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
 *
 * SPDX-License-Identifier: Apache-2.0
 */
#include <stdio.h>

#include "sdkconfig.h"

#if CONFIG_REPRO_COMPONENT_A
#include "component_a.h"
#elif CONFIG_REPRO_COMPONENT_B
#include "component_b.h"
#else
#error "No reproduction component selected"
#endif

void app_main(void)
{
#if CONFIG_REPRO_COMPONENT_A
    printf("Selected %s\n", component_a_name());
#else
    printf("Selected %s\n", component_b_name());
#endif
}
