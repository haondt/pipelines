# pipelines

To use this repo, project should contain a `pipeline.yml` file in the root directory.

The `pipeline.yml` file should be a list of tasks to be done by the pipeline. 

```yml
tasks:
  - type: docker-build
    on: commit
    context: . # optional
    file: Dockefile # optional
    image: foo-image
    auto: # optional
      - source: push
        branch: main
        tag_source: branch
      - source: push
        has_tag: true
        tag_source: tag
      - source: push
        has_tag: true
        tag_source: latest
    registries:
      - gitlab
      - docker-hub
  - type: python-build
    package: foo-package
    context: . # optional
    file: pyproject.toml # optional
    auto: # optional
      - source: push
      - source: web
    registries:
      - gitlab
      - pypi
      - testpypi
  - type: docker-deploy
    target: foo@bar # this can be a static value or an env variable
    key: $TARGET_SSH_KEY # this can be a static value or an env variable
    auto: # optional
      - source: push
        branch: main
    
```

`type`: can be one of
- `docker-build`
- `python-build`

Additionally, project should contain a `.gitlab-ci.yml` that references this repo, as well as overrides the pipeline triggers.
By default, the pipeline only triggers on `web`.

```yml
include:
  - project: 'haondt/CICD/pipelines'
    ref: main
    file: 'generate.yml'

workflow:
  rules:
    - if: $CI_PIPELINE_SOURCE == "push" 
    - if: $CI_PIPELINE_SOURCE == "web"
    - if: $CI_COMMIT_TAG
```

# type-specific parameters

## `docker-build`

**notes**
- there are 3 possible tags that will be added to the docker image
  - `latest` - always
  - `<branch>-<short_commit_sha>` - if the pipeline is run on a branch
  - `X.Y.Z` - if the pipeline is run on a tag, in the format `vX.Y.Z`
- the `auto` entry
  - if the job for the push matches any of the entries in `auto`, it will trigger immediately, otherwise it will be a manual job.
    - if a filter is not present on an entry, all jobs will match it. It is **not** like saying that field should be `null`.
  - `source`: the `CI_PIPELINE_SOURCE`. Typically `push` or `web`, but any are valid
  - `branch`: the `CI_COMMIT_BRANCH`
  - `tag_source`: the thing used to generate the tag for the job. i.e. if the job is to push `my/image:latest`, it will look for an entry with either no `tag`, or `tag: latest`. possible values are:
    - `latest`: the `latest` tag
    - `tag`: `X.Y.Z`, sourced from the tag
    - `commit`: `<branch>-<short_commit_sha>`, source from the branch name and commit
    - `branch`: `<branch>`, source from the branch name only
  - `has_tag`: bool, indicating if `CI_COMMIT_TAG` is present
  - note that this is not the same as setting the overall pipeline triggers, and that still needs to be set manually in your `.gitlab-ci.yml`.

## `python-build`

**notes**
- only works on tag pipelines
- `auto_push`: whether or not to push automatically
- the `auto` entry
  - see [docker-build](#docker-build) for basics, with a caveat:
    - only the `source` key is supported, as the job will fail on non-tag pipelines

## `docker-deploy`

**notes**
- requires a specific repositiory structure. See [docker deploy docs](./docker_deploy.md) for details.
- `key` should be a file that contains private ssh key to connect to the target
- the `auto` entry
  - see [docker-build](#docker-build) for basics, with a caveat:
    - only the `source` and `branch` keys are supported
