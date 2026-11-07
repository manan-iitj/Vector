# VECTOR source library
# NOTE: src/simulation/vector_ns3_simulation.cc is a standalone ns-3 example
# that uses the ns-3 Object/Ptr API and is built as a separate executable
# when VECTOR_USE_NS3 is enabled.

set(VECTOR_SOURCES
    ${CMAKE_CURRENT_SOURCE_DIR}/network/node.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/network/network_manager.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/topology/debruijn_topology.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/topology/chordal_ring_topology.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/topology/routing_engine.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/security/crypto_manager.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/security/handshake.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/security/turboblom.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/clustering/heed.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/clustering/leach.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/election/candidate_manager.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/election/leader_election.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/joining/joining_protocol.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/recovery/search_protocol.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/recovery/network_recovery.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/energy/energy_model.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/metrics/metrics_collector.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/simulation/vector_simulation.cpp
)

# Public and local header directories
include_directories("${CMAKE_CURRENT_SOURCE_DIR}/../include")
include_directories("${CMAKE_CURRENT_SOURCE_DIR}")

add_library(vector STATIC ${VECTOR_SOURCES})

set(VECTOR_EXTRA_LIBS "")

if(VECTOR_USE_MBEDTLS AND MbedTLS_FOUND)
    target_compile_definitions(vector PRIVATE VECTOR_USE_MBEDTLS)
    get_filename_component(MBEDTLS_PREFIX "${MbedTLS_DIR}/../../.." ABSOLUTE)
    target_include_directories(vector PRIVATE "${MBEDTLS_PREFIX}/include")
    message(STATUS "mbedTLS include dir: ${MBEDTLS_PREFIX}/include")
    target_link_libraries(vector
        ${VECTOR_EXTRA_LIBS}
        MbedTLS::mbedtls_static
    )
else()
    target_link_libraries(vector
        ${VECTOR_EXTRA_LIBS}
    )
endif()

target_include_directories(vector PUBLIC
    "${CMAKE_CURRENT_SOURCE_DIR}/../include"
    "${CMAKE_CURRENT_SOURCE_DIR}"
)

# ------------------------------------------------------------------
# ns-3 packet-level simulator (separate executable target)
# ------------------------------------------------------------------
# Added via add_subdirectory(src/vector) from parent CMakeLists.txt

# ------------------------------------------------------------------
# Standalone metrics simulator (no ns-3 dependency)
# ------------------------------------------------------------------
add_executable(vector_standalone_sim
    ${CMAKE_CURRENT_SOURCE_DIR}/simulation/vector_standalone_sim.cc
)
target_link_libraries(vector_standalone_sim
    vector
)
target_include_directories(vector_standalone_sim PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/../include"
    "${CMAKE_CURRENT_SOURCE_DIR}"
)
message(STATUS "Standalone simulator target: vector_standalone_sim")
