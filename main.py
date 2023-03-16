import argparse
import importlib
import inspect
import json
import logging.config
import os
import sys
from typing import List

from apispec import APISpec
from apispec.exceptions import DuplicateComponentNameError
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec.yaml_utils import load_yaml_from_docstring
from apispec_fromfile import FromFilePlugin
from apispec_flask_restful import RestfulPlugin
from flask import Flask
from flask_restful import Api
from marshmallow import Schema

with open("conf/logging.json", "r", encoding="utf-8") as fd:
    CONFIG = json.load(fd)

# Set up logging
logging.config.dictConfig(CONFIG["logging"])
logger = logging.getLogger(__name__)


def gen_spec(title, version, openapi_version) -> APISpec:
    """
    Return an object representing the OpenAPI specifications.

    :param title: title of the application
    :param version: version of the application
    :param openapi_version: OpenAPI version
    :returns: the OpenAPI specifications
    """

    # FromFilePlugin: used to read openapi spec stored in yml file
    # MarshmallowPlugin: used to init openapi schemas from Marshmallow schemas
    # RestfulPlugin: used to provide a path helper that allows to pass a Flask-RESTful resource object to path.
    return APISpec(
        title=title,
        version=version,
        openapi_version=openapi_version,
        plugins=[MarshmallowPlugin(), FromFilePlugin("resource"), RestfulPlugin()],
    )


def get_fullpath_files(relative_path, filename=None, suffix=None) -> List[str]:
    """
    Return a list of files.

    :param relative_path: the relative path to the folder to browse
    :param filename: file name
    :param suffix: the suffix of the file name
    :returns: a list containing the full absolute path to the files (including the file names)
    """
    logger.debug(
        f"trying to find files in {relative_path} with filename={filename}, suffix={suffix}..."
    )
    cwd = os.getcwd()
    matching_files = []
    for root, dirs, files in os.walk(relative_path):
        for f in files:
            logger.debug(f"{f} found")
            if (
                (filename and f == filename)
                or (suffix and f.endswith(suffix))
                or (filename is None and suffix is None)
            ):
                logger.debug(
                    f"{f} found in {relative_path} and matching criteria: filename={filename}, suffix={suffix}"
                )
                matching_files.append(os.path.join(cwd, root, f))
    logger.debug(
        f"files found in {relative_path} and matching criteria: filename={filename}, suffix={suffix}: {matching_files}"
    )
    return matching_files


def to_module_fullpath(p: str):
    if p.endswith(".py"):
        p = p[0:-3]
    return p.replace("/", ".")


def load_yml(relative_path, spec):
    """
    Add parameters, schemas and responses into the OpenAPI specifications.

    :param relative_path: the relative path to the folder to browse
    :param spec: the OpenAPI specifications that will be updated
    """
    logger.debug(
        f"trying to load all YAML files from {relative_path} "
        f"into the OpenAPI specifications..."
    )
    yaml_files = get_fullpath_files(relative_path, suffix=".yml")

    for f in yaml_files:
        logger.debug(f"trying to load {f}...")
        with open(f) as fw:
            logger.debug(f"trying to parse content {f}...")
            d = load_yaml_from_docstring(fw.read())

            try:
                logger.debug(f"trying to retrieve OpenAPI parameters in {f}...")
                for key, value in d["parameters"].items():
                    logger.debug(f"OpenAPI parameter found in {f}: {key}->{value}")
                    spec.components.parameter(key, value["in"], value)
                    logger.debug(f"OpenAPI parameter in {f}: {key}->{value} loaded")
            except KeyError:
                pass

            try:
                logger.debug(f"trying to retrieve OpenAPI schemas in {f}...")
                for key, value in d["schemas"].items():
                    logger.debug(f"OpenAPI schema found in {f}: {key}->{value}")
                    spec.components.schema(key, value)
                    logger.debug(f"OpenAPI schema in {f}: {key}->{value} loaded")
            except KeyError:
                pass

            try:
                logger.debug(f"trying to retrieve OpenAPI responses in {f}...")
                for key, value in d["responses"].items():
                    logger.debug(f"OpenAPI response found in {f}: {key}->{value}")
                    spec.components.response(key, value)
                    logger.debug(f"OpenAPI response in {f}: {key}->{value} loaded")
            except KeyError:
                pass
    logger.debug(
        f"YAML files in {relative_path} loaded into the OpenAPI specifications"
    )


def import_python_modules(relative_path, extending_class) -> List[str]:
    """
    Import all Python modules in which there are classes extending the extending_class.
    Return a list class name/class.

    :param relative_path: the relative path to the folder to browse
    :param extending_class: the parent class for which the classes in the modules must extend
    :returns: a list containing class names and the class itself.
    """
    logger.debug(
        f"trying to import Python modules containing classes extending {extending_class} in {relative_path}..."
    )
    py_files = get_fullpath_files(relative_path, suffix="py")

    py_modules = []

    for f in py_files:
        n = to_module_fullpath(os.path.relpath(f))

        logger.debug(f"importing module {n}...")
        try:
            m = importlib.import_module(n)
            for name, cls in inspect.getmembers(m, inspect.isclass):
                found = False
                # only the members of the module itself, not the imported ones
                if cls.__module__ == n:
                    if issubclass(cls, extending_class):
                        logger.debug(
                            f"module {n} has a class ({name}) extending {extending_class}"
                        )
                        py_modules.append([name, cls])
                        found = True
            if not found:
                logger.debug(
                    f"no classes extending {extending_class} found in {n}, undo import"
                )
                del m
        except:
            logger.exception(f"Cannot import module {n}")

    logger.debug(
        f"Python modules containing classes extending {extending_class} in {relative_path} imported"
    )
    return py_modules


def load_marshmallow_schemas(relative_path, spec):
    """
    Add marshmallow schemas into the OpenAPI specifications.

    :param relative_path: the relative path to the folder to browse
    :param spec: the OpenAPI specifications that will be updated
    """
    logger.debug(
        f"trying to load all marshmallow schemas from {relative_path} "
        f"into the OpenAPI specifications..."
    )

    py_modules = import_python_modules(relative_path, Schema)

    for m in py_modules:
        # https://stackoverflow.com/questions/55067166/in-python-how-do-i-get-the-list-of-classes-defined-within-a-particular-file
        try:
            logger.debug(
                f"trying to load marshmallow schema named {m[0]} as a OpenAPI schema..."
            )
            spec.components.schema(m[0], schema=m[1])
            logger.debug(f"marshmallow schema named {m[0]} loaded as a OpenAPI schema")
        except DuplicateComponentNameError as e:
            logger.warning(f"OpenAPI component schema {m[0]} already declared!")

    logger.debug(
        f"Marshmallow schemas in {relative_path} loaded into the OpenAPI specifications"
    )


def load_paths_from_py(relative_path, spec, prefix=None):
    """
    Add paths into the OpenAPI specifications.

    :param relative_path: the relative path to the folder to browse
    :param spec: the OpenAPI specifications that will be updated
    :param prefix: the prefix of each endpoints. For example: /1.1
    """
    logger.debug(
        f"trying to load all OpenAPI paths from {relative_path} "
        f"into the OpenAPI specifications..."
    )

    app = Flask("Temporary App")
    api = Api(app, prefix=prefix)

    py_plugins = get_fullpath_files(relative_path, suffix="py")

    for f in py_plugins:
        n = to_module_fullpath(os.path.relpath(f))

        for name, value in inspect.getmembers(importlib.import_module(n)):
            if inspect.isclass(value):
                try:
                    for k, v in value.resources.items():
                        api.add_resource(k, *v)
                        spec.path(resource=k, api=api, app=app)
                except AttributeError as e:
                    pass

    logger.debug(
        f"Marshmallow schemas in {relative_path} loaded into the OpenAPI specifications"
    )


def cli():
    """
    Interpret the parameters given by the user
    :return: None
    """
    parser = argparse.ArgumentParser(
        description="OpenAPI specifications generator",
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=50),
    )
    required_params = parser.add_argument_group("required arguments")
    required_params.add_argument(
        "--app_name",
        help="the name of the application for which the specifications will be generated",
        action="store",
        required=True,
    )
    required_params.add_argument(
        "--app_version",
        help="the version of the application",
        action="store",
        required=True,
    )
    required_params.add_argument(
        "--openapi_version",
        help="the version of the generated OpenAPI specifications",
        action="store",
        required=True,
    )
    required_params.add_argument(
        "--root_package_name",
        help="the name of the main Python package that will be analyzed",
        action="store",
        required=True,
    )
    required_params.add_argument(
        "--output",
        help="the full path file name of the generated OpenAPI specifications",
        action="store",
        required=True,
    )

    required_params.add_argument(
        "--source_code",
        help="the working directory containing the root Python package",
        action="store",
        required=True,
    )

    args = parser.parse_args()

    # for files reading
    os.chdir(args.source_code)
    # for Python modules import
    sys.path.append(os.path.join(os.path.dirname(__file__), args.source_code))

    spec = gen_spec(args.app_name, args.app_version, args.openapi_version)
    load_yml(args.root_package_name, spec)
    load_marshmallow_schemas(args.root_package_name, spec)
    load_paths_from_py(args.root_package_name, spec)

    with open(args.output, "w") as f:
        logger.info(f"Writing OpenAPI specifications in {args.output}")
        f.write(spec.to_yaml())


if __name__ == "__main__":
    cli()
