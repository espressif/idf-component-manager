idf_component_register(SRCS "cmp_cmake_function.c"
                       INCLUDE_DIRS "include")

# Define a CMake function that other components can use
function(test_cmake_function_from_component output_var)
    set(${output_var} "CMAKE_FUNCTION_WORKS" PARENT_SCOPE)
    message(STATUS "test_cmake_function_from_component was called successfully!")
endfunction()
