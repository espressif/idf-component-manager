#include <stdio.h>
{% for header_file in header_files %}
#include "{{ header_file }}"
{%- endfor %}

void {{ func_name }}(void)
{

}
