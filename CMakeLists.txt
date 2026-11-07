cmake_minimum_required(VERSION 3.21)
project(vector VERSION 1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

option(BUILD_TESTS "Build unit tests" ON)
option(BUILD_EXAMPLES "Build examples" ON)
option(VECTOR_USE_MBEDTLS "Use mbedTLS for cryptography (falls back to pure-C++ if not found)" ON)
option(VECTOR_USE_NS3 "Build ns-3 packet-level simulator" OFF)

enable_testing()

if(VECTOR_USE_MBEDTLS)
    find_package(MbedTLS QUIET)
    if(MbedTLS_FOUND)
        message(STATUS "mbedTLS found: using hardware-accelerated cryptography")
    else()
        message(STATUS "mbedTLS not found: using pure-C++ cryptography fallback")
    endif()
endif()

if(VECTOR_USE_NS3)
    # ns-3 is installed via homebrew at /opt/homebrew
    set(NS3_INCLUDE_DIRS "/opt/homebrew/include" CACHE PATH "ns-3 include directory")
    set(NS3_LIBRARIES
        "/opt/homebrew/lib/libns3.49-core.dylib"
        "/opt/homebrew/lib/libns3.49-network.dylib"
        "/opt/homebrew/lib/libns3.49-internet.dylib"
        CACHE STRING "ns-3 libraries")

    find_path(NS3_INCLUDE_DIR ns3/core-module.h HINTS /opt/homebrew/include)
    find_library(NS3_CORE_LIBRARY ns3.49-core HINTS /opt/homebrew/lib)

    if(NS3_INCLUDE_DIR AND NS3_CORE_LIBRARY)
        set(NS3_FOUND TRUE)
        message(STATUS "ns-3 found: building vector_ns3_sim packet simulator")
        add_subdirectory(src/vector)
    else()
        message(STATUS "ns-3 not found: ns-3 simulator target disabled")
        set(VECTOR_USE_NS3 OFF CACHE INTERNAL "")
    endif()
endif()

add_subdirectory(src)
add_subdirectory(tests)
add_subdirectory(scripts)
