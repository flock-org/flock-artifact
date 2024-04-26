#ifndef NETIOMP_H__
#define NETIOMP_H__
#include <emp-tool/emp-tool.h>
#include "cmpc_config.h"
#include <chrono>
#include <thread>
using namespace emp;

template<int nP>
class NetIOMP { 
public:
	NetIO*ios[nP+1];
	NetIO*ios2[nP+1];
	int party;
	bool sent[nP+1];

	struct NetioArg {

	};
	NetIOMP() {}

	NetIOMP(int party, std::string addr, int port, std::string prefix, std::string cert_path) {
		this->party = party;
		memset(sent, false, nP+1);
		typedef std::chrono::high_resolution_clock Time;
		typedef std::chrono::milliseconds ms;
		typedef std::chrono::duration<float> fsec;
		
		for(int i = 1; i <= nP; ++i) {
			for(int j = 1; j <= nP; ++j) {
				std::string chan_ij = std::to_string(i) + "_" + std::to_string(j);
				if(i < j) {
					if(i == party) {
						auto t0 = Time::now();
						ios[j] = new NetIO(addr, port, prefix+"ios_"+chan_ij, cert_path);
						auto t1 = Time::now();
						ios2[j] = new NetIO(addr, port, prefix+"ios2_"+chan_ij,cert_path);
						auto t2 = Time::now();
						fsec fs = t1 - t0;
						ms d1 = std::chrono::duration_cast<ms>(fs);
						fsec fs2 = t2 - t1;
						ms d2 = std::chrono::duration_cast<ms>(fs2);
						printf("%s - %d\n", prefix+"ios_"+chan_ij, d1.count());
						printf("%s - %d\n", prefix+"ios2_"+chan_ij, d2.count());
					} else if(j == party) {
						ios[i] = new NetIO(addr, port, prefix+"ios_"+chan_ij, cert_path);
						ios2[i] = new NetIO(addr, port, prefix+"ios2_"+chan_ij, cert_path);
					}
				}
			}
		}
	}

	NetIOMP(int party, int port, std::string cert_path) {
		this->party = party;
		memset(sent, false, nP+1);
		for(int i = 1; i <= nP; ++i)for(int j = 1; j <= nP; ++j)if(i < j){
			if(i == party) {
#ifdef LOCALHOST
				usleep(1000);
				ios[j] = new NetIO(IP[j], port+2*(i*nP+j), true, cert_path);
#else
				usleep(1000);
				ios[j] = new NetIO(IP[j], port+2*(i), true, cert_path);
#endif
				ios[j]->set_nodelay();	

#ifdef LOCALHOST
				usleep(1000);
				ios2[j] = new NetIO(nullptr, port+2*(i*nP+j)+1, true, cert_path);
#else
				usleep(1000);
				ios2[j] = new NetIO(IP[j], port+2*(j)+1, true, cert_path);
#endif
				ios2[j]->set_nodelay();	
			} else if(j == party) {
#ifdef LOCALHOST
				usleep(1000);
				ios[i] = new NetIO(nullptr, port+2*(i*nP+j), true, cert_path);
#else
				usleep(1000);
				ios[i] = new NetIO(nullptr, port+2*(i), true, cert_path);
#endif
				ios[i]->set_nodelay();	

#ifdef LOCALHOST
				usleep(1000);
				ios2[i] = new NetIO(IP[i], port+2*(i*nP+j)+1, true, cert_path);
#else
				usleep(1000);
				ios2[i] = new NetIO(nullptr, port+2*(j)+1, true, cert_path);
#endif
				ios2[i]->set_nodelay();	
			}
		}
	}


	NetIOMP(int party, int port, std::string cert_path, const std::vector<std::string>& IPs) {
		typedef std::chrono::high_resolution_clock Time;
		typedef std::chrono::milliseconds ms;
		typedef std::chrono::duration<float> fsec;

        this->party = party;
        memset(sent, false, nP+1);
        for(int i = 1; i <= nP; ++i) {
            for(int j = 1; j <= nP; ++j) {
                if(i < j) {
                    if(i == party) {
                        usleep(1000);
                        ios[j] = new NetIO(IPs[j].c_str(), port+2*(i), true, cert_path);
                        ios[j]->set_nodelay();    
                        usleep(1000);
                        ios2[j] = new NetIO(IPs[j].c_str(), port+2*(j)+1, true, cert_path);
                        ios2[j]->set_nodelay();    
                    } else if(j == party) {
                        usleep(1000);
                        ios[i] = new NetIO(nullptr, port+2*(i), true, cert_path);
                        usleep(1000);
                        ios2[i] = new NetIO(nullptr, port+2*(j)+1, true, cert_path);
                        ios2[i]->set_nodelay();    
                    }
                }
            }
        }
    }

	// NetIOMP(int party, int port, int router_port, std::string cert_path, std::string router_ip, std::string server_ip, std::string prefix) {
    //     this->party = party;
    //     memset(sent, false, nP+1);
	// 	// party 1 and party 2 connects to party 3 as usual. Both 1 and 2 connects to the router for interconnect.

	// 	// GCP
	// 	if (party == 1) {
	// 		usleep(1000);
	// 		ios[2] = new NetIO(router_ip.c_str(), port+2, false, cert_path);
	// 		ios[2]->set_nodelay();
	// 		usleep(1000);
	// 		ios2[2] = new NetIO(router_ip.c_str(), port+5, false, cert_path);
	// 		ios2[2]->set_nodelay();

	// 		usleep(1000);
	// 		ios[3] = new NetIO(server_ip.c_str(), port+2, false, cert_path);
	// 		ios[3]->set_nodelay();
	// 		usleep(1000);
	// 		ios2[3] = new NetIO(server_ip.c_str(), port+7, false, cert_path);
	// 		ios2[3]->set_nodelay();
	// 	}

	// 	// AWS
	// 	if (party == 2) {
	// 		usleep(1000);
	// 		ios[1] = new NetIO(nullptr, port+2, false, cert_path);
	// 		ios[1]->set_nodelay();
	// 		usleep(1000);
	// 		ios2[1] = new NetIO(nullptr, port+5, false, cert_path);
	// 		ios2[1]->set_nodelay();

	// 		usleep(1000);
	// 		ios[3] = new NetIO(server_ip.c_str(), port+4 , false, cert_path);
	// 		ios[3]->set_nodelay();
	// 		usleep(1000);
	// 		ios2[3] = new NetIO(server_ip.c_str(), port+7, false, cert_path);
	// 		ios2[3]->set_nodelay();
	// 	}

	// 	// Azure
	// 	if (party == 3) {
	// 		usleep(1000);
	// 		ios[1] = new NetIO(nullptr, port+2, false, cert_path);
	// 		ios[1]->set_nodelay();
	// 		usleep(1000);
	// 		ios2[1] = new NetIO(nullptr, port+7, false, cert_path);
	// 		ios2[1]->set_nodelay();

	// 		usleep(1000);
	// 		ios[2] = new NetIO(nullptr, port+4, false, cert_path);
	// 		ios[2]->set_nodelay();
	// 		usleep(1000);
	// 		ios2[2] = new NetIO(nullptr, port+7, false, cert_path);
	// 		ios2[2]->set_nodelay();
	// 	}
    // }

	void startNetIO1(std::string router_ip, int router_port, int party, int dest_party, char *tag) {
		if (party == 0) {
			ios[2] = new NetIO(router_ip, router_port, dest_party, tag);
			ios[2]->set_nodelay();
		}
		if (party == 1) {
			ios[1] = new NetIO(router_ip, router_port, dest_party, tag);
			ios[1]->set_nodelay();
		}

		if (party ==2) {
			ios[1] = new NetIO(router_ip, router_port, dest_party, tag);
			ios[1]->set_nodelay();
		}
		
	}

	void startNetIO2(std::string router_ip, int router_port, int party, int dest_party, char *tag) {
		if (party == 0) {
			ios2[2] = new NetIO(router_ip, router_port, dest_party, tag);
			ios2[2]->set_nodelay();
		}
		if (party == 1) {
			ios2[1] = new NetIO(router_ip, router_port, dest_party, tag);
			ios2[1]->set_nodelay();
		}
		if (party == 2) {
			ios2[1] = new NetIO(router_ip, router_port, dest_party, tag);
			ios2[1]->set_nodelay();
		}
	}

	void startNetIO3(std::string router_ip, int router_port, int party, int dest_party, char *tag) {
		if (party == 0) {
			ios[3] = new NetIO(router_ip, router_port, dest_party, tag);
			ios[3]->set_nodelay();
		}
		if (party == 1) {
			ios[3] = new NetIO(router_ip, router_port, dest_party, tag);
			ios[3]->set_nodelay();
		}
		if (party == 2) {
			ios[2] = new NetIO(router_ip, router_port, dest_party, tag);
			ios[2]->set_nodelay();
		}
	}

	void startNetIO4(std::string router_ip, int router_port, int party, int dest_party, char *tag) {
		if (party == 0) {			
			ios2[3] = new NetIO(router_ip, router_port, dest_party, tag);
			ios2[3]->set_nodelay();
		}
		if (party == 1) {			
			ios2[3] = new NetIO(router_ip, router_port, dest_party, tag);
			ios2[3]->set_nodelay();
		}
		if (party == 2) {			
			ios2[2] = new NetIO(router_ip, router_port, dest_party, tag);
			ios2[2]->set_nodelay();
		}
	}

	void startNetIOC1(std::string router_ip, int router_port, std::string user, int party, int dest_party, char *tag, std::string cert_path) {
		if (party == 0) {
			ios[2] = new NetIO(router_ip, router_port, user, party, dest_party, tag, cert_path);
			ios[2]->set_nodelay();
		}
		if (party == 1) {
			ios[1] = new NetIO(router_ip, router_port, user, party, dest_party, tag, cert_path);
			ios[1]->set_nodelay();
		}
		if (party == 2) {
			ios[1] = new NetIO(router_ip, router_port, user, party, dest_party, tag, cert_path);
			ios[1]->set_nodelay();
		}
	}

	void startNetIOC2(std::string router_ip, int router_port, std::string user, int party, int dest_party, char *tag, std::string cert_path) {
		if (party == 0) {
			ios2[2] = new NetIO(router_ip, router_port, user, party, dest_party, tag, cert_path);
			ios2[2]->set_nodelay();
		}
		if (party == 1) {
			ios2[1] = new NetIO(router_ip, router_port, user, party, dest_party, tag, cert_path);
			ios2[1]->set_nodelay();
		}
		if (party == 2) {
			ios2[1] = new NetIO(router_ip, router_port, user, party, dest_party, tag, cert_path);
			ios2[1]->set_nodelay();
		}
	}

	void startNetIOC3(std::string router_ip, int router_port, std::string user, int party, int dest_party, char *tag, std::string cert_path) {
		if (party == 0) {
			ios[3] = new NetIO(router_ip, router_port, user, party, dest_party, tag, cert_path);
			ios[3]->set_nodelay();
		}
		if (party == 1) {
			ios[3] = new NetIO(router_ip, router_port, user, party, dest_party, tag, cert_path);
			ios[3]->set_nodelay();
		}
		if (party == 2) {
			ios[2] = new NetIO(router_ip, router_port, user, party, dest_party, tag, cert_path);
			ios[2]->set_nodelay();
		}
	}

	void startNetIOC4(std::string router_ip, int router_port, std::string user, int party, int dest_party, char *tag, std::string cert_path) {
		if (party == 0) {
			ios2[3] = new NetIO(router_ip, router_port, user, party,  dest_party, tag, cert_path);
			ios2[3]->set_nodelay();
		}
		if (party == 1) {
			ios2[3] = new NetIO(router_ip, router_port, user, party, dest_party, tag, cert_path);
			ios2[3]->set_nodelay();
		}
		if (party == 2) {
			ios2[2] = new NetIO(router_ip, router_port, user, party, dest_party, tag, cert_path);
			ios2[2]->set_nodelay();
		}
	}

	NetIOMP(int party, int port, int router_port, std::string cert_path, std::string router_ip, std::string server_ip, std::string user, std::string tag) {
        this->party = party;
		int dest_party1, dest_party2;
        memset(sent, false, nP+1);

		char *cert = getenv("RELAY_CERT");
		// party 1 and party 2 connects to party 3 as usual. Both 1 and 2 connects to the router for interconnect.

		char tag1_12[16], tag2_12[16], tag1_13[16], tag2_13[16], tag1_23[16], tag2_23[16]; 
		// GCP
		if (party == 1) {
			// 
			// 0-1 (gcp-aws) dest_party is based on same terminology as in signing.
			dest_party1 = 2;
			dest_party2 = 3;
			sprintf(tag1_12,"%sios_1_2",tag.c_str());
			sprintf(tag2_12,"%sios2_1_2",tag.c_str());
			sprintf(tag1_13,"%sios_1_3",tag.c_str());
			sprintf(tag2_13,"%sios2_1_3",tag.c_str());
			// If there are no certs passed in the env vars, check the image 
			if (cert != NULL) {
				// Already certs would be loaded in env with party = 0

				// Connection with aws
				printf("Certs provided..Starting with provided certs in env.\n");
				std::thread t1(&NetIOMP::startNetIO1, this, router_ip, router_port, party-1, dest_party1-1, tag1_12);
				std::thread t2(&NetIOMP::startNetIO2, this, router_ip, router_port, party-1, dest_party1-1, tag2_12);
				std::thread t3(&NetIOMP::startNetIO3, this, router_ip, router_port, party-1, dest_party2-1, tag1_13);
				std::thread t4(&NetIOMP::startNetIO4, this, router_ip, router_port, party-1, dest_party2-1, tag2_13);

				t1.join();
				t2.join();
				t3.join();
				t4.join();
				// ios[2] = new NetIO(router_ip, router_port, dest_party1-1, tag1_12);
				// ios[2]->set_nodelay();
				// ios2[2] = new NetIO(router_ip, router_port, dest_party1-1, tag2_12);
				// ios2[2]->set_nodelay(); 

				// // Connection with azure
				// ios[3] = new NetIO(router_ip, router_port, dest_party2-1, tag1_13);
				// ios[3]->set_nodelay();
				// ios2[3] = new NetIO(router_ip, router_port, dest_party2-1, tag2_13);
				// ios2[3]->set_nodelay();
			} else {
				printf("No certs provided..Starting with provided certs in image.\n");
				std::thread t1(&NetIOMP::startNetIOC1, this, router_ip, router_port, user, party-1, dest_party1-1, tag1_12, cert_path);
				std::thread t2(&NetIOMP::startNetIOC2, this, router_ip, router_port, user, party-1, dest_party1-1, tag2_12, cert_path);
				std::thread t3(&NetIOMP::startNetIOC3, this, router_ip, router_port, user, party-1, dest_party2-1, tag1_13, cert_path);
				std::thread t4(&NetIOMP::startNetIOC4, this, router_ip, router_port, user, party-1, dest_party2-1, tag2_13, cert_path);

				t1.join();
				t2.join();
				t3.join();
				t4.join();
				// ios[2] = new NetIO(router_ip, router_port, user, party-1, dest_party1-1, tag1_12, cert_path);
				// ios[2]->set_nodelay();
				// ios2[2] = new NetIO(router_ip, router_port, user, party-1, dest_party1-1, tag2_12, cert_path);
				// ios2[2]->set_nodelay(); 		

				// ios[3] = new NetIO(router_ip, router_port, user, party-1, dest_party2-1, tag1_13, cert_path);
				// ios[3]->set_nodelay();
				// ios2[3] = new NetIO(router_ip, router_port, user, party-1, dest_party2-1, tag2_13, cert_path);
				// ios2[3]->set_nodelay();		
			}

			// usleep(1000);
			// ios[3] = new NetIO(server_ip.c_str(), port+1, false, cert_path);
			// ios[3]->set_nodelay();
			// usleep(1000);
			// ios2[3] = new NetIO(server_ip.c_str(), port+3, false, cert_path);
			// ios2[3]->set_nodelay();
		}

		// AWS
		if (party == 2) {
			//1 -0 (aws-gcp)
			dest_party1 = 1;
			dest_party2 = 3;
			sprintf(tag1_12,"%sios_1_2",tag.c_str());
			sprintf(tag2_12,"%sios2_1_2",tag.c_str());
			sprintf(tag1_23,"%sios_2_3",tag.c_str());
			sprintf(tag2_23,"%sios2_2_3",tag.c_str());
			//usleep(1000);
			if (cert != NULL) {
				printf("Certs provided..Starting with provided certs in env.\n");

				std::thread t1(&NetIOMP::startNetIO1, this, router_ip, router_port, party-1, dest_party1-1, tag1_12);
				std::thread t2(&NetIOMP::startNetIO2, this, router_ip, router_port, party-1, dest_party1-1, tag2_12);
				std::thread t3(&NetIOMP::startNetIO3, this, router_ip, router_port, party-1, dest_party2-1, tag1_23);
				std::thread t4(&NetIOMP::startNetIO4, this, router_ip, router_port, party-1, dest_party2-1, tag2_23);

				t1.join();
				t2.join();
				t3.join();
				t4.join();
				// Already certs would be loaded in env with party = 1
				// ios[1] = new NetIO(router_ip, router_port, dest_party1-1, tag1_12);
				// ios[1]->set_nodelay();
				// //usleep(1000);
				// ios2[1] = new NetIO(router_ip, router_port, dest_party1-1, tag2_12);
				// ios2[1]->set_nodelay();

				// //usleep(1000);
				// ios[3] = new NetIO(router_ip, router_port, dest_party2-1, tag1_23);
				// ios[3]->set_nodelay();
				// //usleep(1000);
				// ios2[3] = new NetIO(router_ip, router_port, dest_party2-1, tag2_23);
				// ios2[3]->set_nodelay();
			} else {
				printf("No certs provided..Starting with provided certs in image.\n");
				std::thread t1(&NetIOMP::startNetIOC1, this, router_ip, router_port, user, party-1, dest_party1-1, tag1_12, cert_path);
				std::thread t2(&NetIOMP::startNetIOC2, this, router_ip, router_port, user, party-1, dest_party1-1, tag2_12, cert_path);
				std::thread t3(&NetIOMP::startNetIOC3, this, router_ip, router_port, user, party-1, dest_party2-1, tag1_23, cert_path);
				std::thread t4(&NetIOMP::startNetIOC4, this, router_ip, router_port, user, party-1, dest_party2-1, tag2_23, cert_path);

				t1.join();
				t2.join();
				t3.join();
				t4.join();
				// ios[1] = new NetIO(router_ip, router_port, user, party-1, dest_party1-1, tag1_12, cert_path);
				// ios[1]->set_nodelay();
				// //usleep(1000);
				// ios2[1] = new NetIO(router_ip, router_port, user, party-1, dest_party1-1, tag2_12, cert_path);
				// ios2[1]->set_nodelay();		

				// //usleep(1000);
				// ios[3] = new NetIO(router_ip, router_port, user, party-1, dest_party2-1, tag1_23, cert_path);
				// ios[3]->set_nodelay();
				// //usleep(1000);
				// ios2[3] = new NetIO(router_ip, router_port, user, party-1, dest_party2-1, tag2_23, cert_path);
				// ios2[3]->set_nodelay();		
			}
			// usleep(1000);
			// ios[3] = new NetIO(server_ip.c_str(), port+5, false, cert_path);
			// ios[3]->set_nodelay();
			// usleep(1000);
			// ios2[3] = new NetIO(server_ip.c_str(), port+7, false, cert_path);
			// ios2[3]->set_nodelay();
		}

		// Azure
		if (party == 3) {
			dest_party1 = 1;
			dest_party2 = 2;
			sprintf(tag1_13,"%sios_1_3",tag.c_str());
			sprintf(tag2_13,"%sios2_1_3",tag.c_str());
			sprintf(tag1_23,"%sios_2_3",tag.c_str());
			sprintf(tag2_23,"%sios2_2_3",tag.c_str());
			//usleep(1000);
			if (cert != NULL) {
				printf("Certs provided..Starting with provided certs in env.\n");
				std::thread t1(&NetIOMP::startNetIO1, this, router_ip, router_port, party-1, dest_party1-1, tag1_13);
				std::thread t2(&NetIOMP::startNetIO2, this, router_ip, router_port, party-1, dest_party1-1, tag2_13);
				std::thread t3(&NetIOMP::startNetIO3, this, router_ip, router_port, party-1, dest_party2-1, tag1_23);
				std::thread t4(&NetIOMP::startNetIO4, this, router_ip, router_port, party-1, dest_party2-1, tag2_23);

				t1.join();
				t2.join();
				t3.join();
				t4.join();	
				// Already certs would be loaded in env with party = 1
				// ios[1] = new NetIO(router_ip, router_port, dest_party1-1, tag1_13);
				// ios[1]->set_nodelay();
				// //usleep(1000);
				// ios2[1] = new NetIO(router_ip, router_port, dest_party1-1, tag2_13);
				// ios2[1]->set_nodelay();

				// //usleep(1000);
				// ios[2] = new NetIO(router_ip, router_port, dest_party2-1, tag1_23);
				// ios[2]->set_nodelay();
				// //usleep(1000);
				// ios2[2] = new NetIO(router_ip, router_port, dest_party2-1, tag2_23);
				// ios2[2]->set_nodelay();
			} else {
				printf("No certs provided..Starting with provided certs in image.\n");
				std::thread t1(&NetIOMP::startNetIOC1, this, router_ip, router_port, user, party-1, dest_party1-1, tag1_13, cert_path);
				std::thread t2(&NetIOMP::startNetIOC2, this, router_ip, router_port, user, party-1, dest_party1-1, tag2_13, cert_path);
				std::thread t3(&NetIOMP::startNetIOC3, this, router_ip, router_port, user, party-1, dest_party2-1, tag1_23, cert_path);
				std::thread t4(&NetIOMP::startNetIOC4, this, router_ip, router_port, user, party-1, dest_party2-1, tag2_23, cert_path);

				t1.join();
				t2.join();
				t3.join();
				t4.join();
				// ios[1] = new NetIO(router_ip, router_port, user, party-1, dest_party1-1, tag1_13, cert_path);
				// ios[1]->set_nodelay();
				// //usleep(1000);
				// ios2[1] = new NetIO(router_ip, router_port, user, party-1, dest_party1-1, tag2_13, cert_path);
				// ios2[1]->set_nodelay();		

				// //usleep(1000);
				// ios[2] = new NetIO(router_ip, router_port, user, party-1, dest_party2-1, tag1_23, cert_path);
				// ios[2]->set_nodelay();
				// //usleep(1000);
				// ios2[2] = new NetIO(router_ip, router_port, user, party-1, dest_party2-1, tag2_23, cert_path);
				// ios2[2]->set_nodelay();		
			}

			// usleep(1000);
			// ios[1] = new NetIO(nullptr, port+1, false, cert_path);
			// ios[1]->set_nodelay();
			// usleep(1000);
			// ios2[1] = new NetIO(nullptr, port+3, false, cert_path);
			// ios2[1]->set_nodelay();

			// usleep(1000);
			// ios[2] = new NetIO(nullptr, port+5, false, cert_path);
			// ios[2]->set_nodelay();
			// usleep(1000);
			// ios2[2] = new NetIO(nullptr, port+7, false, cert_path);
			// ios2[2]->set_nodelay();
		}
    }


	int64_t count() {
		int64_t res = 0;
		for(int i = 1; i <= nP; ++i) if(i != party){
			res += ios[i]->counter;
			res += ios2[i]->counter;
		}
		return res;
	}

	~NetIOMP() {
		for(int i = 1; i <= nP; ++i)
			if(i != party) {
				delete ios[i];
				delete ios2[i];
			}
	}
	void send_data(int dst, const void * data, size_t len) {
		if(dst != 0 and dst!= party) {
			if(party < dst)
				ios[dst]->send_data(data, len);
			else
				ios2[dst]->send_data(data, len);
			sent[dst] = true;
		}
	}
	void recv_data(int src, void * data, size_t len) {
		if(src != 0 and src!= party) {
			if(sent[src])flush(src);
			if(src < party)
				ios[src]->recv_data(data, len);
			else
				ios2[src]->recv_data(data, len);
		}
	}
	NetIO*& get(size_t idx, bool b = false){
		if (b)
			return ios[idx];
		else return ios2[idx];
	}
	void flush(int idx = 0) {
		if(idx == 0) {
			for(int i = 1; i <= nP; ++i)
				if(i != party) {
					ios[i]->flush();
					ios2[i]->flush();
				}
		} else {
			if(party < idx)
				ios[idx]->flush();
			else
				ios2[idx]->flush();
		}
	}
	void sync() {
		for(int i = 1; i <= nP; ++i) for(int j = 1; j <= nP; ++j) if(i < j) {
			if(i == party) {
				ios[j]->sync();
				ios2[j]->sync();
			} else if(j == party) {
				ios[i]->sync();
				ios2[i]->sync();
			}
		}
	}
};

#endif //NETIOMP_H__
