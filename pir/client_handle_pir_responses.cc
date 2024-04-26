// client_handle_pir_responses.cc

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

namespace distributed_point_functions {

void ProcessResponses(const std::string& serialized_responses_json) {
    // Deserialize the JSON to get the serialized responses
    nlohmann::json responses_json = nlohmann::json::parse(serialized_responses_json);

    // Grab both of the serialized responses from the JSON
    std::string serialized_response1_base64 = responses_json["response1"];
    std::string serialized_response2_base64 = responses_json["response2"];

    // Decode the base64 encoded serialized responses
    std::string serialized_response1 = base64_decode(serialized_response1_base64);
    std::string serialized_response2 = base64_decode(serialized_response2_base64);

    // Deserialize responses
    PirResponse deserialized_response1, deserialized_response2;
    deserialized_response1.ParseFromString(serialized_response1);
    deserialized_response2.ParseFromString(serialized_response2);
   
    ASSERT_EQ(deserialized_response1.dpf_pir_response().masked_response_size(),
              deserialized_response2.dpf_pir_response().masked_response_size());

    std::vector<std::string> result;
    for (int i = 0; i < deserialized_response1.dpf_pir_response().masked_response_size();
        i++) {
        ASSERT_EQ(deserialized_response1.dpf_pir_response().masked_response(i).size(),
                  deserialized_response2.dpf_pir_response().masked_response(i).size());

        result.emplace_back(
            deserialized_response1.dpf_pir_response().masked_response(i).size(), '\0');
        for (int j = 0;
            j < deserialized_response1.dpf_pir_response().masked_response(i).size(); ++j) {
            result.back()[j] =
            deserialized_response1.dpf_pir_response().masked_response(i)[j] ^
            deserialized_response2.dpf_pir_response().masked_response(i)[j];
        }
    }

    // Concatenate the final answers with ", " separator and print them on the same line
    // std::cout << "Results: ";
    for (size_t i = 0; i < result.size(); ++i) {
        std::cout << result[i];
        if (i < result.size() - 1) {
            std::cout << ", ";
        }
    }
    std::cout << '\n';
}
} // namespace distributed_point_functions

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "Usage: " << argv[0] << " <serialized_responses_json>" << std::endl;
        return 1;
    }

    std::string serialized_responses_json(argv[1]);

    distributed_point_functions::ProcessResponses(serialized_responses_json);
    return 0;
}
