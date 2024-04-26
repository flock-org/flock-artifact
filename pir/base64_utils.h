#ifndef BASE64_UTILS_H
#define BASE64_UTILS_H

#include <string>

std::string base64_decode(const std::string& encoded_string);
std::string base64_encode(const unsigned char* bytes_to_encode, unsigned int in_len);

#endif // BASE64_UTILS_H
