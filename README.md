<p align="center"><img src="https://github.com/wazo-platform/wazo-platform.org/raw/master/static/images/logo.png" height="200"></p>

# wazo-flask-restful-openapi-specs-generator

## Description

This tool generates OpenAPI specifications from multiple sources:
- the Marshmallow schemas
- any other YAML files containing some parts of the OpenAPI specifications


## Requirements

* Linux
* Python3.7 or later
* Python code using Flask-RESTful and Marshmallow


## Run

Let's suppose you have an API having the following structure:

    /tmp
    └── my_api                    
        └── requirements.txt                    
            my_package                  # root Python package containing all the code
            ├── my_resource.py                     
            └── my_other_resource.py
  
To generate OpenAPI specifications for an API stored in /tmp/my_api and containing a Python package named my_package:
```bash
make run source_requirements='/tmp/my_api/requirements.txt' source_code='/tmp/my_api' app_name='My API' app_version='0.0.1' openapi_version='2.0' root_package_name='my_package' output='/tmp/my_api.yaml'
```
This will generate the OpenAPI specifications in ```/tmp/my_api.yaml```

## Docker

Instead of using the Makefile, You can build a Docker image and use it:

```
docker build -t wazo-openapi-generator . --no-cache
```


After, you can execute for any project:
```bash
cd /tmp/my_api
docker run -it --mount type=bind,source="$(pwd)"/my_package/,target=/source/code/my_package/,readonly --mount type=bind,source="$(pwd)"/conf/requirements.txt,target=/source/requirements.txt,readonly --mount type=bind,source="$(pwd)"/output,target=/output/ wazo-openapi-generator app_name='My API' app_version='0.0.1' openapi_version='2.0' root_package_name='my_package' output='/output/my_api.yaml'
```


## Logs

You can set logging level to ERROR (instead of DEBUG) in the `conf/logging.json` if you want only the errors.
By default logs are stored in `log/generator*` (all the logs, in plain text).
The log files are rotated.
In any case, you can configure logging by editing the `conf/logging.json` file.
