job_script = """
  {% if registry %}which oras || (echo "Oras is required to use a registry" && exit 1){% endif %}
  jobid="{{ jobid }}"
  outpath="{{ workdir }}"
  {% if registry %}
  registry="{{ registry["host"] }}"
  {% if registry["pull"] %}pull_tag={{ registry["pull"] }}{% endif %}
  {% if registry["push"] %}push_tag={{ registry["push"] }}{% endif %}
  {% endif %}

  echo ">> jobid        = $jobid"
  echo ">> outpath      = $outpath"
  {% if registry %}echo ">> registry     = $registry"{% endif %}
  echo ">> hostname     = "$(hostname)
  mkdir -p -v $outpath; cd $outpath

  {% if pull %}
  echo "Looking for $jobid with oras repo list"
  oras repo list $registry {% if plain_http %}--plain-http{% endif %} | grep ${jobid}
  echo "Pulling oras artifact to $locpath"
  oras pull $registry/${jobid}:{{ pull }} {% if plain_http %}--plain-http{% endif %}
  {% endif %}

  {{ script }}

  {% if push %}
  retval=$?
  if [ $retval -eq 0 ];
  then
      cd $outpath
      echo "Job was successful, pushing result to $registry/${jobid}:{{ push }}"
      oras push {% if plain_http %}--plain-http{% endif %} $registry/${jobid}:{{ push }} .
  else
    echo "Job was not successful"
    exit 1
  fi
  {% endif %}
"""

job_config = (
    """
config:
  nnodes:           {% if config["nodes"] %}{{ config["nodes"] }}{% else %}1{% endif %}
  cores_per_task:   {% if config["coresPerTask"] %}{{ config["coresPerTask"] }}{% else %}6{% endif %}
  ngpus:            {% if config["gpus"] %}{{ config["gpus"] }}{% else %}0{% endif %}
  {% if config["walltime"] %}walltime:         '{{ config["walltime"] }}'{% endif %}
  retry_failure:    {% if config["retryFailure"] %}true{% else %}false{% endif %}
  {% if config["command"] %}command: {{ config["command"] }}{% endif %}

workdir:  {{ workdir }}

{% if registry %}
registry:
  {% if registry["push"] %}push: {{ registry["push"] }}{% endif %}
  {% if registry["pull"] %}pull: {{ registry["pull"] }}{% endif %}
  {% if registry["host"] %}host: {{ registry["host"] }}{% endif %}
{% endif %}

# This will need testing to determine a good format.
{% if appconfig %}
app-config: |
  {{ appconfig }}
{% endif %}

{% if script %}
script: |"""
    + job_script
    + """
{% endif %}
"""
)
