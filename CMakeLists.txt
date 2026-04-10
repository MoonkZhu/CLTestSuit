cmake_minimum_required(VERSION 3.10)
project(CLTestSuit)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(OpenCL REQUIRED)

file(GLOB TEST_DIRS RELATIVE "${CMAKE_CURRENT_SOURCE_DIR}/tests" "${CMAKE_CURRENT_SOURCE_DIR}/tests/*")

foreach(TEST_NAME ${TEST_DIRS})
    if(IS_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/tests/${TEST_NAME}")
        # Skip auto-build if the test directory has a run.sh script,
        # as it will manage its own build/run process.
        if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/tests/${TEST_NAME}/run.sh")
            continue()
        endif()

        file(GLOB CPP_FILES "${CMAKE_CURRENT_SOURCE_DIR}/tests/${TEST_NAME}/*.cpp")

        if(CPP_FILES)
            add_executable(${TEST_NAME} ${CPP_FILES})
            target_link_libraries(${TEST_NAME} OpenCL::OpenCL)

            # Set the output name to test_bin and put it in build/tests/<test_name>
            set_target_properties(${TEST_NAME} PROPERTIES
                OUTPUT_NAME "test_bin"
                RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/tests/${TEST_NAME}"
            )

            # Copy .cl and .txt files from source to build directory so tests can find them
            file(GLOB CL_FILES "${CMAKE_CURRENT_SOURCE_DIR}/tests/${TEST_NAME}/*.cl")
            if(CL_FILES)
                add_custom_command(TARGET ${TEST_NAME} POST_BUILD
                    COMMAND ${CMAKE_COMMAND} -E copy_if_different
                    ${CL_FILES}
                    "${CMAKE_CURRENT_BINARY_DIR}/tests/${TEST_NAME}/"
                )
            endif()

            file(GLOB TXT_FILES "${CMAKE_CURRENT_SOURCE_DIR}/tests/${TEST_NAME}/*.txt")
            if(TXT_FILES)
                add_custom_command(TARGET ${TEST_NAME} POST_BUILD
                    COMMAND ${CMAKE_COMMAND} -E copy_if_different
                    ${TXT_FILES}
                    "${CMAKE_CURRENT_BINARY_DIR}/tests/${TEST_NAME}/"
                )
            endif()
        endif()
    endif()
endforeach()
