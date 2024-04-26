cmake_minimum_required (VERSION 2.8.11)
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Debug and Optimization Flags
set(CMAKE_C_FLAGS_DEBUG "${CMAKE_C_FLAGS_DEBUG} -O0 -g")
set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG} -O0 -g")
set(CMAKE_C_FLAGS_RELEASE "${CMAKE_C_FLAGS_RELEASE} -O3")
set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -O3")

# Architecture-specific flag
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -march=native")

project (mpcauth)
set(NAME "mpcauth")

# Required Packages
find_package(OpenSSL REQUIRED)
find_package(Threads REQUIRED)

# Includes
include_directories(${OPENSSL_INCLUDE_DIR})
link_libraries(OpenSSL::Crypto)
link_libraries(${CMAKE_THREAD_LIBS_INIT})

include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/emp-tool/
    ${CMAKE_CURRENT_SOURCE_DIR}/emp-ot/
    ${CMAKE_CURRENT_SOURCE_DIR}/emp-agmpc/
    ${CMAKE_CURRENT_SOURCE_DIR}/external/jsoncpp/include
    ${CMAKE_CURRENT_SOURCE_DIR}/utils
)

# Add Subdirectories
add_subdirectory(emp-tool)
add_subdirectory(emp-ot)
add_subdirectory(emp-agmpc)
add_subdirectory(./external/jsoncpp)


add_executable(auth_passcode_2PC ./apps/auth_passcode_2PC.cpp ./utils/base64.cpp)
target_link_libraries(
    auth_passcode_2PC
    PRIVATE
    emp-tool
    jsoncpp_lib
    OpenSSL::Crypto # <-- explicitly link against OpenSSL's crypto library
    OpenSSL::SSL    # <-- explicitly link against OpenSSL's SSL library
)

add_executable(auth_passcode_3PC ./apps/auth_passcode_3PC.cpp ./utils/base64.cpp)
target_link_libraries(
    auth_passcode_3PC
    PRIVATE
    emp-tool
    jsoncpp_lib
    OpenSSL::Crypto # <-- explicitly link against OpenSSL's crypto library
    OpenSSL::SSL    # <-- explicitly link against OpenSSL's SSL library
)

add_executable(aes_ctr "./apps/aes_ctr.cpp")
target_link_libraries(
    aes_ctr
    PRIVATE
    jsoncpp_lib
    OpenSSL::Crypto # <-- explicitly link against OpenSSL's crypto library
    OpenSSL::SSL    # <-- explicitly link against OpenSSL's SSL library
)

add_executable(create_authshare_3PC "./apps/create_authshare_3PC.cpp")
target_link_libraries(
    create_authshare_3PC
    PRIVATE
    OpenSSL::Crypto # <-- explicitly link against OpenSSL's crypto library
    OpenSSL::SSL    # <-- explicitly link against OpenSSL's SSL library
)

add_executable(create_authshare_2PC "./apps/create_authshare_2PC.cpp")
target_link_libraries(
    create_authshare_2PC
    PRIVATE
    OpenSSL::Crypto # <-- explicitly link against OpenSSL's crypto library
    OpenSSL::SSL    # <-- explicitly link against OpenSSL's SSL library
)
