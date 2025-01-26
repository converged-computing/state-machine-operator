import os

from setuptools import find_packages, setup  # noqa: H301

DESCRIPTION = "State Machine orchestrator intended for Kubernetes"

# Try to read description, otherwise fallback to short description
try:
    with open(os.path.abspath("README.md")) as filey:
        LONG_DESCRIPTION = filey.read()
except Exception:
    LONG_DESCRIPTION = DESCRIPTION

with open(os.path.join("state_machine_operator", "__init__.py")) as fd:
    version = fd.read().strip().replace("__version__ = ", "").replace('"', "")


if __name__ == "__main__":
    setup(
        name="state-machine-operator",
        version=version,
        author="Vanessasaurus",
        author_email="vsoch@users.noreply.github.com",
        maintainer="Vanessasaurus",
        packages=find_packages(),
        include_package_data=True,
        zip_safe=False,
        url="https://github.com/converged-computing/state-machine-operator",
        license="MIT",
        description=DESCRIPTION,
        long_description=LONG_DESCRIPTION,
        long_description_content_type="text/markdown",
        keywords="state machine, simulation, hpc, kubernetes",
        setup_requires=["pytest-runner"],
        install_requires=[
            "python-statemachine",
            "jsonschema",
            "Jinja2",
            "pyyaml",
            "kubernetes",
        ],
        tests_require=["pytest", "pytest-cov"],
        classifiers=[
            "Intended Audience :: Science/Research",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: Apache Software License",
            "Programming Language :: C",
            "Programming Language :: Python",
            "Topic :: Software Development",
            "Topic :: Scientific/Engineering",
            "Operating System :: Unix",
            "Programming Language :: Python :: 3.11",
        ],
        entry_points={
            "console_scripts": [
                "state-machine-manager=state_machine_operator.manager:main",
            ]
        },
    )
