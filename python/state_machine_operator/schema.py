state_machine_config_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "https://github.com/converged-computing/state-machine-operator/tree/main/python/state_machine_operator/schema.py",
    "title": "state-machine-workflow-01",
    "description": "State Machine Manager Config",
    "type": "object",
    # The only required thing is jobs
    "required": ["jobs", "workflow"],
    "properties": {
        "jobs": {"$ref": "#/definitions/jobs"},
        "workflow": {"$ref": "#/definitions/workflow"},
        "cluster": {"$ref": "#/definitions/cluster"},
        "registry": {"$ref": "#/definitions/registry"},
        "logging": {"$ref": "#/definitions/logging"},
        "config_dir": {"type": "string"},
        "additionalProperties": False,
    },
    "definitions": {
        "workflow": {
            "type": "object",
            "required": ["completed"],
            "properties": {
                "completed": {"type": "number", "default": 4},
                "prefix": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "filesystem": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "registry": {
            "type": "object",
            "properties": {
                "host": {"type": "string"},
                "plain_http": {"type": "boolean", "default": True},
            },
            "additionalProperties": False,
        },
        "cluster": {
            "type": "object",
            "properties": {
                "max_size": {"type": "number", "default": 6},
                "autoscale": {"type": "boolean", "default": False},
            },
            "additionalProperties": False,
        },
        "logging": {
            "type": "object",
            "properties": {
                "debug": {"type": "boolean", "default": False},
            },
            "additionalProperties": False,
        },
        "jobs": {
            "type": ["array"],
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                },
                "required": ["config"],
            },
        },
    },
}

state_machine_job_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "https://github.com/converged-computing/state-machine-operator/tree/main/python/state_machine_operator/schema.py",
    "title": "state-machine-job-01",
    "description": "State Machine Job Config",
    "type": "object",
    "required": ["name", "config", "script"],
    "properties": {
        "name": {"type": "string"},
        "config": {"$ref": "#/definitions/config"},
        "script": {"type": "string"},
        "image": {"type": "string"},
        "registry": {"$ref": "#/definitions/registry"},
        "properties": {"type": ["object", "null"]},
        "workdir": {"type": "string", "default": "/tmp/out"},
        "additionalProperties": False,
    },
    "definitions": {
        "registry": {
            "type": ["object", "null"],
            "properties": {
                # Job specific host / plain http can override the workflow
                "host": {"type": "string"},
                "plain_http": {"type": "boolean", "default": True},
                "push": {"type": "string"},
                "pull": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "config": {
            "type": "object",
            "properties": {
                "nnodes": {"type": "number", "default": 1},
            },
        },
    },
}
