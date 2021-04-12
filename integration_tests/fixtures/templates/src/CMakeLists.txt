idf_component_register(SRCS "{{ component }}.c"
                    INCLUDE_DIRS "include"
                    {% for parameter in parameters %}
                    {{ parameter }}
                    {%- endfor %}

)
