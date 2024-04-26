#include <iostream>
#include <cstring>
#include <openssl/aes.h>

using namespace std;

// std::string encrypt_AES_256(std::string plaintext, std::string key) {
//     // Create a new AES key object
//     AES_KEY aes_key;
//     AES_set_encrypt_key((const unsigned char*) key.c_str(), 256, &aes_key);

//     // Calculate the number of blocks in the plaintext
//     size_t num_blocks = plaintext.length() / AES_BLOCK_SIZE + 1;

//     // Calculate the number of padding bytes needed
//     size_t padding_len = AES_BLOCK_SIZE - plaintext.length() % AES_BLOCK_SIZE;
//     if (padding_len == 0) {
//         padding_len = AES_BLOCK_SIZE;
//     }

//     // Add the padding bytes to the plaintext
//     std::string padded_text = plaintext;
//     padded_text.resize(plaintext.length() + padding_len, (char)padding_len);

//     // Allocate memory for the ciphertext
//     size_t padded_len = padded_text.length();
//     unsigned char* ciphertext = new unsigned char[padded_len];

//     // Encrypt the data using AES-256
//     for (size_t i = 0; i < num_blocks; i++) {
//         AES_encrypt((const unsigned char*) (padded_text.c_str() + i*AES_BLOCK_SIZE), ciphertext + i*AES_BLOCK_SIZE, &aes_key);
//     }

//     // Convert the ciphertext to a string
//     std::string encrypted_data((char*) ciphertext, padded_len);

//     // Free the memory used for the ciphertext
//     delete[] ciphertext;

//     return encrypted_data;
// }


// std::string decrypt_AES_256(std::string ciphertext, std::string key) {
//     // Create a new AES key object
//     AES_KEY aes_key;
//     AES_set_decrypt_key((const unsigned char*) key.c_str(), 256, &aes_key);

//     // Calculate the number of blocks in the ciphertext
//     size_t num_blocks = ciphertext.length() / AES_BLOCK_SIZE;

//     // Allocate memory for the plaintext
//     size_t padded_len = num_blocks * AES_BLOCK_SIZE;
//     unsigned char* plaintext = new unsigned char[padded_len];

//     // Decrypt the data using AES-256
//     for (size_t i = 0; i < num_blocks; i++) {
//         AES_decrypt((const unsigned char*) (ciphertext.c_str() + i*AES_BLOCK_SIZE), plaintext + i*AES_BLOCK_SIZE, &aes_key);
//     }

//     // Determine the number of padding bytes
//     size_t padding_len = (size_t) plaintext[padded_len - 1];
//     if (padding_len > AES_BLOCK_SIZE || padding_len > padded_len) {
//         throw std::runtime_error("Invalid padding");
//     }

//     // Strip off the padding bytes
//     size_t unpadded_len = padded_len - padding_len;
//     std::string decrypted_data((char*) plaintext, unpadded_len);

//     // Free the memory used for the plaintext
//     delete[] plaintext;

//     return decrypted_data;
// }