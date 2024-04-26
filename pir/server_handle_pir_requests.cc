// server_handle_pir_requests.cc

#include "external/google_dpf/pir/private_information_retrieval.pb.h"
#include "external/google_dpf/pir/prng/aes_128_ctr_seeded_prng.h"
#include "external/google_dpf/pir/testing/request_generator.h"
#include "external/google_dpf/pir/testing/mock_pir_database.h"
#include "external/google_dpf/pir/dense_dpf_pir_database.h"
#include "external/google_dpf/pir/dense_dpf_pir_client.h"
#include "external/google_dpf/pir/dense_dpf_pir_server.h"
#include "base64_utils.h"
#include "nlohmann/json.hpp"
#include "absl/strings/str_split.h"

#include <memory>
#include <string>
#include <tuple>
#include <utility>
#include <vector>
#include <iostream>
#include <algorithm>
#include <fstream>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <cstdint>
#include <cstring>

namespace distributed_point_functions {

using Database = DenseDpfPirServer::Database;
constexpr int kBitsPerBlock = 128;

std::unique_ptr<DenseDpfPirServer> server_;
std::unique_ptr<Database> database_;
std::unique_ptr<DistributedPointFunction> dpf_;
DpfParameters params_;
std::vector<std::string> elements_;
PirConfig config_;

void SetUpConfig(int database_size) {
    config_.mutable_dense_dpf_pir_config()->set_num_elements(
        database_size);
}

void SetUpDpf(int database_size) {
    // Create a DPF instance.
    params_.mutable_value_type()->mutable_xor_wrapper()->set_bitsize(
        kBitsPerBlock);
    params_.set_log_domain_size(
        static_cast<int>(std::ceil(std::log2(database_size))));
    auto status_or_dpf = DistributedPointFunction::Create(params_);
    if (!status_or_dpf.ok()) {
        std::cerr << "Failed to create DistributedPointFunction: " << status_or_dpf.status() << '\n';
        exit(EXIT_FAILURE);
    }
    dpf_ = std::move(status_or_dpf.value());
}

void DeserializeElements(const std::string& serialized_elements) {
    elements_ = absl::StrSplit(serialized_elements, absl::ByString(std::string(1, ':')));
}

void GenerateElements(const std::string& serialized_elements, int database_size) {
    if (!serialized_elements.empty()) {
        DeserializeElements(serialized_elements);
    } else {
        auto status_or_elements = pir_testing::GenerateCountingStrings(database_size, "Element ");
        if (!status_or_elements.ok()) {
            std::cerr << "Failed to generate elements: " << status_or_elements.status() << '\n';
            exit(EXIT_FAILURE);
        }
        elements_ = std::move(status_or_elements.value());
    }
}

void SetUpDatabase(const std::string& serialized_elements, int database_size) {
    SetUpConfig(database_size);

    GenerateElements(serialized_elements, database_size);

    SetUpDpf(database_size);

    auto status_or_database = pir_testing::CreateFakeDatabase<DenseDpfPirDatabase>(elements_);
    if (!status_or_database.ok()) {
        std::cerr << "Failed to create database: " << status_or_database.status() << '\n';
        exit(EXIT_FAILURE);        
    }
    database_ = std::move(status_or_database.value());
}

void HandleRequest(const std::string& serialized_request_base64, const std::string& serialized_elements, int database_size, double io_time) {
    // Set up database

    auto tik = std::chrono::high_resolution_clock::now();
    // SetUpDatabase(serialized_elements, database_size);
    SetUpConfig(database_size);
    
    auto tik2 = std::chrono::high_resolution_clock::now();
    GenerateElements(serialized_elements, database_size);
    auto tok2 = std::chrono::high_resolution_clock::now();

    auto tik3 = std::chrono::high_resolution_clock::now();
    SetUpDpf(database_size);
    auto status_or_database = pir_testing::CreateFakeDatabase<DenseDpfPirDatabase>(elements_);
    if (!status_or_database.ok()) {
        std::cerr << "Failed to create database: " << status_or_database.status() << '\n';
        exit(EXIT_FAILURE);        
    }
    auto tok3 = std::chrono::high_resolution_clock::now();
    database_ = std::move(status_or_database.value());
    auto tok = std::chrono::high_resolution_clock::now();

    auto create_db_duration = std::chrono::duration<double>(tok3 - tik3).count();
    auto serialization_duration = std::chrono::duration<double>(tok2 - tik2).count();
    auto setup_db_duration = std::chrono::duration<double>(tok - tik).count();

    auto start_time = std::chrono::high_resolution_clock::now();

    // Set up server
    auto status_or_server = DenseDpfPirServer::CreatePlain(config_, std::move(database_));
    if (!status_or_server.ok()) {
        std::cerr << "Failed to create server: " << status_or_server.status() << '\n';
        exit(EXIT_FAILURE);        
    }
    server_ = std::move(status_or_server.value());

    std::string serialized_request = base64_decode(serialized_request_base64);

    PirRequest deserialized_request;
    if (!deserialized_request.ParseFromString(serialized_request)) {
        std::cerr << "Failed to parse request from the given string.\n";
        exit(EXIT_FAILURE);
    }

    // Obtain a response to the request
    auto status_or_response = server_->HandleRequest(deserialized_request);
    if (!status_or_response.ok()) {
        std::cerr << "Failed to handle request: " << status_or_response.status() << '\n';
        exit(EXIT_FAILURE);
    }
    PirResponse response = std::move(status_or_response.value());

    // Serialize responses
    std::string serialized_response;
    response.SerializeToString(&serialized_response);

    // Encode serialized response to base64
    std::string serialized_response_base64 = base64_encode(reinterpret_cast<const unsigned char*>(serialized_response.data()), serialized_response.size());

    // Print base64 encoded serialized response
    // std::cout << serialized_response_base64 << std::endl;
    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration<double>(end_time - start_time).count();

    nlohmann::json json_obj;
    json_obj["pir_response"] = serialized_response_base64;
    json_obj["pir_inmem_time"] = duration;
    json_obj["pir_setup_db_time"] = setup_db_duration;
    json_obj["pir_serialization_duration"] = serialization_duration;
    json_obj["pir_create_db_time"] = create_db_duration;
    json_obj["pir_io_time"] = io_time; 
    std::cout << json_obj.dump() << std::endl;
}

} // namespace distributed_point_functions


// uint32_t read_uint32(std::ifstream& file) {
//     uint32_t value;
//     file.read(reinterpret_cast<char*>(&value), sizeof(value));
//     return value;
// }

// std::string read_string(std::ifstream& file, uint32_t length) {
//     std::vector<char> buffer(length);
//     file.read(buffer.data(), length);
//     return std::string(buffer.begin(), buffer.end());
// }


uint32_t read_uint32(const char*& addr) {
    uint32_t value;
    std::memcpy(&value, addr, sizeof(uint32_t));
    addr += sizeof(uint32_t);  // Move the address pointer forward
    return value;
}

// Function to read a string from a memory address
std::string read_string(const char*& addr, uint32_t length) {
    std::string value(addr, length);
    addr += length;  // Move the address pointer forward
    return value;
}

int main(int argc, char** argv) {

    auto start = std::chrono::high_resolution_clock::now();
    std::ios::sync_with_stdio(false);

    // std::string shm_name = "/dev/shm/pir";
    // std::ifstream shm_file(shm_name, std::ios::binary);

    // if (!shm_file.is_open()) {
    //     std::cerr << "Failed to open shared memory file" << std::endl;
    //     return 1;
    // }

    // uint32_t serialized_request_length = read_uint32(shm_file);
    // std::string serialized_request = read_string(shm_file, serialized_request_length);

    // uint32_t serialized_elements_length = read_uint32(shm_file);
    // std::string serialized_elements = read_string(shm_file, serialized_elements_length);

    // uint32_t database_size = read_uint32(shm_file);

    // shm_file.close();

    // std::string fifo_name = "/tmp/pir";
    // std::ifstream fifo_file(fifo_name, std::ios::binary);

    // if (!fifo_file.is_open()) {
    //     std::cerr << "Failed to open named pipe" << std::endl;
    //     return 1;
    // }

    // uint32_t serialized_request_length = read_uint32(fifo_file);
    // std::string serialized_request = read_string(fifo_file, serialized_request_length);

    // uint32_t serialized_elements_length = read_uint32(fifo_file);
    // std::string serialized_elements = read_string(fifo_file, serialized_elements_length);

    // uint32_t database_size = read_uint32(fifo_file);

    // fifo_file.close();

    std::ios::sync_with_stdio(false);

    std::string mmap_file_name = "/tmp/pir";
    int fd = open(mmap_file_name.c_str(), O_RDONLY);
    if (fd == -1) {
        std::cerr << "Failed to open memory-mapped file" << std::endl;
        return 1;
    }

    struct stat st;
    if (fstat(fd, &st) == -1) {
        std::cerr << "Failed to get file size" << std::endl;
        close(fd);
        return 1;
    }

    const char* addr = static_cast<char*>(mmap(nullptr, st.st_size, PROT_READ, MAP_PRIVATE, fd, 0));
    if (addr == MAP_FAILED) {
        std::cerr << "Failed to map file" << std::endl;
        close(fd);
        return 1;
    }

    // Read data from the memory-mapped file using the helper functions
    uint32_t serialized_request_length = read_uint32(addr);
    std::string serialized_request = read_string(addr, serialized_request_length);

    uint32_t serialized_elements_length = read_uint32(addr);
    std::string serialized_elements = read_string(addr, serialized_elements_length);

    uint32_t database_size = read_uint32(addr);


    auto end = std::chrono::high_resolution_clock::now();
    auto io_time = std::chrono::duration<double>(end - start).count();
    std::cout << "IO time: " << io_time << std::endl;

    distributed_point_functions::HandleRequest(serialized_request, serialized_elements, database_size, io_time);
    return 0;
}



// int main(int argc, char** argv) {

//     auto start = std::chrono::high_resolution_clock::now();
//     std::string serialized_json;
//     std::getline(std::cin, serialized_json);
//     auto end = std::chrono::high_resolution_clock::now();
//     auto duration = std::chrono::duration<double>(end - start).count();
//     std::cout << "Read input from python time: " << duration << std::endl;


//     auto tik = std::chrono::high_resolution_clock::now();
//     // Parse the serialized JSON to get the serialized request and elements
//     nlohmann::json json_data;
//     try {
//         json_data = nlohmann::json::parse(serialized_json);
//     } catch (const nlohmann::json::exception& e) {
//         std::cerr << "Failed to parse JSON: " << e.what() << std::endl;
//         return 1;
//     }
//     auto tok = std::chrono::high_resolution_clock::now();
//     auto json_duration = std::chrono::duration<double>(tok - tik).count();
//     std::cout << "Parsing Json time: " << json_duration << std::endl;

//     tik = std::chrono::high_resolution_clock::now();
//     std::string serialized_request;
//     std::string serialized_elements;
//     int database_size;
//     try {
//         serialized_request = json_data.at("serialized_request").get<std::string>();
//         serialized_elements = json_data.at("serialized_elements").get<std::string>();
//         database_size = json_data.at("num_database_elements");
//         std::cout << "Database size is: " << database_size << std::endl;
//     } catch (const nlohmann::json::exception& e) {
//         std::cerr << "Failed to get data from JSON: " << e.what() << std::endl;
//         return 1;
//     }
//     tok = std::chrono::high_resolution_clock::now();
//     json_duration = std::chrono::duration<double>(tok - tik).count();
//     std::cout << "Reading Json time: " << json_duration << std::endl;

//     distributed_point_functions::HandleRequest(serialized_request, serialized_elements, database_size);

//     end = std::chrono::high_resolution_clock::now();
//     duration = std::chrono::duration<double>(end - start).count();
//     std::cout << "E2E C++ time: " << duration << std::endl;
//     return 0;
// }
