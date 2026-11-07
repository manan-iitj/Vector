# VECTOR ns-3 module CMakeLists.txt
# Built when VECTOR_USE_NS3 is ON

set(VECTOR_NS3_SOURCES
    ${CMAKE_CURRENT_SOURCE_DIR}/main.cc
    ${CMAKE_CURRENT_SOURCE_DIR}/model/vector-node.cc
    ${CMAKE_CURRENT_SOURCE_DIR}/model/vector-topology.cc
    ${CMAKE_CURRENT_SOURCE_DIR}/model/vector-crypto.cc
    ${CMAKE_CURRENT_SOURCE_DIR}/model/vector-routing.cc
    ${CMAKE_CURRENT_SOURCE_DIR}/model/vector-clustering.cc
    ${CMAKE_CURRENT_SOURCE_DIR}/helper/vector-helper.cc
    # ${CMAKE_CURRENT_SOURCE_DIR}/helper/vector-net-device.cc  # Excluded: ns-3 API incompatibility
)

add_executable(vector_ns3_sim ${VECTOR_NS3_SOURCES})

target_link_libraries(vector_ns3_sim
    ${NS3_LIBRARIES}
    /opt/homebrew/lib/libmbedcrypto.dylib
)

target_compile_definitions(vector_ns3_sim PRIVATE MBEDTLS_DECLARE_PRIVATE_IDENTIFIERS)
target_include_directories(vector_ns3_sim PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}"
    "${CMAKE_CURRENT_SOURCE_DIR}/model"
    "${CMAKE_CURRENT_SOURCE_DIR}/helper"
    "${NS3_INCLUDE_DIRS}"
)

message(STATUS "ns-3 simulator target: vector_ns3_sim")
