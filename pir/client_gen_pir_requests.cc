// client_gen_pir_requests.cc

#include "external/google_dpf/pir/private_information_retrieval.pb.h"
#include "external/google_dpf/pir/prng/aes_128_ctr_seeded_prng.h"
#include "external/google_dpf/pir/testing/request_generator.h"
#include "external/google_dpf/pir/testing/mock_pir_database.h"
#include "external/google_dpf/pir/dense_dpf_pir_database.h"
#include "external/google_dpf/pir/dense_dpf_pir_client.h"
#include "external/google_dpf/pir/dense_dpf_pir_server.h"
#include "nlohmann/json.hpp"
#include "base64_utils.h"

#include <memory>
#include <string>
#include <tuple>
#include <utility>
#include <vector>
#include <iostream>
#include <algorithm>
#include <fstream>
#include <iomanip>

namespace distributed_point_functions {

void GeneratePirRequests(const std::vector<int>& indices, const int database_size) {
    // Generate plain requests for `indices`.
    auto status_or_request_generator = pir_testing::RequestGenerator::Create(
        database_size, DenseDpfPirServer::kEncryptionContextInfo);
    if (!status_or_request_generator.ok()) {
        std::cerr << "Failed to create request generator: " << status_or_request_generator.status() << '\n';
        exit(EXIT_FAILURE);
    }
    auto request_generator = std::move(status_or_request_generator.value());

    PirRequest request1, request2;

    auto status_or_plain_requests = request_generator->CreateDpfPirPlainRequests(indices);
    if (!status_or_plain_requests.ok()) {
        std::cerr << "Failed to create DPF PIR plain requests: " << status_or_plain_requests.status() << '\n';
        exit(EXIT_FAILURE);
    }
    std::tie(*request1.mutable_dpf_pir_request()->mutable_plain_request(),
            *request2.mutable_dpf_pir_request()->mutable_plain_request()) = std::move(status_or_plain_requests.value());

    // Serialize requests
    std::string serialized_request1, serialized_request2;
    request1.SerializeToString(&serialized_request1);
    request2.SerializeToString(&serialized_request2);

    std::string encoded_request1 = base64_encode(reinterpret_cast<const unsigned char*>(serialized_request1.c_str()), serialized_request1.length());
    std::string encoded_request2 = base64_encode(reinterpret_cast<const unsigned char*>(serialized_request2.c_str()), serialized_request2.length());

    // Print serialized and base64 encoded requests as a JSON object
    nlohmann::json j;
    j["request1"] = encoded_request1;
    j["request2"] = encoded_request2;

    std::cout << j.dump() << std::endl;
}

} // namespace distributed_point_functions

int main(int argc, char** argv) {
    std::string indices_str(argv[1]);
    std::vector<int> indices;
    size_t pos = 0;
    while ((pos = indices_str.find(',')) != std::string::npos) {
        indices.push_back(std::stoi(indices_str.substr(0, pos)));
        indices_str.erase(0, pos + 1);
    }
    indices.push_back(std::stoi(indices_str));
    int database_size = std::stoi(argv[2]);
    distributed_point_functions::GeneratePirRequests(indices, database_size);
    return 0;
}
