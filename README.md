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
    auto_push_on: # optional
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
```

`type`: can be one of
- `docker-build`

# type-specific parameters

## `docker-build`

**notes**
- there are 3 possible tags that will be added to the docker image
  - `latest` - always
  - `<branch>-<short_commit_sha>` - if the pipeline is run on a branch
  - `X.Y.Z` - if the pipeline is run on a tag, in the format `vX.Y.Z`
- the `auto_push_on` entry
  - if the job for the push matches any of the entries in `auto_push_on`, it will trigger immediately, otherwise it will be a manual job.
    - if a filter is not present on an entry, all jobs will match it. It is **not** like saying that field should be `null`.
  - `source`: the `CI_PIPELINE_SOURCE`. Typically `push` or `web`, but any are valid
  - `branch`: the `CI_COMMIT_BRANCH`
  - `tag_source`: the thing used to generate the tag for the job. i.e. if the job is to push `my/image:latest`, it will look for an entry with either no `tag`, or `tag: latest`. possible values are:
    - `latest`: the `latest` tag
    - `tag`: `X.Y.Z`, sourced from the tag
    - `branch`: `<branch>-<short_commit_sha>`, source from the branch name and commit
  - `has_tag`: bool, indicating if `CI_COMMIT_TAG` is present

