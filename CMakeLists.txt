cmake_minimum_required(VERSION 3.10)
project(CLTestSuit)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(OpenCL REQUIRED)

file(GLOB TEST_DIRS RELATIVE "${CMAKE_CURRENT_SOURCE_DIR}/tests" "${CMAKE_CURRENT_SOURCE_DIR}/tests/*")

foreach(TEST_NAME ${TEST_DIRS})
    if(IS_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/tests/${TEST_NAME}")
        file(GLOB CPP_FILES "${CMAKE_CURRENT_SOURCE_DIR}/tests/${TEST_NAME}/*.cpp")

        if(CPP_FILES)
            add_executable(${TEST_NAME} ${CPP_FILES})
            target_link_libraries(${TEST_NAME} OpenCL::OpenCL)

            # Set the output name to test_bin
            set_target_properties(${TEST_NAME} PROPERTIES
                OUTPUT_NAME "test_bin"
                RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/tests/${TEST_NAME}"
            )
        endif()
    endif()
endforeach()
