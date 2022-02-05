from setuptools import find_namespace_packages, setup
import os
import ast
import re


project_name = "dbt-athena2"
cur_dir = os.path.abspath(os.path.dirname(__file__))


def read_version():
    _version_re = re.compile(r"version\s+=\s+(.*)")
    _version_path = os.path.join(cur_dir, "dbt", "adapters", "athena", "__version__.py")
    with open(_version_path, "rb") as f:
        version = str(ast.literal_eval(_version_re.search(f.read().decode("utf-8")).group(1)))

    return version


def read_requirements():
    with open(os.path.join(cur_dir, "requirements.txt")) as f:
        content = f.read()
        requirements = content.split("\n")
    return requirements


def read_readme():
    with open(os.path.join(cur_dir, "README.md")) as f:
        long_description = f.read()
    return long_description


setup(
    name=project_name,
    version=read_version(),
    description="The athena adapter plugin for dbt (data build tool)",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="Duc Nguyen",
    author_email="vanducng.dev@gmail.com",
    url="https://github.com/vdn-tools/dbt-athena2",
    packages=find_namespace_packages(include=["dbt", "dbt.*"]),
    include_package_data=True,
    install_requires=read_requirements(),
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: Unix",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)
