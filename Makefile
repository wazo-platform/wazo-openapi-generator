SHELL = bash

run:
	@echo "Setup environment for the tool execution"
	@pip3 install virtualenv --force-reinstall
	@virtualenv --python=python3 venv
	@source venv/bin/activate;pip install -r '$(source_requirements)' --force-reinstall;mkdir -p log
	@source venv/bin/activate;pip install -r conf/requirements.txt
	@echo "Generate OpenAPI specifications"
	@source venv/bin/activate;python3 main.py --source_code '$(source_code)' --app_name '$(app_name)' --app_version '$(app_version)' --openapi_version '$(openapi_version)' --root_package_name  '$(root_package_name)' --output '$(output)'
