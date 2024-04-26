### Step 1: install AWS Lambda runtime
```bash
$ git clone https://github.com/awslabs/aws-lambda-cpp.git
$ cd aws-lambda-cpp
$ mkdir build
$ cd build
$ cmake .. -DCMAKE_BUILD_TYPE=Release
$ make && make install
```

### Step 2: building the executables
```bash
mkdir build
cd build
cmake ..
make -j
```

### Packaging the executables
Run the following script:
```bash
bash package_lambda.sh
```

### Updating the codes on AWS Lambda
One way to update the code is to use the AWS cli:
```bash
aws lambda update-function-code --function-name emp-lambda --zip-file fileb://emp-lambda.zip
aws lambda update-function-code --function-name emp-lambda2 --zip-file fileb://emp-lambda.zip
```

Input config has the following format:
```json
{
  "partyInt": 1,
  "routerAddr": "tcp://184.72.21.66:6379",
  "circuit": "comparison256.txt",
  "encKey": "82290e51cae1aced3d03a01bbae34b4baccefa313c8cc340ad91771869464a4f"
}
```

One caveat is that the number of parties is hardcoded. It needs to be set during compile time so we could not pass its value during runtime. 


### Testing the code locally
The local test file is  `tests/test_agmpc.cpp`, first build the executables
```bash
cd build
cmake ..
make test_agmpc
```
Then, on two separate terminals, run the following two commands (the port number does not matter, it is just a placeholder):
```
./bin/test_agmpc 1 8080
./bin/test_agmpc 2 8080
```
